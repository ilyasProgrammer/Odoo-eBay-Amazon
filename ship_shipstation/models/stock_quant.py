# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    # Empty same location first
    @api.model
    def _quants_removal_get_order(self, removal_strategy=None):
        if removal_strategy == 'fifo':
            return 'location_id, in_date, id'
        elif removal_strategy == 'lifo':
            return 'location_id, in_date desc, id desc'
        raise UserError(_('Removal strategy %s not implemented.') % (removal_strategy,))

    def _quants_get_reservation(self, quantity, move, ops=False, domain=None, orderby=None, removal_strategy=None):
        if removal_strategy:
            order = self._quants_removal_get_order(removal_strategy)
        elif orderby:
            order = orderby
        else:
            order = 'location_id, in_date'

        rounding = move.product_id.uom_id.rounding
        domain = domain if domain is not None else [('qty', '>', 0.0)]
        res = []
        offset = 0

        remaining_quantity = quantity
        quants = self.search(domain, order=order, limit=10, offset=offset)
        quants = self.sort_quants(quants)
        while float_compare(remaining_quantity, 0, precision_rounding=rounding) > 0 and quants:
            for quant in quants:
                if float_compare(remaining_quantity, abs(quant.qty), precision_rounding=rounding) >= 0:
                    # reserved_quants.append(self._ReservedQuant(quant, abs(quant.qty)))
                    res += [(quant, abs(quant.qty))]
                    remaining_quantity -= abs(quant.qty)
                elif float_compare(remaining_quantity, 0.0, precision_rounding=rounding) != 0:
                    # reserved_quants.append(self._ReservedQuant(quant, remaining_quantity))
                    res += [(quant, remaining_quantity)]
                    remaining_quantity = 0
            offset += 10
            quants = self.search(domain, order=order, limit=10, offset=offset)

        if float_compare(remaining_quantity, 0, precision_rounding=rounding) > 0:
            res.append((None, remaining_quantity))
        return res

    @api.model
    def sort_quants(self, quants):
        #  Quants should be taken from locations where qty sum is minimal
        try:  # TODO try is for cowards. remove it later.
            locs = set([r.location_id for r in quants])
            if len(locs) < 2:
                return quants
            priority = []
            res = self.env['stock.quant']
            quants = quants.sorted(key=lambda r: r.qty)
            for loc in locs:
                priority.append((loc, sum([r.qty for r in quants.filtered(lambda x: x.location_id == loc)])))
            priority.sort(key=lambda tup: tup[1])
            for pr in priority:
                for q in quants:
                    if q.location_id.id == pr[0].id:
                        res += q
            return res
        except Exception as e:
            _logger.error("Error: %s" % (e.message or repr(e)))
            return quants
