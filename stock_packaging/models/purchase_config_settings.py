# -*- coding: utf-8 -*-

from odoo import fields, models, api


class PurchaseConfigSettings(models.TransientModel):
    _name = 'purchase.config.settings'
    _inherit = 'purchase.config.settings'

    packaging_partner_id = fields.Many2one('res.partner', 'Vendor', domain=[('supplier', '=', True)])

    @api.multi
    def set_packaging_partner_config(self):
        packaging_partner_id = self[0].packaging_partner_id or ''
        self.env['ir.config_parameter'].set_param('packaging_partner_id', packaging_partner_id.id, groups=["base.group_user"])

    @api.model
    def get_default_packaging_parnter_config(self, fields):
        packaging_partner_id = self.env['ir.config_parameter'].get_param('packaging_partner_id', False)
        return {
            'packaging_partner_id': int(packaging_partner_id) if packaging_partner_id else None
        }
