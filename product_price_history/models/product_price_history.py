# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductPriceHistory(models.Model):
    _inherit = 'product.price.history'

    @api.model
    def delete_repeated_price_history(self):
        _logger.info("Starting delete_repeated_price_history")
        histories = self.env['product.price.history'].search([], order="datetime desc")
        product_history = {}
        deleted_records = []
        for h in histories:
            if product_history.get((h.product_id.id, h.cost)):
                deleted_records.append(h.id)
            else:
                product_history[h.product_id.id, h.cost] = True
        sql = "DELETE FROM product_price_history where id IN ( %s )" % str(deleted_records)[1:-1]
        cr = self.env.cr
        cr.execute(sql)
        _logger.info("End of delete_repeated_price_history, deleted: " + str(len(deleted_records)) + ' records')
