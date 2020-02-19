# -*- coding: utf-8 -*-

from odoo import api, models, fields


class CustomMessage(models.TransientModel):
    _name = "custom.message"

    text = fields.Text('Text')
