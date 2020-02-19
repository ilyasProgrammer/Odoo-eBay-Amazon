# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Picking(models.Model):
    _inherit = 'stock.picking'

    recon_line_ids = fields.One2many('purchase.shipping.recon.line', 'pick_id', 'Recon Lines')


class TrackingLine(models.Model):
    _inherit = 'stock.picking.tracking.line'

    recon_line_ids = fields.One2many('purchase.shipping.recon.line', 'tracking_line_id', 'Recon Lines')
