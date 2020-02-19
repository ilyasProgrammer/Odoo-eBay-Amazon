# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def onchange_template_id(self, template_id, composition_mode, model, res_id):
        values = super(MailComposeMessage, self).onchange_template_id(template_id, composition_mode, model, res_id)
        if model == 'purchase.order':
            po_id = self.env['purchase.order'].browse([res_id])
            attachment_id = po_id.create_purchase_attachment()
            values['value']['attachment_ids'] = [(6, 0, [attachment_id.id])]
        return values
