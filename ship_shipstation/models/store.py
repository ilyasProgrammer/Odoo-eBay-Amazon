# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields

class OnlineStore(models.Model):
    _inherit = 'sale.store'

    ss_warehouse_id = fields.Char('SS Warehouse ID')

    @api.multi
    def button_get_warehouse_id(self):
        self.ensure_one()
        result = self.env['sale.order'].ss_execute_request('GET', '/warehouses')
        for wh in result:
            if wh['warehouseName'] == self.name:
                self.write({'ss_warehouse_id': wh['warehouseId']})
                break
        else:
            company_id = self.env.user.company_id
            data = {
                'warehouseName': self.name,
                'originAddress': {
                    'name': self.name,
                    'company': self.name,
                    'street1': company_id.street,
                    'street2': company_id.street2 or '',
                    'city': company_id.city,
                    'state': company_id.state_id.code,
                    'postalCode': company_id.zip,
                    'country': company_id.country_id.code,
                    'phone': company_id.phone
                }
            }
            result = self.env['sale.order'].ss_execute_request('POST', '/warehouses/createwarehouse', data)
            self.write({'ss_warehouse_id': result['warehouseId']})

    @api.multi
    def get_tracking_numbers_to_send_to_store(self):
        self.ensure_one()
