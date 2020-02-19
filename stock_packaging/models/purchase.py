# -*- coding: utf-8 -*-

import base64
import csv
from cStringIO import StringIO
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

from odoo import models, fields, api, _


class Purchase(models.Model):
    _inherit = 'purchase.order'

    use_non_auto_supplies_layout = fields.Boolean('Use Layout for Non-Auto Supplies')

    @api.model
    def cron_reorder_packaging_supplies(self):
        # sdt_14_days_ago = (datetime.now() - timedelta(days=14)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        sdt_30_days_ago = (datetime.now() - timedelta(days=30)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        # param_partner_id = self.env['ir.config_parameter'].get_param('packaging_partner_id', False)
        # partner_id = False
        # if param_partner_id:
        #     partner_id = self.env['res.partner'].browse([int(param_partner_id)])
        partners_ids = self.env['res.partner'].browse([45772, 333654])  # Aero Box, Tri-County
        # if partner_id:
        for partner_id in partners_ids:
            sql = ("""
                SELECT PT.name as name, PT.uom_po_id as product_uom, PP.id as product_id, MOVE_RES.demand, QUANT_RES.qty_available, 
                INCOMING.incoming_total, PL_RES.min_qty, PL_RES.price
                FROM product_template PT
                LEFT JOIN product_product PP on PP.id = PT.product_variant_id
                LEFT JOIN (
                    SELECT MOVE.product_id, SUM(MOVE.product_uom_qty) as demand
                    FROM stock_move MOVE
                    WHERE MOVE.create_date >= %s AND MOVE.state = 'done' AND MOVE.name LIKE 'PACK%%'
                    GROUP BY MOVE.product_id
                    ) as MOVE_RES on MOVE_RES.product_id = PP.id
                LEFT JOIN
                    (SELECT QUANT.product_id, SUM(QUANT.qty) as qty_available
                    FROM stock_quant QUANT
                    LEFT JOIN stock_location LOC on QUANT.location_id = LOC.id
                    WHERE LOC.usage = 'internal' AND QUANT.qty > 0
                    GROUP BY QUANT.product_id
                    ) as QUANT_RES on QUANT_RES.product_id = PP.id
                LEFT JOIN (
                    SELECT POL.product_id, SUM(POL.product_qty - POL.qty_received) as incoming_total
                    FROM purchase_order_line POL
                    LEFT JOIN purchase_order PO on POL.order_id = PO.id
                    WHERE POL.product_qty > POL.qty_received AND POL.state NOT IN ('cancel', 'done')
                    AND PO.dest_address_id IS NULL
                    GROUP BY POL.product_id
                ) AS INCOMING on INCOMING.product_id = PP.id
                LEFT JOIN (
                    SELECT PL_SUB_RES.product_id, PL_SUB_RES.min_qty, PL_SUB_RES.price
                    FROM
                        (SELECT PP.id as product_id, PL.min_qty, PL.price, RANK() OVER(PARTITION BY PL.product_tmpl_id ORDER BY PL.price) AS rank
                        FROM product_supplierinfo PL
                        LEFT JOIN product_template PT on PL.product_tmpl_id = PT.id
                        LEFT JOIN product_product PP on PP.id = PT.product_variant_id
                        WHERE PL.price > 0 AND PL.name = %s
                        ) as PL_SUB_RES WHERE PL_SUB_RES.rank = 1
                ) AS PL_RES on PL_RES.product_id = PP.id
                WHERE PT.is_packaging_product = True AND PL_RES.price <> 0;""")
            params = [sdt_30_days_ago, partner_id.id]
            cr = self.env.cr
            cr.execute(sql, params)
            results = cr.dictfetchall()
            to_order = []
            for res in results:
                incoming_total = int(res['incoming_total']) if res['incoming_total'] > 0 else 0
                qty_available = int(res['qty_available']) if res['qty_available'] > 0 else 0
                demand = int(res['demand']) if res['demand'] > 0 else 0
                min_qty = int(res['min_qty']) if res['min_qty'] else 1
                required_qty = demand - (incoming_total + qty_available)
                if required_qty > 0:
                    to_order_qty = ((required_qty + (min_qty - 1)) / min_qty) * min_qty
                    date_planned = (datetime.now() + timedelta(days=partner_id.purchase_lead_time)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    to_order.append({
                        'name': res['name'],
                        'date_planned': date_planned,
                        'product_id': res['product_id'],
                        'product_qty': float(to_order_qty),
                        'price_unit': float(res['price']),
                        'product_uom': res['product_uom']
                    })
            if to_order:
                po_id = self.create({'partner_id': partner_id.id, 'use_non_auto_supplies_layout': True})
                for row in to_order:
                    row['order_id'] = po_id.id
                    po_id.order_line.create(row)
                email_act = po_id.action_rfq_send()
                if email_act and email_act.get('context'):
                    email_ctx = email_act['context']
                    po_id.with_context(email_ctx).message_post_with_template(email_ctx.get('default_template_id'))

    @api.multi
    def get_non_auto_rfq_lines(self):
        data = []
        sql = ("""
            SELECT PT.name, VC.vendor_code, POL.product_qty, POL.price_unit, POL.price_subtotal
            FROM purchase_order_line POL
            LEFT JOIN purchase_order PO ON POL.order_id = PO.id
            LEFT JOIN product_product PP ON PP.id = POL.product_id
            LEFT JOIN product_template PT ON PT.id = PP.product_tmpl_id
            LEFT JOIN (
                SELECT PS.product_tmpl_id, PS.name, MAX(PS.product_code) as vendor_code
                FROM product_supplierinfo PS
                GROUP BY PS.product_tmpl_id, PS.name
            ) as VC on VC.product_tmpl_id = PT.id and VC.name = PO.partner_id
            WHERE PO.id = %s
        """)
        params = [self.id]
        cr = self.env.cr
        cr.execute(sql, params)
        results = cr.dictfetchall()
        for res in results:
            if 'Teletwin' in res['vendor_code']:
                row = [
                    res['vendor_code'] if 'vendor_code' in res and res['vendor_code'] else res['name'],
                    # 2 * res['product_qty'],
                    res['product_qty'],
                ]
            else:
                row = [
                    res['vendor_code'] if 'vendor_code' in res and res['vendor_code'] else res['name'],
                    res['product_qty'],
                ]
            data.append(row)
        return data

    @api.multi
    def create_purchase_attachment(self):
        self.ensure_one()
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        if self.use_non_auto_supplies_layout:
            columns = ['Description', 'Qty']
            rows = self.get_non_auto_rfq_lines()
        else:
            columns = ['LAD Part Number', 'Vendor Code', 'Partslink', 'Description', 'Qty', 'Unit Price', 'Subtotal']
            rows = self.get_rfq_lines()
        writer.writerow([name.encode('utf-8') for name in columns])
        for row in rows:
            writer.writerow(row)
        fp.seek(0)
        data = fp.read()
        fp.close()
        attachment_id = self.env['ir.attachment'].create({
            'name': self.name,
            'datas_fname': self.name + '.csv',
            'datas': base64.encodestring(data)
        })
        return attachment_id

    @api.multi
    def action_rfq_send(self):
        if self.use_non_auto_supplies_layout:
            ir_model_data = self.env['ir.model.data']
            try:
                template_id = ir_model_data.get_object_reference('stock_packaging', 'email_template_aero_purchase')[1]
            except ValueError:
                template_id = False
            try:
                compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
            except ValueError:
                compose_form_id = False
            ctx = dict(self.env.context or {})
            ctx.update({
                'default_model': 'purchase.order',
                'default_res_id': self.ids[0],
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'default_composition_mode': 'comment',
            })
            return {
                'name': _('Compose Email'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form_id, 'form')],
                'view_id': compose_form_id,
                'target': 'new',
                'context': ctx,
            }
        else:
            return super(Purchase, self).action_rfq_send()
