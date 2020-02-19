# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import models
import wizard
import models
# from odoo import api, SUPERUSER_ID


# def set_amz_order_type(cr, registry):
#     env = api.Environment(cr, SUPERUSER_ID, {})
#     orders = env['sale.order'].search([])
#     for order in orders:
#         if order.store_id.site == 'amz':
#             if order.is_fbm_prime:
#                 order.amz_order_type = 'fbm'
#             else:
#                 order.amz_order_type = 'normal'
#         else:
#             order.amz_order_type = 'ebay'


