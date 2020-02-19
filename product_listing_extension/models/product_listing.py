# -*- coding: utf-8 -*-

from odoo import models, fields, api
from pytz import timezone
from datetime import datetime
import logging

_log = logging.getLogger(__name__)


class ProductListing(models.Model):
    _inherit = 'product.listing'

    current_price = fields.Float('Current Price', track_visibility='onchange')
    current_min_price = fields.Float('Current Min Price', track_visibility='onchange')
    current_max_price = fields.Float('Current Max Price', track_visibility='onchange')
    previous_price = fields.Float('Previous Price', track_visibility='onchange')
    title = fields.Char('Title', track_visibility='onchange')
    qty_sold = fields.Integer('Qty Sold', track_visibility='onchange')
    listing_url = fields.Char('Listing URL', compute='_get_listing_url')
    custom_label = fields.Char('Custom Label', track_visibility='onchange')
    brand = fields.Char('Brand', track_visibility='onchange')
    asin = fields.Char('ASIN', track_visibility='onchange')
    price_explain = fields.Text(compute='_compute_price_explain', string='Price explanation', track_visibility='onchange')
    dumping_percent = fields.Float('Dumping Percent', default=0, help='Overwrites store percent', track_visibility='onchange')
    dumping_amount = fields.Float('Dumping Amount', default=0, help='Overwrites store amount', track_visibility='onchange')
    min_store_qty = fields.Integer('Min qty', default=0, help='Set 0 to use store setting', track_visibility='onchange')
    max_store_qty = fields.Integer('Max qty', default=0, help='Set 0 to use store setting', track_visibility='onchange')
    manual_price = fields.Float('Manual price', default=0.0, track_visibility='onchange')
    keep_manual = fields.Boolean('Keep manual price', default=False, track_visibility='onchange')
    price_history = fields.Text('Price History', default='')

    @api.multi
    def write(self, values):
        if values.get('current_price') and values.get('current_price') != self.current_price:
            now = datetime.now(timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S')
            # now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            values['price_history'] = '%s  %s\n%s' % (now, values['current_price'], self.price_history)
        # values['fresh_record'] = False
        return super(ProductListing, self).write(values)

    @api.multi
    def _compute_price_explain(self):
        if self.store_id.site == 'amz':
            return
        store = self.store_id.code
        rates = {'visionary': 1.08, 'visionary_mg': 1.07, 'visionary_v2f': 1.06, 'revive': 1.09, 'revive_apc': 1.095, 'rhino': 1.1, 'ride': 1.11}
        if not rates.get(store):
            return
        report = ''
        rate_diff = 1 + (rates[store] - rates['visionary'])
        ebay_fees = {'visionary': 0.1051, 'revive': 0.1103, 'rhino': 0.1303, 'ride': 0.0847}
        percents = {'visionary': 3,
                    'visionary_mg': 3,
                    # 'visionary_v2f': 3,  # competes only with C2C
                    'revive': 1.5,
                    'revive_apc': 1.5,
                    'rhino': 0.5,
                    'ride': 2}
        paypal_fee = 0.0215
        report += "Rate_diff: 1 + (rates[store] - rates['visionary'])\n"
        report += "Rate_diff: 1 + (%s - %s) = %s\n" % (rates[store], rates['visionary'], rate_diff)

        qry = """
               SELECT PL.name,PL.custom_label,PL.current_price,PTL.wh_qty,PTL.vendor_qty,PTL.total_min_cost,PL.do_not_reprice, PL.keep_manual, PL. manual_price,
               PL.do_not_restock,PL.ebay_reprice_against_competitors,PL.sell_with_loss,PL.sell_with_loss_type,PL.sell_with_loss_percent,
               PL.sell_with_loss_amount,PTL.wh_sale_price,REP.type,REP.percent,REP.amount,COMP.non_c2c_comp_price,COMP.c2c_comp_price, 
               pb.id as pb_id, pb.multiplier, pb.do_not_reprice as pb_do_not_reprice
               FROM product_template_listed PTL
               LEFT JOIN product_listing PL 
               ON PTL.product_tmpl_id = PL.product_tmpl_id
               LEFT JOIN product_brand pb
               ON pl.brand_id = pb.id
               LEFT JOIN repricer_scheme REP 
               ON REP.id = PL.repricer_scheme_id
               LEFT JOIN ( SELECT COMP.product_tmpl_id,
                                  MIN(CASE WHEN COMP.seller <> 'classic2currentfabrication' THEN COMP.price ELSE NULL END) AS non_c2c_comp_price,
                                  MIN(CASE WHEN COMP.seller = 'classic2currentfabrication' THEN COMP.price ELSE NULL END) AS c2c_comp_price
                           FROM repricer_competitor COMP
                           WHERE COMP.state = 'active' AND COMP.price > 0
                           GROUP BY COMP.product_tmpl_id
                          ) AS COMP 
               ON COMP.product_tmpl_id = PTL.product_tmpl_id
               WHERE PL.id = %s
           """ % self.id
        self.env.cr.execute(qry)
        listings = self.env.cr.dictfetchall()
        for l in listings:
            qty = -1
            if not (l['do_not_restock'] and l['custom_label'] and l['custom_label'].startswith('X-')):
                qty = 0
                if not l['total_min_cost']:
                    qty = 0
                elif l['wh_qty'] > 0 and l['vendor_qty'] > 0:
                    qty = l['wh_qty'] + l['vendor_qty']
                elif l['wh_qty'] > 0:
                    qty = l['wh_qty']
                elif l['vendor_qty'] > 0:
                    qty = l['vendor_qty']

            if not l['do_not_reprice'] and qty > 0 and l['total_min_cost'] > 0:
                report += "Listing repricing\n"
                ebay_fee = ebay_fees[store] if store in ebay_fees else 0.11
                report += "eBay fee is %s\n" % ebay_fee
                min_ebay_cost = (0.03 + l['total_min_cost']) / (1 - ebay_fee - paypal_fee)
                report += "Minimum ebay cost: (0.03 + l['total_min_cost']) / (1 - ebay_fee - paypal_fee)\n"
                report += "Minimum ebay cost: (0.03 + %s) / (1 - %s - %s) = %s \n" % (l['total_min_cost'], ebay_fee, paypal_fee, min_ebay_cost)
                if l['pb_id'] and l['pb_do_not_reprice'] and l['multiplier']:
                    price = min_ebay_cost * l['multiplier']
                    report += "Listing has brand and do not reprice  for brand and multiplier > 0.\n Final price is min_ebay_cost * multiplier\n"
                    report += "min_ebay_cost * multiplier = %s * %s = %s\n" % (min_ebay_cost, l['multiplier'], price)
                else:
                    if l['sell_with_loss']:
                        report += "Listing sales with loss\n"
                        if l['sell_with_loss_type'] == 'percent':
                            percent = l['sell_with_loss_percent'] if l['sell_with_loss_percent'] > 0 else 1
                            report += "Loss percent is %s\n" % percent
                            report += "New Minimum ebay cost: (100 - %s) / 100 * %s = %s\n" % (percent, min_ebay_cost, (100 - percent) / 100 * min_ebay_cost)
                            min_ebay_cost = (100 - percent) / 100 * min_ebay_cost
                        else:
                            amount = l['sell_with_loss_amount'] if l['sell_with_loss_amount'] > 0 else 1
                            report += "Loss amount is %s\n" % amount
                            report += "New Minimum ebay cost: %s - %s = %s\n" % (min_ebay_cost, amount, min_ebay_cost - amount)
                            min_ebay_cost = min_ebay_cost - amount
                    price = min_ebay_cost * rates[store]
                    report += "Price based on min_ebay_cost and store rate: %s * %s = %s\n" % (min_ebay_cost, rates[store], price)
                    if l['custom_label'] and l['custom_label'].startswith('X-'):
                        price = -1
                    elif l['custom_label'] and l['custom_label'].startswith('MG-'):
                        report += "Brand is MG\n"
                        if l['wh_qty'] > 0 and l['wh_sale_price'] > 0:
                            price = max((1 + (rates['visionary_mg'] - rates['visionary'])) * l['wh_sale_price'], min_ebay_cost)
                            report += "New price: max((1 + (rates['visionary_mg'] - rates['visionary'])) * l['wh_sale_price'], min_ebay_cost) \n"
                            report += "New price: max((1 + (%s - %s)) * %s, %s) = %s \n" % (rates['visionary_mg'], rates['visionary'], l['wh_sale_price'], min_ebay_cost, price)
                        else:
                            price = min_ebay_cost * rates['visionary_mg']
                            report += "No wh_sale_price\n"
                            report += "New price: min_ebay_cost * rates['visionary_mg']\n"
                            report += "New price: %s * %s = %s\n" % (min_ebay_cost, rates['visionary_mg'], price)
                    elif l['custom_label'] and l['custom_label'].startswith('V2F'):
                        report += "Brand is V2F\n"
                        if l['wh_qty'] > 0 and l['wh_sale_price'] > 0:
                            price = max((1 + (rates['visionary_v2f'] - rates['visionary'])) * l['wh_sale_price'], min_ebay_cost)
                            report += "New price: max((1 + (rates['visionary_v2f'] - rates['visionary'])) * l['wh_sale_price'], min_ebay_cost) \n"
                            report += "New price: max((1 + (%s - %s)) * %s, %s) = %s \n" % (rates['visionary_v2f'], rates['visionary'], l['wh_sale_price'], min_ebay_cost, price)
                        else:
                            price = min_ebay_cost * rates['visionary_v2f']
                            report += "No wh_sale_price\n"
                            report += "New price: min_ebay_cost * rates['visionary_v2f']\n"
                            report += "New price: %s * %s = %s\n" % (min_ebay_cost, rates['visionary_v2f'], price)
                    elif l['custom_label'] and l['custom_label'].startswith('APC'):
                        report += "Brand is APC\n"
                        if l['wh_qty'] > 0 and l['wh_sale_price'] > 0:
                            price = max((1 + (rates['revive_apc'] - rates['visionary'])) * l['wh_sale_price'], min_ebay_cost)
                            report += "New price: max((1 + (rates['revive_apc'] - rates['visionary'])) * l['wh_sale_price'], min_ebay_cost) \n"
                            report += "New price: max((1 + (%s - %s)) * %s, %s) = %s \n" % (rates['revive_apc'], rates['visionary'], l['wh_sale_price'], min_ebay_cost, price)
                        else:
                            price = min_ebay_cost * rates['revive_apc']
                            report += "No wh_sale_price\n"
                            report += "New price: min_ebay_cost * rates['revive_apc']\n"
                            report += "New price: %s * %s = %s\n" % (min_ebay_cost, rates['revive_apc'], price)
                    else:
                        report += "Other brand\n"
                        # Dont pull down price of wh available listing
                        if price > 0 and l['wh_qty'] > 0:
                            if l['wh_sale_price'] > 0:
                                price = max(rate_diff * l['wh_sale_price'], min_ebay_cost)
                                report += "New price: max(rate_diff * l['wh_sale_price'], min_ebay_cost) \n"
                                report += "New price: max(%s * %s, %s) = %s \n" % (rate_diff, l['wh_sale_price'], min_ebay_cost, price)
                            elif l['current_price'] > 0:
                                price = max(l['current_price'], min_ebay_cost)
                                report += "New price:  max(l['current_price'], min_ebay_cost)\n"
                                report += "New price:  max(%s, %s) = %s \n" % (l['current_price'], min_ebay_cost, price)
                        else:
                            report += "Not available in warehouse\n"

                    if price > 0 and l['ebay_reprice_against_competitors'] and (l['non_c2c_comp_price'] > 0 or l['c2c_comp_price'] > 0):
                        report += "Listing competes\n"
                        type = l['type'] if l['type'] else 'percent'
                        report += "Type is %s\n" % type
                        comp_price = l['non_c2c_comp_price']
                        report += "Non c2c price is %s\n" % l['non_c2c_comp_price']
                        report += "c2c price is %s\n" % l['c2c_comp_price']
                        if store == 'rhino':
                            comp_price = l['c2c_comp_price']
                            report += "As store is Rhino we take c2c price as basis\n"
                        if l['custom_label'] and l['custom_label'].startswith('V2F'):
                            comp_price = l['c2c_comp_price']
                            report += "As brand is V2M we take c2c price as basis\n"
                        if comp_price > 0:
                            if self.dumping_percent:
                                report += "Dumping percent set = %s\n" % self.dumping_percent
                                price = ((100 - self.dumping_percent) / 100.0) * comp_price
                                report += "Competitive price is: ((100 - %s) / 100.0) * %s = %s\n" % (self.dumping_percent, comp_price, price)
                            elif self.dumping_amount:
                                report += "Dumping amount set = %s\n" % self.dumping_amount
                                price = comp_price - self.dumping_amount
                                report += "Competitive price is: %s - %s = %s\n" % (comp_price, self.dumping_amount, price)
                            elif type == 'percent':
                                percent = percents[store] if percents.get(store) else 1
                                report += "As store is %s percent = %s\n" % (store, percent)
                                price = ((100 - percent) / 100.0) * comp_price
                                report += "Competitive price is: ((100 - %s) / 100.0) * %s = %s\n" % (percent, comp_price, price)
                            else:
                                amount = l['amount'] if l['amount'] > 0 else 1
                                price = comp_price - amount
                        if l['keep_manual'] and l['manual_price'] > 0 and comp_price > 0:
                            if min_ebay_cost > l['manual_price']:
                                report += "Keep manual = True, but Manual Price < min_ebay_rice. Manual Price is ignored.\n"
                            if comp_price < l['manual_price']:
                                report += "Keep manual = True, but comp_price > Manual Price. Manual Price is ignored.\n"
                        if min_ebay_cost < l['manual_price'] < comp_price:
                            report += "Keep manual = True and Manual Price > min_ebay_price and Manual Price < competitor price.\nFinal price is Manual Price.\n"
                        else:
                            if price > min_ebay_cost:
                                report += "Competitive price is higher then min_ebay_cost.\nFinal price is calculated competitive price.\n"
                            else:
                                report += "Minimum ebay cost is higher then competitive price.\nFinal price is min_ebay_cost.\n"
                    else:
                        report += "Listing is not competes\n"
        self.price_explain = report

    @api.multi
    @api.depends('name', 'site', 'asin')
    def _get_listing_url(self):
        for l in self:
            if l.site == 'ebay' and l.name:
                l.listing_url = 'https://www.ebay.com/itm/' + l.name
            elif l.site == 'amz' and l.asin:
                if l.asin:
                    l.listing_url = 'https://www.amazon.com/dp/' + l.asin

    @api.multi
    def button_sync_item(self):
        self.ensure_one()
        if self.store_id.site == 'ebay':
            self.ebay_sync_listing()

    @api.multi
    def ebay_sync_listing(self):
        result = self.store_id.ebay_execute('GetItem', {
            'ItemID': self.name
        }).dict()['Item']
        self.write({
            'title': result['Title'],
            'custom_label': result['SKU'],
            'current_price': float(result['StartPrice']['value']),
            'qty_sold': int(result['SellingStatus']['QuantitySold'])
        })

    @api.multi
    def button_ebay_revise_item(self):
        revise_form = self.env.ref('sale_store_ebay.view_revise_item', False)
        ctx = dict(
            default_listing_id=self.id
        )
        return {
            'name': 'Revise Item',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.store.ebay.revise.item',
            'views': [(revise_form.id, 'form')],
            'view_id': revise_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.model
    def cron_clear_price_history(self):
        listings = self.search([('state', '=', 'active')])
        for l in listings:
            try:
                if l.price_history:
                    l.price_history = '\n'.join(l.price_history.split('\n')[0::20])
                    _log.info('Updated: %s', l.id)
            except Exception as e:
                _log.error(e)
        # for l in listings:
        #     prices = l.price_history.split('\n')
        #     np = []
        #     total = len(prices)
        #     for ind, pr in enumerate(prices):
        #         for n in range(ind+1, total-1):
        #             if pr.split(' ')[3] == prices[n].split(' ')[3]:
        #                 prices[n] = '- - - - -'
        #             else:
        #                 np.append(pr)
        #                 break
