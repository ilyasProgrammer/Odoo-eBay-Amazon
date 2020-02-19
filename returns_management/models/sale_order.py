    # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class SalesOrder(models.Model):
    _inherit = 'sale.order'

    return_ids = fields.One2many('sale.return', 'sale_order_id', 'Returns')
    return_count = fields.Integer('# of Returns', compute='_get_returns_count')

    @api.multi
    @api.depends('return_ids')
    def _get_returns_count(self):
        for so in self:
            so.return_count = len(so.return_ids)

    @api.multi
    def action_view_returns(self):
        return_ids = self.mapped('return_ids')
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('returns_management.action_sale_return')
        list_view_id = imd.xmlid_to_res_id('returns_management.view_sale_return_tree')
        form_view_id = imd.xmlid_to_res_id('returns_management.view_sale_return_form')

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(return_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % return_ids.ids
        elif len(return_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = return_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result