# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class SendPOToPPR(models.TransientModel):
    _name = 'purchase.send.po.to.ppr.wizard'

    po_ids = fields.Many2many('purchase.order', 'ppr_po_rel', 'wizard_id', 'po_id', 'Purchase Orders', domain=[('state', '=', 'draft'), ('partner_id.dropshipper_code', '=', 'ppr')])

    @api.multi
    def button_send_po_to_ppr(self):
        self.po_ids.send_to_ppr()
        return {'type': 'ir.actions.act_window_close'}



