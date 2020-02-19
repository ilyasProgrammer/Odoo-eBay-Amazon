# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def action_done(self):
        res = super(StockMove, self).action_done()
        if len(self):   # Lets set FBA shipping costs into the quants using some abstract proportions based on total picking shipping cost (taken from picking freight) and shipping rate for items vol and weight
            if self[0].location_dest_id.barcode == 'Amazon FBA':
                _logger.info("WH to FBA shipping calculations started ...")
                prop = []
                total_vol = 0
                total_weight = 0
                total_sipping = 0
                ship_from_address_id = self.env['res.partner'].browse(1)  # must be Xtreme Jeeperz
                ship_to_address_id = self.env.ref('amz_fba.amazon_wh_fullfilment_il')  # Amazon Fulfillment Center - MDW9 4200 Ferry Rd, Naperville, IL 60563, USA
                picking = self[0].picking_id
                if not picking.freight_cost:
                    _logger.error("Freight cost is not set. Processing interrupted.")
                    return
                for move in self:
                    product = move.product_tmpl_id
                    _logger.info("WH to FBA shipping: getting shipping rate for: %s", product)
                    shipping = product.get_cheapest_shipping_rate(length=product.length,
                                                                  width=product.width,
                                                                  height=product.height,
                                                                  weight=product.weight,
                                                                  ship_from_address_id=ship_from_address_id,
                                                                  ship_to_address_id=ship_to_address_id)
                    volume = product.length * product.width * product.height * move.product_qty
                    weight = product.weight * move.product_qty
                    rate = shipping['rate'] * move.product_qty
                    prop.append({'move': move,
                                 'product': product,
                                 'volume': volume,
                                 'weight': weight,
                                 'qty': move.product_qty,
                                 'rate': rate})
                    total_vol += volume
                    total_weight += weight
                    total_sipping += rate
                if len(prop):
                    result_freight = 0
                    for pr in prop:
                        pr['volume_portion'] = pr['volume']/total_vol
                        pr['weight_portion'] = pr['weight']/total_weight
                        pr['shipping_portion'] = pr['rate']/total_sipping
                        freight_portion = picking.freight_cost*pr['shipping_portion']  # take part of total shipping
                        amount = freight_portion/pr['qty']
                        for q in pr['move'].sudo().quant_ids:
                            q.amz_fba_shipping_cost = amount
                            q.cost += amount
                            result_freight += amount*q.qty
                            _logger.info("WH to FBA shipping: amz_fba_shipping_cost=%s for %s", amount,  q)
                    prop[0]['move'].quant_ids[0].sudo().amz_fba_shipping_cost += picking.freight_cost - result_freight  # for the case of rounding issues
                _logger.info("Done WH to FBA shipping calculations")
        return res
