# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class StoreMessage(models.Model):
    _name = 'sale.store.amz.message'
    _inherit = ['mail.thread']

    name = fields.Char('Subject', required=True)
    store_id = fields.Many2one('sale.store', 'Store')
    raw_content = fields.Text('Raw Content')

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        self = self.with_context(default_user_id=False)
        print msg_dict
        defaults = {
            'name':  msg_dict.get('subject') or _("No Subject")
        }
        store_email = msg_dict['to'].split('<')[1][:-1]
        store_id = self.env['sale.store'].search([('amz_email', '=', store_email)])
        if store_id:
            defaults['store_id'] = store_id.id
        return super(StoreMessage, self).message_new(msg_dict, custom_values=defaults)

    @api.multi
    def process_message(self):
        pass

    @api.multi
    def action_reply(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('sale', 'email_template_edi_sale')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'sale.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "sale.mail_template_data_notification_email_sale_order"
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
