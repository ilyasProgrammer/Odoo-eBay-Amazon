# -*- coding: utf-8 -*-

from openerp import models, fields, api, exceptions, _


class StockInventory(models.Model):
    _inherit = "stock.inventory"

    @api.multi
    def action_done(self):
        res = super(StockInventory, self).action_done()
        msg = ''
        for m in self.move_ids:
            for q in m.quant_ids:
                if q.cost == 0:
                    msg += '\tID: %s   Product: %s   Qty: %s   Location: %s\n' % (q.id, q.product_id.name, q.qty, q.location_id.name)
        if msg:
            return {
                'name': 'Warning! Zero quants created.',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'custom.message',
                'target': 'new',
                'context': {'default_text': msg}
            }
        else:
            return res
