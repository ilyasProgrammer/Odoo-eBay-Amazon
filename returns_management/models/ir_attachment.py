# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Attachment(models.Model):
    _inherit = 'ir.attachment'

    int_type = fields.Selection([('buyer', 'Buyer'), ('warehouse', 'Warehouse')], 'Type')

    @api.model
    def default_get(self, fields):
        result = super(Attachment, self).default_get(fields)
        result['name'] = ' '
        result['int_type'] = 'warehouse'
        return result
