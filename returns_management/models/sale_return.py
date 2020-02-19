# -*- coding: utf-8 -*-

import logging
import operator
import itertools
from odoo import models, fields, api, tools
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)


class SaleReturns(models.Model):
    _name = 'sale.return'
    _order = 'id desc'
    _inherit = ['mail.thread']

    # Common
    type = fields.Selection([('ebay', 'Ebay'), ('amazon', 'Amazon')])
    name = fields.Char('Reference', required=True, default='New')
    sale_order_id = fields.Many2one('sale.order', 'Related Sales Order')
    partner_id = fields.Many2one(related='sale_order_id.partner_id')
    store_id = fields.Many2one(related='sale_order_id.store_id', readonly=True)
    web_order_id = fields.Char(related='sale_order_id.web_order_id', readonly=True)
    tracking_number = fields.Char('Tracking Number', track_visibility='onchange')
    carrier_id = fields.Many2one('ship.carrier', 'Carrier')
    request_date = fields.Date('Date Requested')
    return_line_ids = fields.One2many('sale.return.line', 'return_id', 'Products', copy=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('open', 'Open'),
                              ('waiting_buyer_send', 'Waiting buyer send'),
                              ('waiting_receipt', 'Waiting back to WH'),
                              ('received', 'Received'),
                              ('to_refund', 'To Refund'),
                              ('refund_paid', 'Refund Paid'),
                              ('to_replacement', 'To Replace'),
                              ('replacement_sent', 'Repl. sent'),
                              ('done', 'Done'),  # Item returned to us. Money refunded or replacement received by buyer.
                              ('cancel', 'Cancelled'),
                              ('exception', 'Exception')], 'State', track_visibility='onchange')
    initiated_by = fields.Selection([('message', 'Message'), ('webstore', 'Web store')])
    with_return = fields.Boolean(default=False)
    with_refund = fields.Boolean(default=False)
    with_replacement = fields.Boolean(default=False)
    # Return
    receipt_picking_ids = fields.One2many('stock.picking', 'receipt_return_id', string='Receipts')
    receipt_pickings_count = fields.Integer('# Returns', compute='_compute_receipt_picking_ids')
    receipt_procurement_group_id = fields.Many2one('procurement.group', 'Receipt Procurement Group', copy=False)
    receipt_state = fields.Selection([('draft', 'draft'),
                                      ('to_receive', 'To Receive'),
                                      ('cancelled', 'Cancelled'),
                                      ('in_transit', 'In Transit'),
                                      ('delivered', 'Delivered'),  # According to API data, but not accepted in WH yet
                                      ('done', 'Done')  # Accepted in WH
                                      ], 'Receipt Status', track_visibility='onchange')
    return_reason = fields.Char('Return Reason')
    # Replacement
    # replacement_po = fields.One2many('purchase.order', 'return_id')
    # replacement_procurement_group_id = fields.Many2one('procurement.group', 'Release Procurement Group', copy=False)
    replacement_by = fields.Selection([('wh', 'WH'), ('ds', 'DS')])
    replacement_picking_ids = fields.One2many('stock.picking', 'replacement_return_id', string='Replacements')
    replacement_pickings_count = fields.Integer('# Replacements', compute='_compute_replacement_picking_ids')
    replacement_state = fields.Selection([('draft', 'Draft'), ('to_send', 'To Send'), ('cancelled', 'Cancelled'), ('in_transit', 'In Transit'), ('done', 'Done')], 'Replacement Status', track_visibility='onchange')
    attachment_ids = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'sale.return')], string='Attachments')
    attachment_number = fields.Integer(compute='_get_attachment_number', string="Number of Attachments")
    not_available_in_all = fields.Boolean('Not available in all warehouse.')
    customer_comments = fields.Char('Customer Comments')
    # Refund
    refund_amount = fields.Float('Actual refund')
    refund_status = fields.Selection([('need_to_pay', 'Need To Pay'), ('paid', 'Paid'), ('pending', 'Pending')])
    refund_type = fields.Selection([('auto', 'Auto'), ('manual', 'Manual')])
    compensation_amount = fields.Float('Credit', help='Supplier credit')
    compensation_status = fields.Selection([('draft', 'draft'), ('requested', 'requested'), ('received', 'received')])
    compensation_type = fields.Selection([('transfer', 'transfer'), ('credit', 'credit')])
    missed = fields.Boolean(default=False, help="True if this return was created through the get all year returns cron")

    @api.onchange('ebay_state')
    def set_main_state(self):
        if self.type == 'ebay':
            if self.ebay_state == 'CLOSED':
                self.state = 'done'
            elif self.ebay_state == 'ITEM_READY_TO_SHIP':
                self.state = 'open'
        elif self.type == 'amazon':
            if all(picking.state == 'done' for picking in self.receipt_picking_ids):
                self.state = 'done'
                self.receipt_state = 'done'
            elif all(picking.state == 'cancel' for picking in self.receipt_picking_ids):
                self.state = 'cancel'
                self.receipt_state = 'cancelled'
            elif all(picking.state == 'done' for picking in self.replacement_picking_ids):
                self.state = 'done'
                self.replacement_state = 'done'
            elif all(picking.state == 'cancel' for picking in self.replacement_picking_ids):
                self.state = 'cancel'
                self.replacement_state = 'cancelled'

    @api.multi
    def _get_attachment_number(self):
        read_group_res = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'sale.return'), ('res_id', 'in', self.ids)],
            ['res_id'], ['res_id'])
        attach_data = dict((res['res_id'], res['res_id_count']) for res in read_group_res)
        for record in self:
            record.attachment_number = attach_data.get(record.id, 0)

    @api.multi
    def action_get_attachment_tree_view(self):
        attachment_action = self.env.ref('returns_management.action_attachment')
        action = attachment_action.read()[0]
        action['context'] = {'default_res_model': self._name, 'default_res_id': self.ids[0]}
        action['domain'] = str(['&', ('res_model', '=', self._name), ('res_id', 'in', self.ids)])
        return action

    @api.multi
    @api.depends('receipt_procurement_group_id')
    def _compute_receipt_picking_ids(self):
        for r in self:
            r.receipt_picking_ids = self.env['stock.picking'].search([('receipt_return_id', '=', r.id)])
            r.receipt_pickings_count = len(r.receipt_picking_ids)

    @api.multi
    # @api.depends('replacement_procurement_group_id')
    def _compute_replacement_picking_ids(self):
        for r in self:
            r.replacement_picking_ids = self.env['stock.picking'].search([('replacement_return_id', '=', r.id)])
            r.replacement_pickings_count = len(r.replacement_picking_ids)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('sale.return') or 'New'
        return super(SaleReturns, self).create(vals)

    @api.multi
    def prepare_picking_for_receipt(self):
        self.ensure_one()
        # if not self.receipt_procurement_group_id:
        #     self.receipt_procurement_group_id = self.receipt_procurement_group_id.create({
        #         'name': self.name,
        #         'partner_id': self.partner_id.id
        #     })
        if not self.partner_id.property_stock_customer.id:
            # raise UserError("You must set a Customer Location for this partner %s" % self.partner_id.name)
            if self.type == 'amazon':
                self.partner_id = self.env['res.partner'].search([('barcode', '=', 'amazon')])
            elif self.type == 'ebay':
                self.partner_id = self.env['res.partner'].search([('barcode', '=', 'ebay')])
        company_id = self.env.context.get('company_id') or self.env.user.company_id.id
        warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1)
        return_picking_type_id = warehouse_id.return_type_id or warehouse_id.in_type_id
        return {
            'picking_type_id': return_picking_type_id.id,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'date': self.request_date,
            'origin': self.name,
            'location_dest_id': return_picking_type_id.default_location_dest_id.id,
            'location_id': self.partner_id.property_stock_customer.id if self.partner_id else False,
            'company_id': 1,
            'store_id': self.store_id.id,
            'receipt_return_id': self.id
        }

    @api.multi
    def create_picking_for_receipt(self):
        StockPicking = self.env['stock.picking']
        # for return_id in self:
            # if any([ptype in ['product', 'consu'] for ptype in return_id.return_line_ids.mapped('product_id.type')]):
                # pickings = return_id.receipt_picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                # if not pickings:
        picking_vals = self.prepare_picking_for_receipt()
        picking = StockPicking.create(picking_vals)
                # else:
                #     picking = pickings[0]
        moves = self.return_line_ids._create_stock_moves_for_receipt(picking)
        if moves:
            self.item_sent_by_buyer_button()
        else:
            _logger.error('Cant create moves for: %s', self)
                # moves = moves.filtered(lambda x: x.state not in ('done', 'cancel')).action_confirm()
                # moves.force_assign()
                # picking.message_post_with_view('mail.message_origin_link',
                #     values={'self': picking, 'origin': return_id},
                #     subtype_id=self.env.ref('mail.mt_note').id)
        return picking

    @api.multi
    def item_sent_by_buyer_button(self):
        for rec in self:
            picks_to_process = rec.receipt_picking_ids.filtered(lambda r: r.state not in ['cancel'])
            for pick in picks_to_process:
                if pick.state not in ['assigned']:
                    pick.action_confirm()
                    pick.action_assign()
            rec.state = 'waiting_receipt'
            rec.receipt_state = 'in_transit'
        # self.create_picking_for_receipt()

    @api.multi
    def action_view_receipt_picking(self):
        action = self.env.ref('stock.action_picking_tree')
        result = action.read()[0]

        #override the context to get rid of the default filtering on picking type
        result['context'] = {}
        pick_ids = sum([r.receipt_picking_ids.ids for r in self], [])
        #choose the view_mode accordingly
        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids and pick_ids[0] or False
        return result

    @api.multi
    def action_view_replacement_picking(self):
        action = self.env.ref('stock.action_picking_tree')
        result = action.read()[0]

        #override the context to get rid of the default filtering on picking type
        result['context'] = {}
        pick_ids = sum([r.replacement_picking_ids.ids for r in self], [])
        #choose the view_mode accordingly
        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids and pick_ids[0] or False
        return result

    @api.multi
    def receive_return_in_wh_button(self, triggered=False, location=False):
        if not triggered:
            raise UserError("You must use returns interface and scan tracking number or receive it there manually")
        done = self.env['stock.picking']
        company_id = self.env.context.get('company_id') or self.env.user.company_id.id
        warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1)
        return_type_id = warehouse_id.return_type_id
        for rec in self:
            picks_to_process = rec.receipt_picking_ids.filtered(lambda r: r.state not in ['cancel', 'done'])
            for pick in picks_to_process:
                if pick.state not in ['assigned']:
                    pick.action_confirm()
                    pick.action_assign()
                for pack in pick.pack_operation_product_ids:
                    if pack.state not in ['draft', 'cancel', 'done'] and pick.picking_type_id == return_type_id:
                        pack.location_dest_id = location.id
                        pack.qty_done = pack.product_qty
                for move in pick.move_lines:
                    if move.state not in ['draft', 'cancel', 'done'] and pick.picking_type_id == return_type_id:
                        move.location_dest_id = location.id
                pick.action_done()
                done += pick
            rec.state = 'received'
            rec.receipt_state = 'done'
        return done

    @api.multi
    def _get_routes(self):
        self.ensure_one()
        # Check availability in warehouse
        for line in self.return_line_ids:
            if line.product_id.qty_available - line.product_id.outgoing_qty >= line.product_uom_qty:
                route_id = self.sale_order_id.warehouse_id.replacement_route_id.id
                line.write({'route_id': route_id})

        # Check which supplier has all the remaining and which has lower price
        # If no warehouse can accommodate all lines, choose cheapest per line
        lines_to_process = self.return_line_ids.filtered(lambda r: len(r.route_id) == 0)
        if lines_to_process:
            inventory_ids = []
            for line in lines_to_process:
                inventory_ids.append(line.product_id.inventory_id)
            proc_rules = self.env['procurement.rule'].search([('action', '=', 'buy'), ('mfg_codes', '!=', False)])
            supplier_costs = []
            supplier_totals = []
            for rule in proc_rules:
                query = ""
                counter = 1
                for line in lines_to_process:
                    reqd_qty = max(rule.min_qty, line.product_uom_qty)
                    subquery = """
                        (SELECT ALT.InventoryID, PR.Cost
                        FROM InventoryAlt ALT
                        LEFT JOIN Inventory INV on ALT.InventoryIDAlt = INV.InventoryID
                        LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
                        LEFT JOIN Mfg MFG ON INV.MfgID = MFG.MfgId
                        WHERE MFG.MfgCode IN (%s) AND INV.QtyOnHand >= %s AND ALT.InventoryID = %s)

                        UNION

                        (SELECT INV.InventoryID, PR.Cost
                        FROM Inventory INV
                        LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
                        LEFT JOIN Mfg MFG ON INV.MfgID = MFG.MfgId
                        WHERE MFG.MfgCode IN (%s) AND INV.QtyOnHand >= %s AND INV.InventoryID = %s)

                    """ %(rule.mfg_codes, reqd_qty, line.product_id.inventory_id, rule.mfg_codes, reqd_qty, line.product_id.inventory_id)
                    if len(lines_to_process) == 1:
                        subquery = subquery[1:-1]
                    query += subquery
                    if counter < len(lines_to_process):
                        query += ' UNION '
                    counter += 1
                result = self.env['sale.order'].autoplus_execute(query)

                total_cost = 0
                for row in result:
                    total_cost += float(row['Cost'])
                    row.update({'rule': rule.id})

                supplier_costs += result

                # This part checks if all inventory ids are present in the result
                complete = False
                for inventory_id in inventory_ids:
                    found = False
                    for row in result:
                        if row['InventoryID'] == inventory_id:
                            found = True
                            break
                    if not found:
                        break
                else:
                    complete = True
                if complete:
                    supplier_totals.append({'rule': rule.id, 'cost': total_cost})

            if supplier_totals:
                supplier_totals = sorted(supplier_totals, key=lambda k: k['cost'])
                proc_rules = self.env['procurement.rule'].search([('action', '=', 'buy'), ('mfg_codes', '!=', False)])
                rule_id = self.env['procurement.rule'].browse([supplier_totals[0]['rule']])
                for line in lines_to_process:
                    cost = list(filter(lambda d: d['InventoryID'] == line.product_id.inventory_id and d['rule'] == rule_id.id, supplier_costs))[0]['Cost']
                    line.write({'route_id': rule_id.route_id.id, 'dropship_cost': cost })

            else:
                for line in lines_to_process:
                    costs = sorted(list(filter(lambda d: d['InventoryID'] == line.product_id.inventory_id, supplier_costs)), key=lambda k: k['Cost'])
                    if costs:
                        rule_id = self.env['procurement.rule'].browse([costs[0]['rule']])
                        line.write({'route_id': rule_id.route_id.id, 'dropship_cost': float(costs[0]['Cost']) })

        for line in self.return_line_ids:
            if not line.route_id:
                self.write({'not_available_in_all': True})
                break
        else:
            self.write({'not_available_in_all': False})

    @api.multi
    def print_label(self):
        return True

    @api.multi
    def create_replacement(self):
        StockPicking = self.env['stock.picking']
        # pick
        company_id = self.env.context.get('company_id') or self.env.user.company_id.id
        warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1)
        picking_type_id = warehouse_id.pick_type_id
        pick_vals = {
            'picking_type_id': picking_type_id.id,
            'partner_id': self.partner_id.id,
            'date': self.request_date,
            'origin': self.name,
            'company_id': self.sale_order_id.company_id.id,
            'store_id': self.store_id.id,
            'replacement_return_id': self.id,
            'location_dest_id': picking_type_id.default_location_dest_id.id,
            'location_id': picking_type_id.default_location_src_id.id,
        }
        pick_id = StockPicking.create(pick_vals)

        # ship replacement
        replacement_picking_type_id = self.env.ref('returns_management.replacement_picking_type')
        ship_vals = {
            'picking_type_id': replacement_picking_type_id.id,
            'partner_id': self.partner_id.id,
            'date': self.request_date,
            'origin': self.name,
            'location_dest_id': replacement_picking_type_id.default_location_dest_id.id,
            'location_id': replacement_picking_type_id.default_location_src_id.id,
            'company_id': self.sale_order_id.company_id.id,
            'store_id': self.store_id.id,
            'replacement_return_id': self.id
        }
        ship_id = StockPicking.create(ship_vals)
        moves = self.return_line_ids.create_stock_moves_for_replacement(pick_id, ship_id)
        pick_id.action_confirm()
        pick_id.action_assign()
        ship_id.action_confirm()
        ship_id.action_assign()

    @api.model
    def validate_replacement(self):
        if not self.replacement_picking_ids:
            return False
        for repl in self.replacement_picking_ids:
            pass   # TODO asd

    @api.model
    def get_carrier(self, code):
        try:
            res = self.env['ship.carrier'].search(['|', ('name', '=', code), ('ss_code', '=', code.lower())], limit=1)
            if res:
                return res.id
        except Exception as e:
            _logger.error('Cant find carrier: %s  %s', code, e)
            return None

    @api.model
    def get_all_year_returns(self, year):
        self.env['sale.return'].amazon_get_all_year_returns(year)
        self.env['sale.return'].ebay_get_all_year_returns(year)

    @api.model
    def slack_error(self, msg, title, text):
        slack_critical_channel_id = self.env['ir.config_parameter'].get_param('slack_critical_channel_id')
        attachment = {
            'color': '#DC3545',
            'fallback': title,
            'title': title,
            'text': text
        }
        self.env['slack.calls'].notify_slack(msg, 'Error', slack_critical_channel_id, attachment)


class SaleReturnLine(models.Model):
    _name = 'sale.return.line'

    return_id = fields.Many2one('sale.return', string="Return Reference", required=True, ondelete='cascade', index=True, copy=False)
    return_type = fields.Selection(related='return_id.type')
    name = fields.Char('Description', required=True)
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict')
    product_uom_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), default=1.0)
    product_uom = fields.Many2one('product.uom', string='Unit of Measure')
    sale_order_id = fields.Many2one('sale.order', 'Sales Order')
    receipt_procurement_ids = fields.One2many('procurement.order', 'receipt_return_line_id', string="Receipt Procurements", copy=False)
    replacement_procurement_ids = fields.One2many('procurement.order', 'replacement_return_line_id', string="replacement Procurements", copy=False)
    receipt_move_ids = fields.One2many('stock.move', 'receipt_return_line_id', string='Receipt Reservation', readonly=True, ondelete='set null', copy=False)
    dropship_cost = fields.Float('Dropship Cost', digits=dp.get_precision('Product Price'))
    route_id = fields.Many2one('stock.location.route', string='Route', domain=[('sale_selectable', '=', True)])
    sale_line_id = fields.Many2one('sale.order.line', 'Sale Order Line')
    return_reason = fields.Char('Return Reason')
    customer_comments = fields.Char('Customer Comments')
    item = fields.Char('Item')
    qty_received = fields.Float(compute='_compute_qty_received', string="Received Qty", digits=dp.get_precision('Product Unit of Measure'), store=True)

    @api.model
    def create(self, values):
        line = super(SaleReturnLine, self).create(values)
        if line.return_id.receipt_state == 'to_receive':
            line.return_id.create_picking_for_receipt()
        return line

    @api.multi
    def write(self, values):
        result = super(SaleReturnLine, self).write(values)
        # return_ids = self.filtered(lambda x: x.return_id.receipt_state == 'to_receive').mapped('return_id')
        # return_ids.create_picking_for_receipt()
        self.return_id.return_reason = values['return_reason'] if values.get('return_reason') else self.return_id.return_reason
        self.return_id.customer_comments = values['customer_comments'] if values.get('customer_comments') else self.return_id.customer_comments
        return result

    @api.multi
    def _get_stock_move_price_unit(self):
        self.ensure_one()
        price_unit = 0
        landed_cost = 0
        if self.sale_line_id:
            move_ids = self.env['stock.move'].search([('procurement_id.sale_line_id', '=', self.sale_line_id.id), ('picking_type_id.code', '=', 'outgoing')], order='price_unit desc')
            if move_ids:
                quant_ids = move_ids[0].quant_ids
                if quant_ids:
                    price_unit = quant_ids[0].product_cost
                    landed_cost = quant_ids[0].landed_cost
            if not move_ids:
                # Process dropship returns
                move_ids = self.env['stock.move'].search([('procurement_id.purchase_line_id.sale_line_id', '=', self.sale_line_id.id), ('picking_type_id.code', '=', 'incoming')], order='price_unit desc')
                if move_ids:
                    price_unit = move_ids[0].price_unit
        else:
            quant_ids = self.env['stock.quant'].search([('product_id', '=', self.product_id.id), ('product_cost', '>', 0)], order='product_cost desc')
            if quant_ids:
                for q in quant_ids:
                    if q.product_cost:
                        price_unit = q.product_cost
                        landed_cost = q.landed_cost
                        break
        return price_unit, landed_cost

    @api.multi
    def _create_stock_moves_for_receipt(self, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            if line.product_id.type not in ['product', 'consu']:
                continue
            qty = 0.0
            for move in line.receipt_move_ids.filtered(lambda x: x.state != 'cancelled'):
                qty += move.product_uom_qty
            price_unit, landed_cost = line._get_stock_move_price_unit()
            if not price_unit:
                self.state = 'exception'
                return done
            if not line.return_id.partner_id:
                if line.return_id.type == 'amazon':
                    partner_id = self.env['res.partner'].search([('barcode', '=', 'amazon')])
                elif line.return_id.type == 'ebay':
                    partner_id = self.env['res.partner'].search([('barcode', '=', 'ebay')])
            else:
                partner_id = line.return_id.partner_id
            template = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'date': line.return_id.request_date,
                'date_expected': line.return_id.request_date,
                'location_id': partner_id.property_stock_customer.id,
                'location_dest_id': picking.location_dest_id.id,
                'picking_id': picking.id,
                'partner_id': partner_id.id,
                'move_dest_id': False,
                'state': 'draft',
                'receipt_return_line_id': line.id,
                'company_id': line.sale_order_id.company_id.id or 1,
                'picking_type_id': picking.picking_type_id.id,
                'group_id': line.return_id.receipt_procurement_group_id.id,
                'procurement_id': False,
                'origin': line.return_id.name,
                'route_ids': [],
                'warehouse_id': picking.picking_type_id.warehouse_id.id or 1,
                'price_unit': price_unit,
                'landed_cost': landed_cost
            }
            done += moves.create(template)
        _logger.info('Return lines: %s  New moves: %s', self.ids, done.ids)
        self._cr.commit()
        return done

    @api.multi
    def create_stock_moves_for_replacement(self, pick, ship):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            if line.product_id.type not in ['product', 'consu']:
                continue
            qty = 0.0
            for move in line.receipt_move_ids.filtered(lambda x: x.state != 'cancelled'):
                qty += move.product_uom_qty
            price_unit, landed_cost = line._get_stock_move_price_unit()
            _logger.info("price_unit, landed_cost %s %s" % (price_unit, landed_cost))
            template = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'date': line.return_id.request_date,
                'date_expected': line.return_id.request_date,
                'location_id': pick.location_id.id,
                'location_dest_id': pick.location_dest_id.id,
                'picking_id': pick.id,
                'partner_id': line.return_id.partner_id.id,
                'move_dest_id': False,
                'state': 'draft',
                'replacement_return_line_id': line.id,
                'company_id': line.sale_order_id.company_id.id or 1,
                'picking_type_id': pick.picking_type_id.id,
                # 'group_id': line.return_id.receipt_procurement_group_id.id,
                'procurement_id': False,
                'origin': line.return_id.name,
                'route_ids': [],
                'warehouse_id': pick.picking_type_id.warehouse_id.id or 1,
                'price_unit': price_unit,
                'landed_cost': landed_cost
            }
            done += moves.create(template)
        # Ship
        for line in self:
            if line.product_id.type not in ['product', 'consu']:
                continue
            qty = 0.0
            for move in line.receipt_move_ids.filtered(lambda x: x.state != 'cancelled'):
                qty += move.product_uom_qty
            price_unit, landed_cost = line._get_stock_move_price_unit()
            _logger.info("price_unit, landed_cost %s %s" % (price_unit, landed_cost))
            template = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'date': line.return_id.request_date,
                'date_expected': line.return_id.request_date,
                'location_id': ship.location_id.id,
                'location_dest_id': ship.location_dest_id.id,
                'picking_id': ship.id,
                'partner_id': line.return_id.partner_id.id,
                'move_dest_id': False,
                'state': 'draft',
                'replacement_return_line_id': line.id,
                'company_id': line.sale_order_id.company_id.id or 1,
                'picking_type_id': ship.picking_type_id.id,
                # 'group_id': line.return_id.receipt_procurement_group_id.id,
                'procurement_id': False,
                'origin': line.return_id.name,
                'route_ids': [],
                'warehouse_id': ship.picking_type_id.warehouse_id.id or 1,
                'price_unit': price_unit,
                'landed_cost': landed_cost
            }
            done += moves.create(template)
        _logger.info('New move for replacement: %s', done.ids)
        return done

    @api.depends('receipt_move_ids.state')
    def _compute_qty_received(self):
        for line in self:
            total = 0.0
            for move in line.receipt_move_ids:
                if move.state == 'done':
                    if move.product_uom != line.product_uom:
                        total += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                    else:
                        total += move.product_uom_qty
            line.qty_received = total


def dv(data, path):
    for ind, el in enumerate(path):
        if data.get(el):
            return dv(data[el], path[ind+1:])
        else:
            return None
    return data
