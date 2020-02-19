# -*- coding: utf-8 -*-

from datetime import datetime
import odoo.addons.decimal_precision as dp
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    not_available_in_all = fields.Boolean('Not available in all warehouse.')
    has_multiple_order_lines = fields.Boolean('Has multiple order lines', compute='_get_has_multiple_order_lines')
    has_zero_dimension = fields.Boolean('Has zero dimension', compute='_get_has_zero_dimension')
    has_exception = fields.Boolean('Has exception', compute='_get_has_exception', store=True)
    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order", copy=False)
    purchase_order_ids = fields.One2many('purchase.order', 'sale_id', string="Dropship POs")
    purchase_order_ids_count = fields.Integer('# of Dropship POs', compute='_get_po_ids_count')
    has_no_state = fields.Boolean('Has no state', compute='_get_has_no_state', store=True)
    checked_for_loss = fields.Boolean('Checked for loss')

    @api.multi
    @api.depends('purchase_order_ids')
    def _get_po_ids_count(self):
        for so in self:
            so.purchase_order_ids_count = len(so.purchase_order_ids)

    @api.multi
    def action_view_purchase_orders(self):
        purchase_order_ids = self.mapped('purchase_order_ids')
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('purchase.purchase_order_action_generic')
        list_view_id = imd.xmlid_to_res_id('purchase.purchase_order_tree')
        form_view_id = imd.xmlid_to_res_id('purchase.purchase_order_form')

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'kanban'], [False, 'calendar'], [False, 'pivot']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(purchase_order_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % purchase_order_ids.ids
        elif len(purchase_order_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = purchase_order_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    @api.multi
    def button_reroute_to_dropship(self):
        for so in self:
            for line in so.order_line:
                line.order_id.picking_ids.action_cancel()
                query = '''
                    SELECT ALT.InventoryID, PR.Cost , INV.MfgID
                    FROM InventoryAlt ALT
                    LEFT JOIN Inventory INV on ALT.InventoryIDAlt = INV.InventoryID
                    LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
                    WHERE INV.MfgID IN (16,17,21, 35, 36, 37, 38, 39) AND INV.QtyOnHand >= %s AND ALT.InventoryID = %s''' % (line.product_uom_qty, line.product_id.inventory_id)
                result = self.autoplus_execute(query)
                mfg_id = result[0].get('MfgID')
                vendor_id = False
                if mfg_id in [17, 21]:
                    vendor_id = self.env.ref('sale_dropship.partner_lkq')
                else:
                    vendor_id = self.env.ref('sale_dropship.partner_pfg')
                fpos = self.env['account.fiscal.position'].with_context(company_id=self.company_id.id).get_fiscal_position(vendor_id.id)
                purchase_exist = self.env['purchase.order'].search([('origin', '=', line.order_id.name)])
                if not purchase_exist:
                    purchase_order = self.env['purchase.order'].create({
                        'partner_id': vendor_id.id,
                        'picking_type_id': self.env['stock.picking.type'].search([('name', 'ilike', 'dropship')]).id,
                        'company_id': self.company_id.id,
                        'currency_id': vendor_id.property_purchase_currency_id.id or self.env.user.company_id.currency_id.id,
                        'dest_address_id': line.order_id.partner_id.id,
                        'origin': line.order_id.name,
                        'payment_term_id': vendor_id.property_supplier_payment_term_id.id,
                        'date_order': fields.Datetime.now(),
                        'fiscal_position_id': fpos,
                    })
                    purchase_order_line = self.env['purchase.order.line'].create({
                        'name': line.product_id.display_name,
                        'product_qty': line.product_uom_qty,
                        'product_id': line.product_id.id,
                        'product_uom': line.product_id.uom_po_id.id,
                        'price_unit': float(result[0].get('Cost')),
                        'date_planned': fields.Datetime.now(),
                        'order_id': purchase_order.id,
                    })
                else:
                    purchase_order_line = self.env['purchase.order.line'].create({
                        'name': line.product_id.display_name,
                        'product_qty': line.product_uom_qty,
                        'product_id': line.product_id.id,
                        'product_uom': line.product_id.uom_po_id.id,
                        'price_unit': float(result[0].get('Cost')),
                        'date_planned': fields.Datetime.now(),
                        'order_id': purchase_exist.id,
                    })

    @api.multi
    @api.depends('order_line', 'order_line.product_uom_qty')
    def _get_has_multiple_order_lines(self):
        for so in self:
            if len(so.order_line) > 1 or so.order_line.product_uom_qty > 1:
                so.has_multiple_order_lines = True

    @api.multi
    @api.depends('partner_id', 'partner_id.state_id')
    def _get_has_no_state(self):
        for so in self:
            so.has_no_state = False
            if not so.partner_id.state_id:
                so.has_no_state = True

    @api.multi
    @api.depends('length', 'width', 'height', 'weight')
    def _get_has_zero_dimension(self):
        for so in self:
            dim = [so.length, so.width, so.height, so.weight]
            for d in dim:
                if d == 0.0:
                    so.has_zero_dimension = True
                    break

    @api.multi
    @api.depends('not_available_in_all', 'has_no_state')
    def _get_has_exception(self):
        for so in self:
            so.has_exception = so.not_available_in_all or so.has_no_state

    @api.multi
    def button_set_routes(self, raise_exception=True):
        self.ensure_one()

        # Check availability in warehouse
        for line in self.order_line:
            if line.product_id.qty_available - line.product_id.outgoing_qty >= line.product_uom_qty:
                route_id = self.warehouse_id.delivery_route_id.id
                line.write({'route_id': route_id})

        # Check which supplier has all the remaining and which has lower price
        # If no warehouse can accommodate all lines, choose cheapest per line
        lines_to_process = self.order_line.filtered(lambda r: len(r.route_id) == 0)
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

                    """ % (rule.mfg_codes, reqd_qty, line.product_id.inventory_id, rule.mfg_codes, reqd_qty, line.product_id.inventory_id)
                    if len(lines_to_process) == 1:
                        subquery = subquery[1:-1]
                    query += subquery
                    if counter < len(lines_to_process):
                        query += ' UNION '
                    counter += 1
                result = self.autoplus_execute(query)

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
                    print line.product_id.inventory_id
                    cost = list(filter(lambda d: d['InventoryID'] == line.product_id.inventory_id and d['rule'] == rule_id.id, supplier_costs))[0]['Cost']
                    line.write({'route_id': rule_id.route_id.id, 'dropship_cost': cost })

            else:
                for line in lines_to_process:
                    costs = sorted(list(filter(lambda d: d['InventoryID'] == line.product_id.inventory_id, supplier_costs)), key=lambda k: k['Cost'])
                    if costs:
                        rule_id = self.env['procurement.rule'].browse([costs[0]['rule']])
                        line.write({'route_id': rule_id.route_id.id, 'dropship_cost': float(costs[0]['Cost']) })

        for line in self.order_line:
            if not line.route_id:
                self.write({'not_available_in_all': True})
                break
        else:
            self.write({'not_available_in_all': False})

    @api.model
    def cron_process_sales_orders(self):
        quotations = self.search([('state', '=', 'draft')])
        for q in quotations:
            try:
                _logger.info('Processing: %s' % q.name)
                if q.has_duplicates():
                    continue
                q.button_set_dimension_from_first_order_line()
                q.button_split_kits()
                q.button_set_routes()
                if self.stop_on_rfq(q):
                    continue
                if not q.has_exception:
                    log = ''
                    for line in q.order_line:
                        if line.route_id.id == q.warehouse_id.delivery_route_id.id:
                            if not q.has_zero_dimension:
                                log = q.button_get_cheapest_service()  # anyway dimensions is only for 1st line
                    q.action_confirm()
                    for picking in q.picking_ids:
                        if picking.picking_type_id.id == 4:  # Township Fulfilment Center: Delivery Orders
                            picking.services_prices_log = log
                            picking.residential = q.residential
                    if q.amz_order_type == 'fba':
                        for picking in q.picking_ids:
                            if picking.state == 'draft':
                                picking.action_confirm()
                                if picking.state != 'assigned':
                                    picking.action_assign()
                                    if picking.state != 'assigned':
                                        raise UserError(_("Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
                            for pack in picking.pack_operation_ids:
                                if pack.product_qty > 0:
                                    pack.write({'qty_done': pack.product_qty})
                                else:
                                    pack.unlink()
                            picking.do_transfer()
            except Exception as e:
                _logger.error(e)
            self.env.cr.commit()

    @api.model
    def has_duplicates(self):
        dupes = self.env['sale.order'].search([('id', '!=', self.id),
                                               ('date_order', '>', '2019-01-01'),
                                               ('web_order_id', '=', self.web_order_id),
                                               ('state', '!=', 'cancel')])
        if self.ebay_sales_record_number:
            dupes = self.env['sale.order'].search([('id', '!=', self.id),
                                                   ('date_order', '>', '2019-01-01'),
                                                   ('ebay_sales_record_number', '=', self.ebay_sales_record_number),
                                                   ('state', '!=', 'cancel')])
        if len(dupes):
            error_text = "Order %s %s has duplicates: %s" % (self.id, self.web_order_id, dupes.mapped('id'))
            _logger.error(error_text)
            self.slack_error(error_text, 'ERROR Duplicate SO', error_text)
            return True
        return False

    @api.model
    def stop_on_rfq(self, q):
        for sol in q.order_line:
            if sol.product_id.stop_on_rfq:
                if sol.product_id.stop_on_rfq_site == 'all' or sol.product_id.stop_on_rfq_site is False:
                    _logger.info('stop_on_rfq: %s', sol.product_id)
                    return True
                elif sol.product_id.stop_on_rfq_site == q.store_id.site:
                    _logger.info('stop_on_rfq: %s', sol.product_id)
                    return True
        return False

    @api.model
    def cron_check_for_potential_losses(self):
        so_lines = self.env['sale.order.line'].search([('create_date', '>=', '2017-04-23 00:00:00'), ('dropship_cost', '>', 0), ('order_id.checked_for_loss', '=', False)], order='create_date', limit=50)
        losses = []
        for line in so_lines:
            fee = 0.0
            if line.order_id.store_id.site == 'ebay':
                fee = 0.1 * line.price_unit
            else:
                fee = 0.12 * line.price_unit

            if line.price_unit + fee > line.dropship_cost:
                losses.append({
                    'store': line.order_id.store_id.name,
                    'order_id': line.order_id.web_order_id,
                    'sales_order': line.order_id.name,
                    'product': line.product_id.name,
                    'price_unit': line.price_unit,
                    'dropship_cost': line.dropship_cost,
                    'fee': fee,
                    'loss': line.dropship_cost - (line.price_unit + fee),
                })

        order_ids = so_lines.mapped('order_id')
        # if order_ids:
        #     order_ids.write({'checked_for_loss': True})
        #     self.env.cr.commit()
        # if losses:
            # template = request.env.ref('sale_dropship.potential_loss_notification').sudo()
            # template.with_context(losses=losses).send_mail(1, force_send=True, raise_exception=True)

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


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    dropship_cost = fields.Float('Dropship Cost', digits=dp.get_precision('Product Price'))


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    alternate_cost = fields.Float(string="Alternate Cost")
    last_received = fields.Datetime(compute="_compute_purchase_info", string="Last Received")
    first_sold = fields.Datetime(compute="_compute_purchase_info", string="First Sold")
    last_sold = fields.Datetime(compute="_compute_purchase_info", string="Last Sold")
    last_returned = fields.Datetime(compute="_compute_purchase_info", string="Last Returned")
    part_min = fields.Float(string="Part Min")
    part_max = fields.Float(string="Part Max")
    part_order_point = fields.Float(string="Part Order Point")
    primary_supplier_id = fields.Many2one('res.partner', 'Primary Supplier', domain=[('supplier', '=', True)])
    lost_sale = fields.Float(compute="_compute_purchase_info", string="Lost Sale")
    current_month_sale_qty = fields.Float(compute="_compute_purchase_info", string="Current Month Sale Qty")
    current_month_sale_amt = fields.Float(compute="_compute_purchase_info", string="Current Month Sale Amt.")
    current_year_sale_qty = fields.Float(compute="_compute_purchase_info", string="Current Year Sale Qty")
    current_year_sale_amt = fields.Float(compute="_compute_purchase_info", string="Current Year Sale Amt.")
    last_month_sale_qty = fields.Float(compute="_compute_purchase_info", string="Last Month Sale Qty")
    last_month_sale_amt = fields.Float(compute="_compute_purchase_info", string="Last Month Sale Amt.")
    last_year_sale_qty = fields.Float(compute="_compute_purchase_info", string="Last Year Sale Qty")
    last_year_sale_amt = fields.Float(compute="_compute_purchase_info", string="Last Year Sale Amt.")
    current_month_cost = fields.Float(compute="_compute_purchase_info", string="Current Month Cost")
    current_year_cost = fields.Float(compute="_compute_purchase_info", string="Current Year Cost")
    qty_defect_rate = fields.Float(compute="_compute_purchase_info", string="Qty Defect Rate")
    past_year_qty1 = fields.Float(compute="_compute_purchase_info", string="Sales previous 13-24")
    past_year_qty2 = fields.Float(compute="_compute_purchase_info", string="Sales Previous 25-36")
    inv_turns = fields.Float(compute="_compute_purchase_info", string="Turns")
    reorder = fields.Boolean()

    @api.multi
    def _compute_purchase_info(self):
        PurchaseOrder = self.env['purchase.order']
        PurchaseOrderLine = self.env['purchase.order.line']
        SaleOrder = self.env['sale.order']
        SaleOrderLine = self.env['sale.order.line']
        StockPicking = self.env['stock.picking']
        StockInvLine = self.env['stock.inventory.line']
        today_date = datetime.now()
        for record in self:
            initial_qty = sum(StockInvLine.search([('inventory_id.name', 'ilike', 'Initial Inventory')]).mapped('product_qty'))
            purchase_order_lines = PurchaseOrderLine.search([('product_id', '=', record.product_variant_id.id)])
            purchase_orders = purchase_order_lines.mapped('order_id').sorted(key=lambda r: r.id)
            first_po = purchase_orders[0] if purchase_orders else PurchaseOrder
            sale_order_lines = SaleOrderLine.search([('product_id', '=', record.product_variant_id.id)])
            sale_orders = sale_order_lines.mapped('order_id').sorted(key=lambda r: r.id)
            first_so = sale_orders[0] if sale_orders else SaleOrder
            last_so = sale_orders[-1] if sale_orders else SaleOrder
            return_pickings = StockPicking.search([
                ('sale_id', 'in', sale_orders.ids),
                ('picking_type_code', '=', 'incoming'),
                ('product_id', '=', record.product_variant_id.id)])
            last_return_picking = return_pickings[-1] if return_pickings else StockPicking

            record.last_received = first_po.date_order
            record.first_sold = first_so.date_order
            record.last_sold = last_so.date_order
            record.last_returned = last_return_picking.date_done

            record.current_month_sale_qty = sum(sale_order_lines.filtered(lambda x: fields.Datetime.from_string(x.order_id.date_order).month == today_date.month).mapped('product_uom_qty'))
            record.current_month_sale_amt = sum(sale_order_lines.filtered(lambda x: fields.Datetime.from_string(x.order_id.date_order).month == today_date.month).mapped('price_subtotal'))
            record.current_year_sale_qty = sum(sale_order_lines.filtered(lambda x: fields.Datetime.from_string(x.order_id.date_order).year == today_date.year).mapped('product_uom_qty'))
            record.current_year_sale_amt = sum(sale_order_lines.filtered(lambda x: fields.Datetime.from_string(x.order_id.date_order).year == today_date.year).mapped('price_subtotal'))

            record.last_month_sale_qty = sum(sale_order_lines.filtered(lambda x: fields.Datetime.from_string(x.order_id.date_order).month == today_date.month - 1).mapped('product_uom_qty'))
            record.last_month_sale_amt = sum(sale_order_lines.filtered(lambda x: fields.Datetime.from_string(x.order_id.date_order).month == today_date.month - 1).mapped('price_subtotal'))
            record.last_year_sale_qty = sum(sale_order_lines.filtered(lambda x: fields.Datetime.from_string(x.order_id.date_order).year == today_date.year - 1).mapped('product_uom_qty'))
            record.last_year_sale_amt = sum(sale_order_lines.filtered(lambda x: fields.Datetime.from_string(x.order_id.date_order).year == today_date.year - 1).mapped('price_subtotal'))
            record.past_year_qty1 = sum(sale_order_lines.filtered(lambda x: fields.Datetime.from_string(x.order_id.date_order).year == today_date.year - 2).mapped('product_uom_qty'))
            record.past_year_qty2 = sum(sale_order_lines.filtered(lambda x: fields.Datetime.from_string(x.order_id.date_order).year == today_date.year - 3).mapped('product_uom_qty'))
            record.lost_sale = len(sale_order_lines.mapped('order_id').filtered(lambda x: x.state == 'cancel'))
            record.current_month_cost = 0.0
            record.current_year_cost = 0.0
            if sum(sale_order_lines.mapped('product_uom_qty')) > 0 and sum(return_pickings.mapped('move_lines').mapped('product_uom_qty')) > 0:
                record.qty_defect_rate = sum(sale_order_lines.mapped('product_uom_qty')) % sum(return_pickings.mapped('move_lines').mapped('product_uom_qty'))
            beggining_cost = initial_qty * record.standard_price
            ending_cost = record.qty_available * record.standard_price
            po_cost = sum(purchase_order_lines.mapped('price_subtotal'))
            cost_of_goods = (beggining_cost + po_cost) - ending_cost
            avg_inv_value = (beggining_cost + ending_cost) / 12
            if cost_of_goods > 0 and avg_inv_value > 0:
                record.inv_turns = cost_of_goods / avg_inv_value

    @api.model
    def cron_sync_products_with_autoplus(self, limit, offset):
        page_counter = 0
        while 200 * page_counter < limit:
            current_offset = offset + (200 * page_counter)
            _logger.info('Page %s, current offset %s ' %(page_counter + 1, current_offset))
            product_tmpl_ids = self.search([], order="id ASC", limit=200, offset=current_offset)
            counter = 1
            for p in product_tmpl_ids:
                try:
                    p.button_sync_with_autoplus(raise_exception=False)
                    _logger.info('Synced product %s' %(current_offset + counter))
                    self.env.cr.commit()
                except:
                    _logger.error('SKU %s not synced due to some error.')
                counter += 1
            page_counter += 1

    @api.multi
    def action_reprice(self):
        self.env['sale.store'].reprice_listing_in_store(self.product_variant_id)

    @api.model
    def cron_get_products_by_inventory_range(self, limit, offset):
        counter = 0
        while counter < limit:
            result = self.env['sale.order'].autoplus_execute(
                """
                    SELECT
                    INV.InventoryID
                    FROM Inventory INV
                    ORDER BY INV.InventoryID DESC
                    OFFSET %s ROWS
                    FETCH NEXT %s ROWS ONLY
                """
                % (counter + offset, min(limit - counter, 200)))
            _logger.info('HELLO WORLD')
            _logger.info('Processing %s rows offset by %s' %(min(limit - counter, 200), counter + offset))
            for row in result:
                product_tmpl = self.search([('inventory_id', '=', row['InventoryID'])])
                if product_tmpl:
                    product_tmpl.button_sync_with_autoplus(raise_exception=False)
                    _logger.info('Updated product from AutoPlus With Inventory %s', (row['InventoryID']))
                else:
                    product_tmpl = self.create({'name': row['InventoryID'], 'inventory_id': row['InventoryID']})
                    product_tmpl.button_sync_with_autoplus(raise_exception=False)
                    _logger.info('Created product from AutoPlus With Inventory %s', (row['InventoryID']))
                self.env.cr.commit()
            counter += 200
        _logger.info('Done processing.')
