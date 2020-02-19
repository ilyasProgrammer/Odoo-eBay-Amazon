# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    box_packaging = fields.Boolean()
    package_box = fields.Many2one('product.template', domain=[('box_packaging', '=', True)])


class PackOperation(models.Model):
    _inherit = 'stock.pack.operation'

    package_box = fields.Many2one('product.product', domain=[('box_packaging', '=', True)])
    use_exsiting_box = fields.Boolean()
    box_barcode = fields.Char()

    @api.multi
    def button_put_in(self):
        action_rec = self.env.ref('box_packaging.action_select_exist_box_wizard')
        if action_rec:
            action = action_rec.read([])[0]
            return action
        return True

    @api.multi
    def button_put_out(self):
        self.ensure_one()
        self.write({'use_exsiting_box': False, 'package_box': False})
        return True

    @api.onchange('box_barcode')
    def onchange_box_barcode(self):
        if self.box_barcode:
            self.package_box = self.env['product.product'].search([('barcode', '=', self.box_barcode), ('box_packaging', '=', True)], limit=1)

    @api.multi
    @api.onchange('product_id', 'product_uom_id')
    def onchange_product_id(self):
        res = super(PackOperation, self).onchange_product_id()
        self.package_box = self.product_id.package_box.id
        return res



class Picking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def do_new_transfer(self):
        StockMove = self.env['stock.move']
        for record in self:
            for pack in record.pack_operation_product_ids.filtered(lambda x: not x.use_exsiting_box):
                vals = {
                    'name': record.name,
                    'company_id': record.company_id.id,
                    'product_id': pack.package_box.id,
                    'product_uom': pack.package_box.uom_id.id,
                    'product_uom_qty': 1,
                    'location_id': record.location_id.id,
                    'location_dest_id': record.location_dest_id.id,
                    'origin': record.origin,
                    'picking_type_id': record.picking_type_id.id,
                    'date': record.min_date,
                    'date_expected': record.min_date,
                }
                move = StockMove.create(vals)
                move.action_done()
        res = super(Picking, self).do_new_transfer()
        return res
