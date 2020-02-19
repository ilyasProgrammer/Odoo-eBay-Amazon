# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

from datetime import datetime, timedelta
from pytz import timezone
import xml.etree.ElementTree as ET
import urllib

import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def get_taw_po_data(self):
        self.get_taw_orders_ids()
        self.env['slack.calls'].notify_slack('[ODOO] Get Tracking Numbers for TAW Orders', 'Started at %s' % datetime.utcnow())
        now = (datetime.now() - timedelta(minutes=60)).strftime('%Y-%m-%d %H:%M:%S')
        from_date = '2018-12-20 00:00:00'
        pickings = self.search([('create_date', '>=', from_date),
                                ('create_date', '<=', now),
                                ('tracking_number', '=', False),
                                ('state', '=', 'assigned'),
                                ('partner_id.dropshipper_code', '=', 'taw')], order='create_date')
        pick_no_tracks = len(pickings)
        pick_track_set = 0
        pick_track_unset = 0
        for picking in pickings:
            _logger.info('Trying to get TAW tracking number for %s' % picking.purchase_id.name)
            res = picking.get_taw_tracking_info()
            if res:
                pick_track_set += 1
            else:
                pick_track_unset += 1
            self.env.cr.commit()
        opsyst_info_channel = self.env['ir.config_parameter'].get_param('slack_odoo_opsyst_info_channel_id')
        attachment = {
            'color': '#7CD197',
            'fallback': 'TAW Tracking numbers report',
            'title': 'Period from %s to %s' % (str(from_date), str(now)),
            'text': 'Total drop pickings: %s \nTracks received for: %s \nNo tracks for: %s' % (pick_no_tracks, pick_track_set, pick_track_unset)
        }
        self.env['slack.calls'].notify_slack('[ODOO] TAW Tracking Numbers', 'Tracking numbers report', opsyst_info_channel, attachment)
        self.env['slack.calls'].notify_slack('[ODOO] TAW Tracking Numbers', 'Ended at %s' % datetime.utcnow())

    @api.multi
    def get_taw_tracking_info(self):
        self.ensure_one()
        if self.purchase_id.vendor_order_id:
            qry = """SELECT * FROM TAWOrdersProcessing.dbo.Orders WHERE QuoteID = '%s'""" % self.purchase_id.vendor_order_id
            _logger.info('\n\nTAW AUTOPLUS QRY: %s', qry)
            result = self.env['sale.order'].autoplus_execute(qry)
            if len(result) == 1:
                result = result[0]
                vals = {'tracking_number': result['TrackingNo']}  # TODO
                carrier_id = self.env['ship.carrier'].search([('name', '=', result['TrackingType'])], limit=1)  # TODO
                if carrier_id:
                    vals['carrier_id'] = carrier_id.id
                self.write(vals)
                _logger.info("\nTracking number updated: %s  for: %s" % (vals['tracking_number'], self))
                return True
            else:
                _logger.error('Cant get TAW data from AUTOPLUS for picking_id: %s  vendor_order_id:%s', self.id, self.purchase_id.vendor_order_id)
                return False

    @api.multi
    def get_taw_orders_ids(self):
        po_ids = self.env['purchase.order'].search([('dropshipper_code', '=', 'taw'), ('vendor_order_id', '=', False)])
        for po in po_ids:
            qry = """SELECT * FROM TAWOrdersProcessing.dbo.Orders WHERE PONumber = '%s'""" % po.id
            result = self.env['sale.order'].autoplus_execute(qry)
            if len(result) == 1:
                po.vendor_order_id = result[0]['QuoteID']
                _logger.info("\n\nTAW PO vendor id obtained: %s : %s" % (po.id, result[0]['QuoteID']))
            elif len(result) > 1:
                _logger.error('Too many records in TAWOrdersProcessing.dbo.Orders table for PO.id = %s', po.id)
            elif len(result) == 0:
                _logger.error('No records in TAWOrdersProcessing.dbo.Orders table for PO.id = %s', po.id)
