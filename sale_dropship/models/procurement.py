# -*- coding: utf-8 -*-

from odoo import models, fields, api,_


class ProcurementRule(models.Model):
    _inherit = 'procurement.rule'

    dropshipper_id = fields.Many2one('res.partner', 'Dropship Partner', help="This will be the priority vendor to dropship requested product.")
    mfg_codes = fields.Char('Mfg Codes', help="Corresponding MfgID of the dropshipper in AutoPlus")
    min_qty = fields.Integer('Min Qty Required from Vendor')


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def _prepare_purchase_order(self, partner):
        result = super(ProcurementOrder, self)._prepare_purchase_order(partner)
        if self.rule_id.dropshipper_id:
            result['partner_id'] = self.rule_id.dropshipper_id.id
        if self.group_id.procurement_ids.mapped('sale_line_id'):
            result['sale_id'] = self.group_id.procurement_ids.mapped('sale_line_id')[0].order_id.id
        return result

    @api.multi
    def _prepare_purchase_order_line(self, po, supplier):
        result = super(ProcurementOrder, self)._prepare_purchase_order_line(po, supplier)
        if self.rule_id.dropshipper_id:
            result['price_unit'] = self.sale_line_id.dropship_cost
            result['taxes_id'] = []
            result['sale_line_id'] = self.sale_line_id.id
        return result

    @api.multi
    def make_po(self):
        cache = {}
        res = []
        for procurement in self:
            suppliers = procurement.product_id.seller_ids.filtered(lambda r: not r.product_id or r.product_id == procurement.product_id)

            if procurement.rule_id.dropshipper_id:
                dropship_supplier = procurement.product_id.seller_ids.filtered(lambda r: r.name == procurement.rule_id.dropshipper_id and not r.product_id or r.product_id == procurement.product_id)
                if not dropship_supplier:
                    suppliers = self.env['product.supplierinfo'].sudo().create({
                        'name': procurement.rule_id.dropshipper_id.id,
                        'product_id': procurement.product_id.id,
                        'price': procurement.sale_line_id.dropship_cost
                        })

            if not suppliers:
                procurement.message_post(body=_('No vendor associated to product %s. Please set one to fix this procurement.') % (procurement.product_id.name))
                continue

            supplier = suppliers[0]
            partner = supplier.name

            gpo = procurement.rule_id.group_propagation_option
            group = (gpo == 'fixed' and procurement.rule_id.group_id) or \
                    (gpo == 'propagate' and procurement.group_id) or False
            domain = (
                ('partner_id', '=', partner.id),
                ('state', '=', 'draft'),
                ('picking_type_id', '=', procurement.rule_id.picking_type_id.id),
                ('company_id', '=', procurement.company_id.id),
                ('dest_address_id', '=', procurement.partner_dest_id.id))
            if group:
                domain += (('group_id', '=', group.id),)
            if domain in cache:
                po = cache[domain]
            else:
                po = self.env['purchase.order'].search([dom for dom in domain])
                po = po[0] if po else False
                cache[domain] = po
            if not po:
                vals = procurement._prepare_purchase_order(partner)
                po = self.env['purchase.order'].create(vals)
                if procurement.group_id.procurement_ids.mapped('sale_line_id'):
                    sale_order = procurement.group_id.procurement_ids.mapped('sale_line_id')[0].order_id
                    sale_order.write({'purchase_order_id': po.id})
                    name = (procurement.group_id and (procurement.group_id.name + ":") or "") + (procurement.name != "/" and procurement.name or procurement.move_dest_id.raw_material_production_id and procurement.move_dest_id.raw_material_production_id.name or "")
                    message = _("This purchase order has been created from: <a href=# data-oe-model=procurement.order data-oe-id=%d>%s</a>") % (procurement.id, name)
                    po.message_post(body=message)
                cache[domain] = po
            elif not po.origin or procurement.origin not in po.origin.split(', '):
                # Keep track of all procurements
                if po.origin:
                    if procurement.origin:
                        po.write({'origin': po.origin + ', ' + procurement.origin})
                    else:
                        po.write({'origin': po.origin})
                else:
                    po.write({'origin': procurement.origin})
                name = (self.group_id and (self.group_id.name + ":") or "") + (self.name != "/" and self.name or self.move_dest_id.raw_material_production_id and self.move_dest_id.raw_material_production_id.name or "")
                message = _("This purchase order has been modified from: <a href=# data-oe-model=procurement.order data-oe-id=%d>%s</a>") % (procurement.id, name)
                po.message_post(body=message)
            if po:
                res += [procurement.id]

            # Create Line
            po_line = False
            for line in po.order_line:
                if line.product_id == procurement.product_id and line.product_uom == procurement.product_id.uom_po_id:
                    procurement_uom_po_qty = procurement.product_uom._compute_quantity(procurement.product_qty, procurement.product_id.uom_po_id)
                    seller = procurement.product_id._select_seller(
                        partner_id=partner,
                        quantity=line.product_qty + procurement_uom_po_qty,
                        date=po.date_order and po.date_order[:10],
                        uom_id=procurement.product_id.uom_po_id)

                    price_unit = self.env['account.tax']._fix_tax_included_price(seller.price, line.product_id.supplier_taxes_id, line.taxes_id) if seller else 0.0
                    if price_unit and seller and po.currency_id and seller.currency_id != po.currency_id:
                        price_unit = seller.currency_id.compute(price_unit, po.currency_id)

                    po_line = line.write({
                        'product_qty': line.product_qty + procurement_uom_po_qty,
                        'price_unit': price_unit,
                        'procurement_ids': [(4, procurement.id)]
                    })
                    break
            if not po_line:
                vals = procurement._prepare_purchase_order_line(po, supplier)
                self.env['purchase.order.line'].create(vals)
        return res

    @api.model
    def cron_set_saleid_storeid(self):
        for picking in self.env['stock.picking'].search(['|', ('sale_id', '=', False), ('store_id', '=', False)]):
            sale_id = self.env['sale.order'].search([('procurement_group_id', '=', picking.group_id.id)], limit=1)
            picking.write({'sale_id': sale_id.id, 'store_id': sale_id.store_id.id})
        for po in self.env['purchase.order'].search([('sale_id', '=', False)]):
            if po.order_line:
                sale_line_ids = po.order_line[0].procurement_ids.group_id.procurement_ids.mapped('sale_line_id')
                if sale_line_ids:
                    po.sale_id = sale_line_ids[0].order_id.id
        return True
