# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class PurchaseConfigSettings(models.TransientModel):
    _name = 'purchase.config.settings'
    _inherit = 'purchase.config.settings'

    lkq_account_number = fields.Char('Account Number')
    lkq_user_name = fields.Char('User Name')
    lkq_user_password = fields.Char('Password')
    lkq_verification_code = fields.Char('Verification Code')
    lkq_partner_code = fields.Char('Partner Code')
    pfg_customer_id = fields.Char('Customer ID')
    pfg_user_name = fields.Char('User Name')
    pfg_password = fields.Char('Password')
    pfg_environment = fields.Selection([('test', 'Test'), ('prod', 'Production')], 'Environment')
    pfg_shipping_code = fields.Char('Shipping Code')

    @api.multi
    def set_vendor_config(self):
        lkq_account_number = self[0].lkq_account_number or ''
        self.env['ir.config_parameter'].set_param('lkq_account_number', lkq_account_number, groups=["base.group_system"])
        lkq_user_name = self[0].lkq_user_name or ''
        self.env['ir.config_parameter'].set_param('lkq_user_name', lkq_user_name, groups=["base.group_system"])
        lkq_user_password = self[0].lkq_user_password or ''
        self.env['ir.config_parameter'].set_param('lkq_user_password', lkq_user_password, groups=["base.group_system"])
        lkq_verification_code = self[0].lkq_verification_code or ''
        self.env['ir.config_parameter'].set_param('lkq_verification_code', lkq_verification_code, groups=["base.group_system"])
        lkq_partner_code = self[0].lkq_partner_code or ''
        self.env['ir.config_parameter'].set_param('lkq_partner_code', lkq_partner_code, groups=["base.group_system"])
        pfg_customer_id = self[0].pfg_customer_id or ''
        self.env['ir.config_parameter'].set_param('pfg_customer_id', pfg_customer_id, groups=["base.group_system"])
        pfg_user_name = self[0].pfg_user_name or ''
        self.env['ir.config_parameter'].set_param('pfg_user_name', pfg_user_name, groups=["base.group_system"])
        pfg_password = self[0].pfg_password or ''
        self.env['ir.config_parameter'].set_param('pfg_password', pfg_password, groups=["base.group_system"])
        pfg_environment = self[0].pfg_environment or ''
        self.env['ir.config_parameter'].set_param('pfg_environment', pfg_environment, groups=["base.group_system"])
        pfg_shipping_code = self[0].pfg_shipping_code or ''
        self.env['ir.config_parameter'].set_param('pfg_shipping_code', pfg_shipping_code, groups=["base.group_system"])

    @api.model
    def get_default_vendor_config(self, fields):
        params = self.env['ir.config_parameter'].sudo()
        lkq_account_number = params.get_param('lkq_account_number', default='')
        lkq_user_name = params.get_param('lkq_user_name', default='')
        lkq_user_password = params.get_param('lkq_user_password', default='')
        lkq_verification_code = params.get_param('lkq_verification_code', default='')
        lkq_partner_code = params.get_param('lkq_partner_code', default='')
        pfg_customer_id = params.get_param('pfg_customer_id', default='')
        pfg_user_name = params.get_param('pfg_user_name', default='')
        pfg_password = params.get_param('pfg_password', default='')
        pfg_environment = params.get_param('pfg_environment', default='')
        pfg_shipping_code = params.get_param('pfg_shipping_code', default='')
        return {'lkq_account_number': lkq_account_number,
            'lkq_user_name': lkq_user_name,
            'lkq_user_password': lkq_user_password,
            'lkq_verification_code': lkq_verification_code,
            'lkq_partner_code': lkq_partner_code,
            'pfg_customer_id': pfg_customer_id,
            'pfg_user_name': pfg_user_name,
            'pfg_password': pfg_password,
            'pfg_environment': pfg_environment,
            'pfg_shipping_code': pfg_shipping_code
        }
