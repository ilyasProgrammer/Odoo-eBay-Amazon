# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class IRCron(models.Model):
    _inherit = 'ir.cron'
    _order = 'priority ASC'