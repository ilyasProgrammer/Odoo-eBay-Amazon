# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class OnlineStore(models.Model):
    _inherit = 'sale.store'

    amz_returns_email = fields.Char('Returns E-mail')