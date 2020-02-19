# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from datetime import datetime

class AutoPlusConfiguration(models.TransientModel):
    _name = 'sale.config.settings'
    _inherit = 'sale.config.settings'

    autoplus_server = fields.Char("Server")
    autoplus_db_name = fields.Char("DB Name")
    autoplus_username = fields.Char("Username")
    autoplus_password = fields.Char("Password")

    @api.multi
    def set_autoplus_config(self):
        autoplus_server = self[0].autoplus_server or ''
        self.env['ir.config_parameter'].set_param('autoplus_server', autoplus_server, groups=["base.group_system"])
        autoplus_db_name = self[0].autoplus_db_name or ''
        self.env['ir.config_parameter'].set_param('autoplus_db_name', autoplus_db_name, groups=["base.group_system"])
        autoplus_username = self[0].autoplus_username or ''
        self.env['ir.config_parameter'].set_param('autoplus_username', autoplus_username, groups=["base.group_system"])
        autoplus_password = self[0].autoplus_password or ''
        self.env['ir.config_parameter'].set_param('autoplus_password', autoplus_password, groups=["base.group_system"])

    @api.model
    def get_default_autoplus_config(self, fields):
        params = self.env['ir.config_parameter'].sudo()
        autoplus_server = params.get_param('autoplus_server', default='')
        autoplus_db_name = params.get_param('autoplus_db_name', default='')
        autoplus_username = params.get_param('autoplus_username', default='')
        autoplus_password = params.get_param('autoplus_password', default='')
        return {'autoplus_server': autoplus_server,
                'autoplus_db_name': autoplus_db_name,
                'autoplus_username': autoplus_username,
                'autoplus_password': autoplus_password
                }