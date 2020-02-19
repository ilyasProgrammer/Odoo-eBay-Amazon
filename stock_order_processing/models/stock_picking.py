# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from pytz import timezone
import pytz
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    processed_by_uid = fields.Many2one('res.users', 'Processed By')
    processed_date = fields.Datetime('Processed Date')

    @api.multi
    def update_dimension_from_order_processing_ui(self, vals):
        if len(self.move_lines) == 1 and self.move_lines[0].product_uom_qty == 1:
            product_tmpl_id = self.env['product.template'].search([('id', '=', self.move_lines[0].product_id.product_tmpl_id.id)])
            product_tmpl_id.write(vals)
            pending_move_ids = self.env['stock.move'].search([
                ('state', 'not in', ['cancel', 'done']),
                ('product_id', '=', self.move_lines[0].product_id.id),
                ('product_uom_qty', '=', 1),
                ('picking_type_id.name', 'in', ['Delivery Orders', 'Replacement'])
            ])
            pending_pick_ids = pending_move_ids.mapped('picking_id').filtered(lambda r: len(r.move_lines) == 1)
            for r in pending_pick_ids:
                r.write(vals)
                r.button_get_cheapest_service()

            pending_sale_line_ids = self.env['sale.order.line'].search([
                ('order_id.state', '=', 'draft'),
                ('product_id', '=', self.move_lines[0].product_id.id),
                ('product_uom_qty', '=', 1)
            ])
            pending_sale_order_ids = pending_sale_line_ids.mapped('order_id').filtered(lambda r: len(r.order_line) == 1)
            for r in pending_sale_order_ids:
                r.write(vals)
                r.button_get_cheapest_service()

        elif len(self.sale_id.kit_line_ids) == 1 and self.sale_id.kit_line_ids[0].product_qty == 1:
            product_tmpl_id = self.env['product.template'].search([('id', '=', self.sale_id.kit_line_ids[0].product_id.product_tmpl_id.id)])
            product_tmpl_id.write(vals)
            pending_move_ids = self.env['stock.move'].search([
                ('state', 'not in', ['cancel', 'done']),
                ('product_id', '=', self.move_lines[0].product_id.id),
                ('product_uom_qty', '=', 1),
                ('picking_type_id.name', '=', 'Delivery Orders')
            ])
            pending_pick_ids = pending_move_ids.mapped('picking_id').filtered(lambda r: len(r.sale_id.kit_line_ids) == 1 and r.sale_id.kit_line_ids[0].product_id.id == self.sale_id.kit_line_ids[0].product_id.id)
            for r in pending_pick_ids:
                r.write(vals)
                r.button_get_cheapest_service()

            pending_kit_line_ids = self.env['sale.order.line.kit'].search([
                ('sale_order_id.state', '=', 'draft'),
                ('product_id', '=', self.sale_id.kit_line_ids[0].product_id.id),
                ('product_qty', '=', 1)
            ])
            pending_sale_order_ids = pending_kit_line_ids.mapped('sale_order_id').filtered(lambda r: len(r.kit_line_ids) == 1)
            for r in pending_sale_order_ids:
                r.write(vals)
                r.button_get_cheapest_service()
        else:
            self.write(vals)
            self.button_get_cheapest_service()
        return {
            'carrier': self.carrier_id.name or self.shipping_service_id,
            'service': self.service_id.name or self.shipping_service_id,
            'rate': self.rate,
        }

    @api.multi
    def do_transfer(self):
        res = super(StockPicking, self).do_transfer()
        if res:
            self.write({
                'processed_by_uid': self.env.user.id,
                'processed_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            })
        return res

    @api.model
    def get_orders_processed(self):
        def dt_to_utc(sdt):
            return timezone('US/Eastern').localize(datetime.strptime(sdt, '%Y-%m-%d %H:%M:%S')).astimezone(timezone('utc')).strftime('%Y-%m-%d %H:%M:%S')

        now = datetime.now(timezone('US/Eastern'))
        from_time = dt_to_utc(datetime.now(timezone('US/Eastern')).strftime('%Y-%m-%d 02:00:00'))
        to_time = dt_to_utc((now + timedelta(days= 1)).strftime('%Y-%m-%d 02:00:00'))
        pick_ids = self.search([('picking_type_id.require_packaging', '=', True), ('processed_by_uid', '=', self.env.user.id),
            ('processed_date', '>=', from_time), ('processed_date', '<', to_time), ('state', '=', 'done')])
        return pick_ids

    @api.model
    def get_processed_orders_count(self):
        pick_ids = self.get_orders_processed()
        return {'count': len(pick_ids)}

    @api.model
    def get_prime_orders_count(self):
        count = self.env['stock.picking'].search([('picking_type_id.name', '=', 'Delivery Orders'), ('amz_order_type', '=', 'fbm'), ('state', 'not in', ('cancel', 'done'))], count=True)
        return {'count': count}

    @api.model
    def get_late_orders_count(self):
        from_time = (datetime.now() - timedelta(days=2)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        count = self.search([('picking_type_id.name', '=', 'Delivery Orders'), ('create_date', '<=', from_time), ('state', 'not in', ('cancel', 'done'))], count=True)
        return {'count': count}

    @api.multi
    def quick_process_order(self, packaging_not_required, packages):
        try:
            # if self.picking_type_id.name == 'Replacement':
            if self.replacement_return_id:
                ship_pick_id = self.replacement_return_id.replacement_picking_ids.filtered(lambda x: x.picking_type_id.name == 'Replacement' and x.state not in ['done', 'cancel'])
            else:
                ship_pick_id = self.search([('group_id', '=', self.group_id.id),
                                            ('picking_type_id.require_packaging', '=', True),
                                            ('state', 'not in', ['cancel', 'done'])])
            if not (ship_pick_id.length and ship_pick_id.width and ship_pick_id.height and ship_pick_id.weight):
                return {'error': 'A dimension is not properly set.'}
            for pack in self.pack_operation_ids:
                if pack.product_qty > 0:
                    pack.write({'qty_done': pack.product_qty})
                else:
                    pack.unlink()
            self.do_transfer()

            if ship_pick_id:
                ship_pick_id.packaging_line_ids.unlink()
                if packaging_not_required:
                    ship_pick_id.write({'packaging_not_required': True})
                else:
                    packaging_lines = []
                    if packages:
                        for p in packages:
                            packaging_lines.append((0, 0, {'packaging_product_id': p['packaging_product_id'], 'quantity': p['quantity']}))
                        ship_pick_id.write({'packaging_not_required': False, 'packaging_line_ids': packaging_lines})

                for pack in ship_pick_id.pack_operation_ids:
                    if pack.product_qty > 0:
                        pack.write({'qty_done': pack.product_qty})
                    else:
                        pack.unlink()
                ship_pick_id.do_transfer()

                if not ship_pick_id.service_id and not ship_pick_id.shipping_service_id:
                    ship_pick_id.button_get_cheapest_service()
                try:
                    ship_pick_id.button_get_label()
                except Exception as j:
                    _logger.warning(j)
                    ship_pick_id.button_get_cheapest_service()
                    ship_pick_id.button_get_label()

        except UserError as e:
            raise UserError('%s' % (e[0],))
        return {
            'amz_order_type': ship_pick_id.amz_order_type,
            'tracking_number': ship_pick_id.tracking_number,
            'carrier': ship_pick_id.carrier_id.name or ship_pick_id.shipping_service_id,
            'service': ship_pick_id.service_id.name or ship_pick_id.shipping_service_id,
            'rate': ship_pick_id.rate,
            'label': ship_pick_id.label
        }
