# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class OnlineStore(models.Model):
    _inherit = 'sale.store'

    ebay_get_messages_enabled = fields.Boolean('Enable Get Messages')
    # amz_email = fields.Char('Recipient E-mail')
    # amz_mail_template_id = fields.Many2one('mail.template', 'E-mail template')
