# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api, tools
import logging
_log = logging.getLogger(__name__)


class OnlineStore(models.Model):
    _name = 'sale.store'

    name = fields.Char('Description', required=True)
    site = fields.Selection([('ebay', 'eBay'), ('amz', 'Amazon')], 'Site', required=True)
    code = fields.Char('Code', required=True)
    enabled = fields.Boolean('Get Orders Enabled')
    image = fields.Binary("Logo", attachment=True, help="This field holds the logo for this store, limited to 1024x1024px",)
    image_medium = fields.Binary("Medium-sized logo", attachment=True, help="Medium-sized image of this store. It is automatically resized as a 128x128px image, with aspect ratio preserved. Use this field in form views or some kanban views.")
    image_small = fields.Binary("Small-sized logo", attachment=True, help="Small-sized image of this store. It is automatically resized as a 64x64px image, with aspect ratio preserved. Use this field anywhere a small image is required.")
    image_ids = fields.One2many('sale.store.image', 'store_id', 'Images')

    @api.multi
    def write(self, vals):
        tools.image_resize_images(vals)
        return super(OnlineStore, self).write(vals)

    @api.model
    def create(self, vals):
        tools.image_resize_images(vals)
        return super(OnlineStore, self).create(vals)

    @api.multi
    def _check_required_if_site(self):
        """ If the field has 'required_if_site="<site>"' attribute, then it is
        required if record.site is <site>. """
        for store in self:
            if any(getattr(f, 'required_if_site', None) == store.site and not store[k] for k, f in self._fields.items()):
                return False
        return True

    _constraints = [
        (_check_required_if_site, 'Required fields not filled', []),
    ]

    @api.model
    def cron_getorder(self, minutes_ago):
        opsyst_info_channel = self.env['ir.config_parameter'].get_param('slack_odoo_opsyst_info_channel_id')
        self.env['slack.calls'].notify_slack('[STORE] Get Order Scheduler', 'Started at %s' % datetime.utcnow())
        now = datetime.now()
        orders_qty = []
        total = 0
        for cred in self.search([('enabled', '=', True), ('is_external_store', '=', False)]):
            if hasattr(cred, '%s_getorder' % cred.site):
                self.env['slack.calls'].notify_slack('[STORE] Get Order Scheduler', '%s' % cred.name)
                try:
                    res = getattr(cred, '%s_getorder' % cred.site)(now, minutes_ago)
                    if type(res) == int:
                        orders_qty.append({'site': cred.site, 'qty': res, 'site_name': cred.name})
                        total += res
                except Exception as e:
                    _log.error(e)
                    _log.error('cron_getorder: Store: %s', cred.name)
        if len(orders_qty):
            if total == 0:
                attachment = {
                    'color': '#7CD197',
                    'fallback': 'Pulled orders report',
                    'title': 'No new orders',
                }
            else:
                attachment = {
                    'color': '#7CD197',
                    'fallback': 'Pulled orders report',
                    'title': 'Total orders received: %s' % total,
                }
                text = ''
                for r in orders_qty:
                    if r['site'] == 'amz':
                        text += '\nReceived Amazon orders: %s' % r['qty']
                    elif r['site'] == 'ebay':
                        if int(r['qty']) > 0:
                            text += '\nReceived Ebay %s orders: %s' % (r['site_name'], r['qty'])
                attachment['text'] = text
            self.env['slack.calls'].notify_slack('[STORE] Get Order Scheduler', 'Pulled orders report', opsyst_info_channel, attachment)
        self.env['slack.calls'].notify_slack('[STORE] Get Order Scheduler', 'Ended at %s' % datetime.utcnow())

    @api.model
    def cron_getorder_external_stores(self, minutes_ago):
        now = datetime.now()
        for cred in self.search([('enabled', '=', True), ('is_external_store', '=', True)]):
            if hasattr(cred, '%s_getorder' % cred.site):
                getattr(cred, '%s_getorder' % cred.site)(now, minutes_ago)

    @api.model
    def cron_store_submit_tracking_number(self):
        now = datetime.now()
        for cred in self.search([('enabled', '=', True)]):
            if hasattr(cred, '%s_submit_tracking_number' % cred.site):
                getattr(cred, '%s_submit_tracking_number' % cred.site)(now)

    @api.model
    def cron_update_quantities(self):
        now = datetime.now()
        for cred in self.search([('enabled', '=', True)]):
            if hasattr(cred, '%s_update_quantities' % cred.site):
                getattr(cred, '%s_update_quantities' % cred.site)(now)

    @api.model
    def cron_fix_pricing(self):
        now = datetime.now()
        for cred in self.search([('enabled', '=', True)]):
            if hasattr(cred, '%s_fix_pricing' % cred.site):
                getattr(cred, '%s_fix_pricing' % cred.site)(now)

    def _get_product(self, sku):
        product_obj = self.env['product.product']
        prod_lst = product_obj.search([('part_number', '=', sku)], limit=1)
        if prod_lst and not prod_lst.mfg_code == 'ASE':
            alternate = prod_lst.alternate_ids.filtered(lambda b: b.mfg_code == 'ASE')
            prod_lst = alternate[0] if alternate else prod_lst
        if not prod_lst:
            prod_lst = product_obj.search([('partslink', '=', sku), ('bom_ids', '=', False)], limit=1)
            if prod_lst and not prod_lst.mfg_code == 'ASE':
                alternate = prod_lst.alternate_ids.filtered(lambda b: b.mfg_code == 'ASE')
                prod_lst = alternate[0] if alternate else prod_lst
        return prod_lst


class OnlineStoreFeed(models.Model):
    _name = 'sale.store.feed'

    name = fields.Char('Merchant Identifier', required=True)
    submission_id = fields.Char('Submission/Job ID')
    file_reference_id = fields.Char('File Ref ID (for eBay feeds)')
    date_submitted = fields.Datetime('Date Submitted')
    content = fields.Text('Feed', required=True)
    state = fields.Selection([('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('error', 'Error')], 'Status', default='draft')
    job_type = fields.Selection([
        ('_POST_ORDER_FULFILLMENT_DATA_', 'Amazon - Post Order Fulfillment'),
        ('SetShipmentTrackingInfo', 'eBay - Set Shipment Tracking Info')], 'Feed Type', required=True)
    store_id = fields.Many2one('sale.store', 'Store', required=True)
    result_description = fields.Char('Result Description')
    related_ids = fields.Text(string="Comma separated IDs of related objects")


class ApiLog(models.Model):
    _name = 'sale.store.log'

    name = fields.Char('Name', required=True)
    description = fields.Char('Description')
    result = fields.Text('Result')


class StoreImage(models.Model):
    _name = 'sale.store.image'

    name = fields.Char('Description', required=True)
    code = fields.Char('Code', required=True)
    image = fields.Binary('Image')
    store_id = fields.Many2one('sale.store', 'Store')
