# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    dropshipper_code = fields.Selection(selection_add=[('taw', 'TAW')])
