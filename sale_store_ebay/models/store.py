# -*- coding: utf-8 -*-

from ebaysdk.exception import ConnectionError
from ebaysdk.trading import Connection as Trading
from ebaysdk.utils import dict2xml
import requests
import lmslib
import sys
import time
import uuid
import logging
import json
import os
import random
import string
from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)

"""
NOTES:
===============================================================

Get shipment that are not notified to store yet

[createUploadJob]
Create a job and record the job details in a feed record

[uploadFile]
Create the xml file and upload the job. Mark the feed record as uploaded

[startUploadJob]
Start processing the file. Mark the feed as in progress

[getJobStatus]
Get the status of the job. Mark the feed as either error or done. If done, mark the related shipments True for notified store field.
"""


class OnlineStore(models.Model):
    _inherit = 'sale.store'

    ebay_dev_id = fields.Char("Developer Key", required_if_site='ebay')
    ebay_token = fields.Text("Token", required_if_site='ebay')
    ebay_app_id = fields.Char("App Key", required_if_site='ebay')
    ebay_cert_id = fields.Char("Cert Key", required_if_site='ebay')
    ebay_site_id = fields.Integer("Site ID")
    ebay_domain = fields.Selection([('prod', 'Production'), ('sand', 'Sandbox')], string='Site', default='sand', required_if_site='ebay')
    ebay_title = fields.Text(string='Title', required=True,
        default='''
# Available variables:
#----------------------
# PRODUCTNAME, PARTNUMBER, MODELNAME, MAKENAME, MINYEAR, MAXYEAR
# Note: returned value have to be set in the variable 'result'

result = 'New ' + PRODUCTNAME + ' for ' + MODELNAME + ' ('+ MINYEAR + ' to ' + MAXYEAR + ')'
'''
)
    ebay_description = fields.Text(string='Title', required=True,
        default='''
# Available variables:
#----------------------
# PRODUCTNAME, PARTNAME, STORENAME
# Note: returned value have to be set in the variable 'result'

result = """
<div align="center">
    <span style="font-size: 14pt">
        <strong>Take care of all your %s needs with this high quality %s.  Each %s %s is made with the highest materials to ensure proper fit, function, and performance the first time!</strong>
    </span>
</div>
<hr />
""" %(PARTNAME, PRODUCTNAME, STORENAME, PRODUCTNAME)
''')
    ebay_paypal = fields.Char(string="Paypal E-mail Address")
    ebay_dispatch_time = fields.Integer(string="Max Dispatch Time", default="1")
    ebay_use_tax_table = fields.Boolean(string="Use Tax Table?")
    ebay_returns_accepted_option = fields.Boolean(string="Accept Returns", default=True)
    ebay_refund_option = fields.Selection([
        ('MoneyBack', 'Money Back'),
        ('MoneyBackOrExchange', 'Money Back or Exchange'),
        ('MoneyBackOrReplacement', 'Money Back or Replacement')
        ], string="Refund Options", default='MoneyBack')
    ebay_returns_within_option = fields.Selection([
        ('Days_14', '14 Days'),
        ('Days_30', '30 Days'),
        ('Days_60', '60 Days'),
        ('Months_1', '1 Month'),
        ], string="Returns Within", default='Days_30')
    ebay_shipping_cost_paid_by = fields.Selection([
        ('Buyer', 'Buyer'),
        ('Seller', 'Seller')
        ], string="Shipping Cost to be Paid By", default='Buyer')
    ebay_return_description = fields.Char(string="Return Policy Description")
    ebay_warranty = fields.Selection([
        ('No Warranty', 'No Warranty'),
        ('Unspecified Length', 'Unspecified Length'),
        ('90 Day', '90 Days'),
        ('6 Month', '6 Months'),
        ('1 Year', '1 Year'),
        ('2 Year', '2 Years'),
        ('3 Year', '3 Years'),
        ('5 Year', '5 Years'),
        ('10 Year', '10 Years'),
        ('Lifetime', 'Lifetime'),
        ('Other', 'Other')
        ], 'Warranty')
    ebay_min_quantity = fields.Integer('Min Quantity')
    ebay_max_quantity = fields.Integer('Max Quantity')
    ebay_pricing_formula = fields.Text(string='Pricing Formula', required=True,
        default='''
# Available variables:
#----------------------
# COST
# Note: returned value have to be set in the variable 'result'

result = COST * 1.2
'''
)
    ebay_brand = fields.Char('Brand')
    ebay_rate = fields.Float('Rate',  digits=dp.get_precision('Product Price'))
    ebay_last_record_number = fields.Integer('Last Record Number')
    is_external_store = fields.Boolean('External store', default=False)
    http_proxy = fields.Char('HTTP proxy', help='Leave it empty for regular stores.')
    http_port = fields.Char('HTTP port', help='Leave it empty for regular stores.')
    https_proxy = fields.Char('HTTPS proxy', help='For eBay we need HTTPS. Leave it empty for regular stores.')
    https_port = fields.Char('HTTPS port', help='For eBay we need HTTPS. Leave it empty for regular stores.')

    @api.multi
    def ebay_submit_tracking_number(self, now):
        self.ensure_one()
        # Do not create a new feed if there is an existing pending feed
        feed_ids = self.env['sale.store.feed'].search([('state', 'in', ['draft', 'submitted', 'in_progress']),('store_id.id', '=', self.id),('job_type', '=', 'SetShipmentTrackingInfo')])
        if feed_ids:
            return

        picking_ids = self.env['stock.picking'].search([('store_notified', '=', False), ('sale_id.store_id.id', '=', self.id), ('tracking_number', '!=', False), ('shipping_state', '!=', 'error')])
        vendor_shipment_ids = self.env['sale.shipment.from.vendor'].search([('store_notified', '=', False), ('sale_id.store_id.id', '=', self.id), ('tracking_number', '!=', False), ('shipping_state', '!=', 'error')])
        if not (vendor_shipment_ids or vendor_shipment_ids):
            return

        xml_body = ""
        string_ids = ""
        for picking in picking_ids:
            string_ids += str(picking.tracking_number) + ','
            xml_body += "<SetShipmentTrackingInfoRequest xmlns='urn:ebay:apis:eBLBaseComponents'>"
            xml_body += "<OrderID>{OrderID}</OrderID>".format(OrderID=picking.sale_id.web_order_id)
            xml_body += "<OrderLineItemID>{OrderLineItemID}</OrderLineItemID>".format(OrderLineItemID=picking.sale_id.order_line[0].web_orderline_id)
            xml_body += "<Shipment>"
            xml_body += "<ShippedTime>{ShippedTime}</ShippedTime>".format(ShippedTime=now.strftime('%Y-%m-%d'+'T'+'%H:%M:%S'+'.000Z'))
            xml_body += "<ShipmentTrackingDetails>"
            xml_body += "<ShippingCarrierUsed>{ShippingCarrierUsed}</ShippingCarrierUsed>".format(ShippingCarrierUsed=picking.carrier_id.name)
            xml_body += "<ShipmentTrackingNumber>{ShipmentTrackingNumber}</ShipmentTrackingNumber>".format(ShipmentTrackingNumber=shipment.tracking_number)
            xml_body += "</ShipmentTrackingDetails>"
            xml_body += "</Shipment>"
            xml_body += "</SetShipmentTrackingInfoRequest>"

        for shipment in vendor_shipment_ids:
            string_ids += str(shipment.tracking_number) + ','
            xml_body += "<SetShipmentTrackingInfoRequest xmlns='urn:ebay:apis:eBLBaseComponents'>"
            xml_body += "<OrderID>{OrderID}</OrderID>".format(OrderID=shipment.sale_id.web_order_id)
            xml_body += "<OrderLineItemID>{OrderLineItemID}</OrderLineItemID>".format(OrderLineItemID=shipment.sale_id.order_line[0].web_orderline_id)
            xml_body += "<Shipment>"
            xml_body += "<ShippedTime>{ShippedTime}</ShippedTime>".format(ShippedTime=now.strftime('%Y-%m-%d'+'T'+'%H:%M:%S'+'.000Z'))
            xml_body += "<ShipmentTrackingDetails>"
            xml_body += "<ShippingCarrierUsed>{ShippingCarrierUsed}</ShippingCarrierUsed>".format(ShippingCarrierUsed=shipment.carrier_id.name)
            xml_body += "<ShipmentTrackingNumber>{ShipmentTrackingNumber}</ShipmentTrackingNumber>".format(ShipmentTrackingNumber=shipment.tracking_number)
            xml_body += "</ShipmentTrackingDetails>"
            xml_body += "</Shipment>"
            xml_body += "</SetShipmentTrackingInfoRequest>"
        xml = "<?xml version='1.0' encoding='UTF-8'?>"
        xml += "<BulkDataExchangeRequests>"
        xml += "<Header>"
        xml += "<Version>1</Version>"
        xml += "<SiteID>0</SiteID>"
        xml += "</Header>"
        xml += xml_body
        xml += "</BulkDataExchangeRequests>"

        environment = 'sandbox' if self.ebay_domain == 'sand' else 'production'
        ebay_api = lmslib.CreateUploadJob(environment,
                       application_key=self.ebay_app_id,
                       developer_key=self.ebay_dev_id,
                       certificate_key=self.ebay_cert_id,
                       auth_token=self.ebay_token)
        build_uuid = uuid.uuid4()
        ebay_api.buildRequest('SetShipmentTrackingInfo', 'gzip', build_uuid)
        ebay_api.sendRequest()
        response, resp_struct = ebay_api.getResponse()

        if response == 'Success':
            jobId = resp_struct.get( 'jobId', None )
            fileReferenceId = resp_struct.get( 'fileReferenceId', None )
            if not jobId or not fileReferenceId:
                _logger.error("createUploadJob Error: couldn't obtain jobId or fileReferenceId")
            else:
                self.env['sale.store.feed'].create({
                    'name':  '%s-eBay-' %str(self.id) + now.strftime('%Y-%m-%d-%H-%M-%S'),
                    'submission_id': jobId,
                    'file_reference_id': fileReferenceId,
                    'date_submitted': now.strftime('%Y-%m-%d %H:%M:%S'),
                    'job_type': 'SetShipmentTrackingInfo',
                    'store_id': self.id,
                    'content': xml,
                    'related_ids': string_ids[:-1]
                })
        elif response == 'Failure':
            _logger.error("createUploadJob Error[%s]: %s" %(resp_struct.get('errorId', None), resp_struct.get('message', None)))
        else:
            _logger.error("createUploadJob Error: Something really went wrong here.")

    @api.multi
    def ebay_execute(self, verb, data=None, list_nodes=[], verb_attrs=None, files=None, raise_exception=False):
        self.ensure_one()
        if self.ebay_domain == 'sand':
            domain = 'api.sandbox.ebay.com'
        else:
            domain = 'api.ebay.com'
        if self.is_external_store:
            ok = self.test_proxy()
            if not ok:
                _logger.error('Store has proxy but proxy is not working!')
                return
            else:
                ebay_api = Trading(domain=domain,
                                   https=True,
                                   proxy_host=self.https_proxy,
                                   proxy_port=self.https_port,
                                   config_file=None,
                                   appid=self.ebay_app_id,
                                   devid=self.ebay_dev_id,
                                   certid=self.ebay_cert_id,
                                   token=self.ebay_token,
                                   siteid=str(self.ebay_site_id))
        else:
            ebay_api = Trading(domain=domain,
                               config_file=None,
                               appid=self.ebay_app_id,
                               devid=self.ebay_dev_id,
                               certid=self.ebay_cert_id,
                               token=self.ebay_token,
                               siteid=str(self.ebay_site_id))
        try:
            return ebay_api.execute(verb, data, list_nodes, verb_attrs, files)
        except ConnectionError as e:
            errors = e.response.dict()['Errors']
            if not raise_exception:
                _logger.error(e)
                return
            if not isinstance(errors, list):
                errors = [errors]
            error_message = ''
            for error in errors:
                if error['SeverityCode'] == 'Error':
                    error_message += error['LongMessage']
            if 'Condition is required for this category.' in error_message:
                error_message += _('Or the condition is not compatible with the category.')
            if any(s in error for s in ['Internal error to the application', 'Internal application error']):
                error_message = _('eBay is unreachable. Please try again later.')
            if 'Invalid Multi-SKU item id supplied with variations' in error_message:
                error_message = _('Impossible to revise a listing into a multi-variations listing.\n Create a new listing.')
            if 'UPC is missing a value.' in error_message:
                error_message = _('The UPC value (the barcode value of your product) is not valid by using the checksum.')
            if 'must have a quantity greater than 0' in error_message:
                error_message += _(" If you want to set quantity to 0, the Out Of Stock option should be enabled"
                                  " and the listing duration should set to Good 'Til Canceled")
            if 'Item Specifics entered for a Multi-SKU item should be different' in error_message:
                error_message = _(" You need to have at least 2 variations selected for a multi-variations listing.\n"
                                   " Or if you try to delete a variation, you cannot do it by unselecting it."
                                   " Setting the quantity to 0 is the safest method to make a variation unavailable.")
            raise UserError(_("Error Encountered.\n'%s'") % (error_message,))

    @api.multi
    def ebay_getorder(self, now, minutes_ago, page=1, saved=0):
        slack_critical_channel_id = self.env['ir.config_parameter'].get_param('slack_critical_channel_id')
        self.ensure_one()
        orders_saved = saved if saved else 0
        mod_time_from = (now - timedelta(minutes=minutes_ago)).strftime('%Y-%m-%d'+'T'+'%H:%M:%S'+'.000Z')
        mod_time_to = now.strftime('%Y-%m-%d'+'T'+'%H:%M:%S'+'.000Z')
        orders = self.ebay_execute('GetOrders', {'ModTimeFrom': mod_time_from,
                                                 'ModTimeTo': mod_time_to,
                                                 'OrderStatus': 'Completed',
                                                 'Pagination': {'EntriesPerPage': 10, 'PageNumber': page}}).dict()
        if orders['OrderArray']:
            for order in orders['OrderArray']['Order']:
                order_id = order['OrderID']
                record_id = order['ShippingDetails']['SellingManagerSalesRecordNumber']
                if self.code == 'visionary' and int(record_id) < 1146:
                    continue
                elif self.code == 'rhino' and int(record_id) < 32926:
                    continue
                elif self.code == 'revive' and int(record_id) < 40161:
                    continue
                elif self.code == 'ride' and int(record_id) < 8541:
                    continue
                sale_order_id = self.env['sale.order'].search([('store_id.id', '=', self.id), '|', ('web_order_id', '=', order_id), ('web_order_id', '=', record_id)])
                if not sale_order_id:
                    try:
                        logging.info('Saving %s order', self.code)
                        self.ebay_saveorder(order)
                    except Exception as e:
                        logging.info('Error: %s', e)
                        attachment = {
                            'color': '#DC3545',
                            'fallback': 'Cant save order',
                            'title': 'Cant save order',
                            'text': 'Store: %s Order data: %s' % (self.name, order)
                        }
                        self.env['slack.calls'].notify_slack('Cant save order!', 'Error', slack_critical_channel_id, attachment)
                    orders_saved += 1
        if orders['HasMoreOrders'] == 'true':
            return self.ebay_getorder(now, minutes_ago, page + 1, orders_saved)
        return orders_saved

    @api.multi
    def ebay_get_order_by_order_id(self, order_id, now):
        self.ensure_one()
        order = self.ebay_execute('GetOrders', {'OrderIDArray': [{'OrderID': order_id}], 'DetailLevel': 'ReturnAll'}).dict()
        new_so = False
        if order['OrderArray']:
            for order in order['OrderArray']['Order']:
                new_so = self.ebay_saveorder(order)
        return new_so

    @api.multi
    def ebay_get_created_shipment_job_list(self):
        self.ensure_one()
        environment = 'sandbox' if self.ebay_domain == 'sand' else 'production'
        ebay_api = lmslib.GetJobs(environment,
                       application_key=self.ebay_app_id,
                       developer_key=self.ebay_dev_id,
                       certificate_key=self.ebay_cert_id,
                       auth_token=self.ebay_token)
        ebay_api.buildRequest(jobType='AddItem', jobStatus='Created')
        ebay_api.sendRequest()
        response, resp_struct = ebay_api.getResponse()
        if response == 'Success':
            print json.dumps(resp_struct)
            self.env['sale.store.log'].create({
                    'name': 'eBay - getJobs - SetShipmentTrackingInfo',
                    'description': self.name,
                    'result': json.dumps(resp_struct)
                })

    @api.model
    def ebay_cron_abort_job(self, code, job_id):
        store_id = self.search([('code', '=', code), ('site', '=', 'ebay')])
        store_id.ensure_one()
        environment = 'sandbox' if store_id.ebay_domain == 'sand' else 'production'
        ebay_api = lmslib.AbortJob(environment,
                       application_key=store_id.ebay_app_id,
                       developer_key=store_id.ebay_dev_id,
                       certificate_key=store_id.ebay_cert_id,
                       auth_token=store_id.ebay_token)
        ebay_api.buildRequest(job_id)
        ebay_api.sendRequest()
        response, resp_struct = ebay_api.getResponse()

        if response == 'Success':
            self.env['sale.store.log'].create({
                'name': 'eBay - abortJob - {job_id}'.format(job_id=job_id),
                'description': store_id.name,
                'result': json.dumps(resp_struct)
            })

    @api.model
    def ebay_cron_get_created_shipment_job_list(self):
        for store_id in self.search([('enabled', '=', True),('site', '=', 'ebay')]):
            store_id.ebay_get_created_shipment_job_list()

    @api.model
    def ebay_cron_upload_file(self):
        feed_ids = self.env['sale.store.feed'].search([('state', '=', 'draft'),('store_id.site', '=', 'ebay')])
        for feed_id in feed_ids:
            filename = '/var/tmp/' + feed_id.name + '.xml'
            file = open(filename, 'wb')
            file.write(feed_id.content)
            file.seek(0)
            file.close()
            store_id = feed_id.store_id
            environment = 'sandbox' if store_id.ebay_domain == 'sand' else 'production'
            ebay_api = lmslib.UploadFile(environment,
                       application_key=store_id.ebay_app_id,
                       developer_key=store_id.ebay_dev_id,
                       certificate_key=store_id.ebay_cert_id,
                       auth_token=store_id.ebay_token)
            ebay_api.buildRequest(feed_id.submission_id, feed_id.file_reference_id, filename )
            response = ebay_api.sendRequest()
            response, response_dict = ebay_api.getResponse()
            if response == 'Success':
                feed_id.write({'state': 'submitted'})
            else:
                'ERROR %s' %json.dumps(response_dict)

    @api.model
    def ebay_cron_start_job(self):
        feed_ids = self.env['sale.store.feed'].search([('state', '=', 'submitted'),('store_id.site', '=', 'ebay')])
        for feed_id in feed_ids:
            store_id = feed_id.store_id
            environment = 'sandbox' if store_id.ebay_domain == 'sand' else 'production'
            ebay_api = lmslib.StartUploadJob(environment,
                       application_key=store_id.ebay_app_id,
                       developer_key=store_id.ebay_dev_id,
                       certificate_key=store_id.ebay_cert_id,
                       auth_token=store_id.ebay_token)
            ebay_api.buildRequest(feed_id.submission_id)
            response = ebay_api.sendRequest()
            response, response_dict = ebay_api.getResponse()
            if response == 'Success':
                feed_id.write({'state': 'in_progress'})
            else:
                _logger.error('ERROR %s' % json.dumps(response_dict))

    @api.model
    def ebay_cron_get_job_status(self):
        feed_ids = self.env['sale.store.feed'].search([('state', '=', 'in_progress'),('store_id.site', '=', 'ebay')])
        for feed_id in feed_ids:
            store_id = feed_id.store_id
            environment = 'sandbox' if store_id.ebay_domain == 'sand' else 'production'
            ebay_api = lmslib.GetJobStatus(environment,
                       application_key=store_id.ebay_app_id,
                       developer_key=store_id.ebay_dev_id,
                       certificate_key=store_id.ebay_cert_id,
                       auth_token=store_id.ebay_token)
            ebay_api.buildRequest(feed_id.submission_id)
            response = ebay_api.sendRequest()
            response, response_dict = ebay_api.getResponse()
            if response == 'Success':
                if response_dict[0].get('jobStatus',None) == 'Completed':
                    feed_id.write({'state': 'done'})
                    string_ids = feed_id.related_ids.split(",")
                    tracking_numbers = []
                    for string_id in string_ids:
                        tracking_numbers.append(int(string_id))
                    for picking in self.env['stock.picking'].search([('tracking_number', 'in', tracking_numbers)]):
                        picking.write({'store_notified': True})
                    for shipment in self.env['sale.shipment.from.vendor'].search([('tracking_number', 'in', tracking_numbers)]):
                        shipment.write({'store_notified': True})
            else:
                _logger.error('ERROR %s' % json.dumps(response_dict))

    @api.multi
    def compute_engine(self, c):
        result =''
        if c['Liter'] != '-':
            result += c['Liter'] + 'L '
        if c['CC'] != '-':
            result += c['CC'] + 'CC '
        if c['CID'] != '-':
            result += c['CID'] + 'Cu. In. '
        if c['BlockType'] == 'L':
            result += 'l'
        else:
            result += c['BlockType']
        result += c['Cylinders']
        if c['FuelTypeName'] not in ['U/K', 'N/R', 'N/A']:
            result += ' ' + c['FuelTypeName']
        if c['CylinderHeadTypeName'] not in ['U/K', 'N/R', 'N/A']:
            result += ' ' + c['CylinderHeadTypeName']
        if c['AspirationName'] != '-':
            result += ' ' + c['AspirationName']
        # Special exceptions
        if c['FuelTypeName'] == 'ELECTRIC' and c['BlockType'] == '-' and c['Cylinders'] == '-':
            result = 'ELECTRIC'
        elif c['Liter'] == '-' and c['CID'] == '-' and c['BlockType'] == '-' and c['Cylinders'] == '-':
            result = '-CC -Cu. In. -- -'
        return result

    @api.model
    def get_main_product_details(self, inventory_id):
        return self.env['sale.order'].autoplus_execute("""
            SELECT
            INV.ProdName,
            INV.PartNo,
            INV.MfgLabel,
            PR.ListPrice
            FROM Inventory INV
            LEFT JOIN InventoryMiscPrCur PR on INV.InventoryID = PR.InventoryID
            WHERE INV.InventoryID = %s
        """ % (inventory_id, ))

    @api.model
    def get_custom_label(self, inventory_id):
        mfg_code_result = self.env['sale.order'].autoplus_execute("""
            SELECT
            INV.PartNo,
            INV.MfgID
            FROM Inventory INV
            WHERE INV.InventoryID = %s
        """ %(inventory_id,))

        sku = mfg_code_result[0]['PartNo']

        if mfg_code_result[0]['MfgID'] != 1:
            ase_sku_result = self.env['sale.order'].autoplus_execute("""
                SELECT
                INV2.PartNo
                FROM Inventory INV
                LEFT JOIN InventoryAlt ALT on ALT.InventoryID = INV.InventoryID
                LEFT JOIN Inventory INV2 on ALT.InventoryIDAlt = INV2.InventoryID
                WHERE INV.InventoryID = %s AND INV2.MfgId = 1
            """ %(inventory_id,))
            if ase_sku_result:
                sku = ase_sku_result[0]['PartNo']
        return sku

    @api.model
    def get_category_id(self, inventory_id):
        return self.env['sale.order'].autoplus_execute("""
            SELECT TOP 1 INV.InventoryID, PCP.pcPartName, PCP.eBayCatID FROM Inventory INV
            LEFT JOIN InventoryPC IPC on IPC.InventoryID = INV.InventoryID
            LEFT JOIN pc PC on IPC.pcID = PC.pcID
            LEFT JOIN pcPART PCP on PC.pcPartID = PCP.pcPartID
            WHERE INV.InventoryID = %s AND PCP.eBayCatID IS NOT NULL
        """ % (inventory_id, ))

    @api.model
    def get_qty_and_price(self, inventory_id):
        return self.env['sale.order'].autoplus_execute("""
            SELECT INV.QtyOnHand, PR.Cost
            FROM Inventory INV
            LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
            WHERE INV.InventoryID = %s AND INV.QtyOnHand > 0
            """
            % (inventory_id, ))

    @api.model
    def get_vehicles(self, inventory_id):
        return self.env['sale.order'].autoplus_execute("""
            SELECT
            VEH.YearID,
            VEH.MakeName,
            VEH.ModelName,
            VEH.Trim,
            ENG.EngineID,
            ENG.Liter,
            ENG.CC,
            ENG.CID,
            ENG.BlockType,
            ENG.Cylinders,
            ENG.CylinderHeadTypeName,
            ENG.FuelTypeName,
            ENG.AspirationName
            FROM Inventory INV
            LEFT JOIN InventoryVcVehicle IVEH on INV.InventoryID = IVEH.InventoryID
            LEFT JOIN VcVehicle VEH on IVEH.VehicleID = VEH.VehicleID
            LEFT JOIN vcVehicleEngine VENG on VEH.VehicleID = VENG.VehicleID
            LEFT JOIN vcEngine ENG on VENG.EngineID = ENG.EngineID
            WHERE INV.InventoryID = %s
            ORDER BY VEH.YearID
        """ % (inventory_id, ))

    @api.model
    def get_picture_urls(self, inventory_id):
        return self.env['sale.order'].autoplus_execute("""
            SELECT
            ASST.URI
            FROM Inventory INV
            LEFT JOIN InventoryPiesASST ASST on INV.InventoryID = ASST.InventoryID
            WHERE INV.InventoryID = %s
        """ %(inventory_id,))

    @api.multi
    def ebay_prepare_item_dict(self, inventory_id, params=None, raise_exception=False):
        self.ensure_one()

        alt_ids = []
        alt_rows = self.env['product.template'].get_alt_products_from_autoplus_by_inventory_id(inventory_id)
        for row in alt_rows:
            alt_ids.append(row['InventoryIDAlt'])

        main_product_details = self.get_main_product_details(inventory_id)

        if not main_product_details[0]['ProdName']:
            for alt_id in alt_ids:
                prod_name_res = self.get_main_product_details(inventory_id)
                if prod_name_res[0]['ProdName']:
                    main_product_details[0]['ProdName'] = prod_name_res[0]['ProdName']
                    break
            else:
                if 'product_name' in params and params['product_name']:
                    main_product_details[0]['ProdName'] = params['product_name']
                elif raise_exception:
                    raise UserError('Product Name is not specified.')
                else:
                    _logger.error("Error in listing SKU %s to %s: Product Name is not specified." %(inventory_id, self.name))
                    return False

        category_id = self.get_category_id(inventory_id)
        if not (category_id and category_id[0]['eBayCatID']):
            for alt_id in alt_ids:
                category_id = self.get_category_id(alt_id)
                if category_id and category_id[0]['eBayCatID']:
                    break
            else:
                if 'ebay_category_id' in params and params['ebay_category_id']:
                    category_id = [{'eBayCatID': params['ebay_category_id']}]
                elif raise_exception:
                    raise UserError(_('Category ID is not specified.'))
                else:
                    _logger.error("Error in listing SKU %s to %s: Category ID is not specified." %(inventory_id, self.name))
                    return False

        sku = self.get_custom_label(inventory_id)

        qty_and_price = self.get_qty_and_price(inventory_id)

        manual_pricing = False
        if not (qty_and_price and qty_and_price[0]['Cost']):
            if 'quantity' in params and params['quantity'] and 'price' in params and params['price']:
                manual_pricing = True
                qty_and_price = [{'QtyOnHand': params['quantity']}]
                StartPrice = params['price']
            elif raise_exception:
                raise UserError(_("Pricing Error."))
            else:
                _logger.error("Error in listing SKU %s to %s: Pricing error." %(inventory_id, self.name))
                return False

        interchange_values = self.env['sale.order'].autoplus_execute("""
            SELECT
            INTE.PartNo,
            INTE.BrandID
            FROM Inventory INV
            LEFT JOIN InventoryPiesINTE INTE on INTE.InventoryID = INV.InventoryID
            WHERE INV.InventoryID = %s
            """ % (inventory_id, ))

        ItemSpecifics = {'NameValueList': [] }
        partslink = ''
        if interchange_values:
            oem_part_number = ''
            parsed_interchange_values = ''
            for i in interchange_values:
                if i['PartNo']:
                    if i['BrandID'] == 'FLQV':
                        partslink = i['PartNo']
                    if i['BrandID'] == 'OEM':
                        oem_part_number = i['PartNo']
                    else:
                        parsed_interchange_values += i['PartNo'] + ', '

            if oem_part_number:
                ItemSpecifics['NameValueList'].append({
                    'Name': 'Manufacturer Part Number', 'Value': oem_part_number
                })
            if parsed_interchange_values:
                ItemSpecifics['NameValueList'].append({
                    'Name': 'Interchange Part Number', 'Value': parsed_interchange_values[:-2]
                })

        if partslink:
            ItemSpecifics['NameValueList'].append({
                'Name': 'Partlink Number', 'Value': partslink
            })

        if self.ebay_brand:
            ItemSpecifics['NameValueList'].append({
                'Name': 'Brand', 'Value': self.ebay_brand
            })
        if self.ebay_warranty:
            ItemSpecifics['NameValueList'].append({
                'Name': 'Warranty', 'Value': self.ebay_warranty
            })

        ItemSpecifics['NameValueList'].append({
            'Name': 'Manufacturer Part Number', 'Value': partslink or oem_part_number or ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        })

        vehicles = self.get_vehicles(inventory_id)
        if not (vehicles[0]['MakeName'] and vehicles[0]['ModelName'] and vehicles[0]['YearID']):
            for alt_id in alt_ids:
                vehicles = self.get_vehicles(alt_id)
                if vehicles[0]['MakeName'] and vehicles[0]['ModelName'] and vehicles[0]['YearID']:
                    break
            else:
                if raise_exception:
                    raise UserError(_('No fitments found.'))
                _logger.error("Error in listing SKU %s to %s: No fitments found." % (inventory_id, self.name))
                return False

        picture_urls = self.get_picture_urls(inventory_id)
        if not (picture_urls and picture_urls[0]['URI']):
            for alt_id in alt_ids:
                picture_urls = self.get_picture_urls(alt_id)
                if picture_urls and picture_urls[0]['URI']:
                    break
            else:
                if 'image_url' in params and params['image_url']:
                    picture_urls = [{'URI': params['image_url']}]
                    print '%s' % picture_urls
                elif raise_exception:
                    raise UserError(_('No images found.'))
                else:
                    _logger.error("Error in listing SKU %s to %s: No images found." %(inventory_id, self.name))
                    return False

        titlelocaldict = dict(
            PRODUCTNAME=main_product_details[0]['ProdName'].replace("&", "&amp;"),
            PARTSLINK=partslink,
            MAKENAME=vehicles[0]['MakeName'].replace("&", "&amp;"),
            MODELNAME=vehicles[0]['ModelName'].replace("&", "&amp;"),
            MINYEAR=str(vehicles[0]['YearID']),
            MAXYEAR=str(vehicles[-1]['YearID'])
        )

        Title = ""
        try:
            safe_eval(self.ebay_title, titlelocaldict, mode='exec', nocopy=True)
            Title = titlelocaldict['result']
        except:
            if raise_exception:
                raise UserError(_('Wrong python code defined for Title.'))
            _logger.error("Error in listing SKU %s to %s: Wrong python code for Title." %(inventory_id, self.name))
            return False

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')

        logo = ''
        if self.image:
            logo = base_url + '/web/image?model=sale.store&id=%s&field=image' %self.id

        PictureURL = []
        picture_counter = 1
        for p in picture_urls:
            if picture_counter > 12:
                break
            if p['URI'] != None:
                PictureURL.append(p['URI'])
            picture_counter += 1
        if PictureURL:
            PictureDetails = { 'PictureURL': PictureURL }

        desclocaldict=dict(
            MFGLABEL=main_product_details[0]['MfgLabel'].replace("&", "&amp;"),
            PRODUCTNAME=main_product_details[0]['ProdName'].replace("&", "&amp;"),
            STORENAME=self.name,
            BRAND=self.ebay_brand,
            TITLE=Title,
            INTERCHANGE=parsed_interchange_values[:-2],
            LOGO=logo,
            MAINIMAGE=PictureURL[0] if PictureURL else '',
            OTHERIMAGES=PictureURL[1:] if len(PictureURL) > 1 else []
        )

        for i in self.image_ids:
            desclocaldict[i.code] = base_url + '/web/image?model=sale.store.image&id=%s&field=image' %i.id

        Description = ""
        try:
            safe_eval(self.ebay_description, desclocaldict, mode='exec', nocopy=True)
            Description = desclocaldict['result']
        except:
            if raise_exception:
                raise UserError(_('Wrong python code defined for Description.'))
            _logger.error("Error in listing SKU %s to %s: Wrong python code for description." %(inventory_id, self.name))
            return False

        if not manual_pricing:
            pricelocaldict = dict(
                COST=float(qty_and_price[0]['Cost'])
            )
            try:
                safe_eval(self.ebay_pricing_formula, pricelocaldict, mode='exec', nocopy=True)
                StartPrice = pricelocaldict['result']
            except:
                if raise_exception:
                    raise UserError(_('Wrong python code defined for Pricing Formula.'))
                _logger.error("Error in listing SKU %s to %s: Wrong python code for pricing formula." %(inventory_id, self.name))
                return False

        item_dict = {
            'Title': Title,
            'PrimaryCategory': {
                'CategoryID': category_id[0]['eBayCatID']
            },
            'SKU': sku,
            'CategoryMappingAllowed': True,
            'StartPrice': StartPrice,
            'ListingType': 'FixedPriceItem',
            'ListingDuration': 'GTC',
            'Country': 'US',
            'Currency': 'USD',
            'Quantity': min(qty_and_price[0]['QtyOnHand'], self.ebay_max_quantity),
            'ConditionID': 1000,
            'PaymentMethods': 'PayPal',
            'PayPalEmailAddress': self.ebay_paypal,
            'AutoPay': True,
            'Location': 'United States',
            'DispatchTimeMax': self.ebay_dispatch_time,
            'UseTaxTable': True,
            'Description': "<![CDATA[" + Description + "]]>",
            'PictureDetails': PictureDetails,
            'ShippingDetails': {
                'ShippingType': 'Flat',
                'ShippingServiceOptions': {
                    'ShippingServicePriority': 1,
                    'ShippingService': 'ShippingMethodStandard',
                    'ShippingTimeMax': 5,
                    'ShippingTimeMin': 1,
                    'FreeShipping': True
                }
            },
            'ReturnPolicy': {
                'ReturnsAcceptedOption': 'ReturnsAccepted' if self.ebay_returns_accepted_option else 'ReturnsNotAccepted',
                'RefundOption': self.ebay_refund_option,
                'ReturnsWithinOption': self.ebay_returns_within_option,
                'Description': self.ebay_return_description ,
                'ShippingCostPaidByOption': self.ebay_shipping_cost_paid_by
            }
        }

        item_dict['ItemSpecifics'] = ItemSpecifics

        ItemCompatibilityList = {'Compatibility': []}
        for c in vehicles:
            Note = ''
            row = {'CompatibilityNotes': Note,
                'NameValueList': [
                    {'Name': 'Make', 'Value': c['MakeName'].replace("&", "&amp;") if c['MakeName'] else '' },
                    {'Name': 'Model', 'Value': c['ModelName'].replace("&", "&amp;") if c['ModelName'] else ''},
                    {'Name': 'Year', 'Value': str(c['YearID'])},
                ]}
            if c['Trim']:
                row['NameValueList'].append(
                    {'Name': 'Trim', 'Value': c['Trim'].replace("&", "&amp;") }
                )
            if c['EngineID']:
                Engine = self.compute_engine(c)
                row['NameValueList'].append(
                    {'Name': 'Engine', 'Value': Engine }
                )
            ItemCompatibilityList['Compatibility'].append(row)
        if vehicles:
            item_dict['ItemCompatibilityList'] = ItemCompatibilityList
        return item_dict

    @api.multi
    def ebay_list_new_product(self, now, product_tmpl, params, raise_exception=True):
        self.ensure_one()
        item_dict = self.ebay_prepare_item_dict(product_tmpl.inventory_id, params=params, raise_exception=raise_exception)
        if item_dict:
            listed_item = self.ebay_execute('AddFixedPriceItem', {'Item': item_dict}, raise_exception=True)
            try:
                listed_item = listed_item.dict()
                if 'ItemID' in listed_item:
                    self.env['product.listing'].create({
                        'name': listed_item['ItemID'],
                        'product_tmpl_id': product_tmpl.id,
                        'store_id': self.id
                    })
                    self.env.cr.commit()
                    _logger.info("New eBay Item Listed in %s, ItemID %s" % (self.name, listed_item['ItemID']))
            except Exception as e:
                if raise_exception:
                    raise UserError("Error: %s \n%s" % (listed_item, e))
                else:
                    _logger.error("eBay listing duplicate on store %s for SKU %s" % (self.name, product_tmpl.inventory_id))

    @api.model
    def ebay_update_quantities(self, now, page=1, item_ids_to_update=[]):
        result = self.ebay_execute('GetMyeBaySelling', {
            'ActiveList': {
                'Include': True,
                'Pagination': {'EntriesPerPage': 20, 'PageNumber': page}
            },
            'DetailLevel': 'ReturnSummary'
        }).dict()
        my_items = result['ActiveList']['ItemArray']['Item']
        if not isinstance(my_items, list):
            my_items = [my_items]
        for item in my_items:
            item_ids_to_update.append(item['ItemID'])
        print 'PAGE %s'
        if page < int(result['ActiveList']['PaginationResult']['TotalNumberOfPages']):
            self.ebay_update_quantities(now, page + 1, item_ids_to_update)

    @api.multi
    def ebay_get_item(self, now, listing):
        self.ensure_one()
        item = self.ebay_execute('GetItem', {
            'ItemID': listing.name,
            'IncludeItemCompatibilityList': True,
            'IncludeItemSpecifics': True,
            'IncludeTaxTable': True,
        }).dict()
        print "QUANTITY IS %s" % json.dumps(item)
        if 'Item' in item:
            print "QUANTITY IS %s" % item['Item']['Quantity']

    @api.multi
    def ebay_end_item(self, now, listing):
        self.ensure_one()
        item = self.ebay_execute('EndFixedPriceItem', {
            'EndingReason': 'NotAvailable',
            'ItemID': listing.name
        }, raise_exception=True)
        listing.write({'state': 'ended'})

    @api.multi
    def ebay_bulk_list_products(self, now, params):
        offset_counter = 0
        while offset_counter < params['number_of_parts_to_list']:
            inventory_ids = []
            result = self.env['sale.order'].autoplus_execute("""
                SELECT INV.InventoryID FROM InventoryMiscPrCur Price
                LEFT JOIN Inventory INV ON INV.InventoryID = Price.InventoryID
                LEFT JOIN InventoryPiesASST ASST ON ASST.InventoryID = Price.InventoryID
                LEFT JOIN InventoryPC INVPC ON INVPC.InventoryID = Price.InventoryID
                LEFT JOIN pc P ON P.pcID = INVPC.pcID
                LEFT JOIN pcPart Part ON Part.pcPartID = P.pcPartID
                WHERE INV.MfgID = 16 AND Price.Cost > 0 AND INV.QtyOnHand > 0
                AND ASST.URI LIKE '%%liveautodata.com%%' AND Part.eBayCatID IS NOT NULL
                ORDER BY InventoryID ASC
                OFFSET %s ROWS
                FETCH NEXT %s ROWS ONLY
            """ %(offset_counter + params['offset'], min(params['number_of_parts_to_list'] - offset_counter, 200)))
            for row in result:
                inventory_ids.append(row['InventoryID'])
            if inventory_ids:
                for i in inventory_ids:
                    product_tmpl = self.env['product.template'].search([('inventory_id', '=', i)])
                    if not product_tmpl:
                        product_tmpl = self.env['product.template'].create({'name': 'New', 'inventory_id': i})
                        product_tmpl.button_sync_with_autoplus()
                    self.ebay_list_new_product(now, product_tmpl, raise_exception=False)
            offset_counter += 200
        _logger.info('Done processing bulk listing.')

    @api.model
    def ebay_bulk_list_products_by_file_upload(self):
        store = self.env['sale.store'].search([('code', '=', 'sandbox')])

        environment = 'sandbox' if store.ebay_domain == 'sand' else 'production'

        ebay_api = lmslib.CreateUploadJob(environment,
                       application_key=store.ebay_app_id,
                       developer_key=store.ebay_dev_id,
                       certificate_key=store.ebay_cert_id,
                       auth_token=store.ebay_token)
        build_uuid = uuid.uuid4()
        ebay_api.buildRequest('AddFixedPriceItem', 'gzip', build_uuid)
        ebay_api.sendRequest()
        response, resp_struct = ebay_api.getResponse()
        if response == 'Success':
            jobId = resp_struct.get( 'jobId', None )
            fileReferenceId = resp_struct.get( 'fileReferenceId', None )
            if not jobId or not fileReferenceId:
                _logger.error("createUploadJob Error: couldn't obtain jobId or fileReferenceId")
            else:
                _logger.info("createUploadJob Success %s %s" %(jobId, fileReferenceId))
        elif response == 'Failure':
            _logger.error("createUploadJob Error[%s]: %s" %(resp_struct.get('errorId', None), resp_struct.get('message', None)))
        else:
            _logger.error("createUploadJob Error: Something really went wrong here.")

        time.sleep(10)

        filename = '/var/tmp/Add.xml'
        # file = open(filename, 'wb')
        # file.write(feed_id.content)
        # file.seek(0)
        # file.close()

        ebay_api = lmslib.UploadFile(environment,
                   application_key=store.ebay_app_id,
                   developer_key=store.ebay_dev_id,
                   certificate_key=store.ebay_cert_id,
                   auth_token=store.ebay_token)
        ebay_api.buildRequest(jobId, fileReferenceId, filename )
        response = ebay_api.sendRequest()
        response, response_dict = ebay_api.getResponse()
        if response == 'Success':
             _logger.info("uploadFile Success")
        else:
            'ERROR %s' %json.dumps(response_dict)

        time.sleep( 10 )

        ebay_api = lmslib.StartUploadJob(environment,
           application_key=store.ebay_app_id,
           developer_key=store.ebay_dev_id,
           certificate_key=store.ebay_cert_id,
           auth_token=store.ebay_token)
        ebay_api.buildRequest(jobId)
        response = ebay_api.sendRequest()
        response, response_dict = ebay_api.getResponse()
        if response == 'Success':
            _logger.info("StartUploadJob Success")
        else:
            _logger.error('ERROR %s' % json.dumps(response_dict))

        time.sleep( 10 )

        ebay_api = lmslib.GetJobStatus(environment,
           application_key=store.ebay_app_id,
           developer_key=store.ebay_dev_id,
           certificate_key=store.ebay_cert_id,
           auth_token=store.ebay_token)
        ebay_api.buildRequest(jobId)
        while True:
            response = ebay_api.sendRequest()
            response, response_dict = ebay_api.getResponse()
            if response == 'Success':
                if response_dict[0].get('jobStatus',None) == 'Completed':
                    _logger.info("COMPLETED!!!")
                    downloadFileId = response_dict[0].get( 'fileReferenceId', None )
                    break
                else:
                    _logger.info("Job is %s complete, trying again in 10 seconds" % response_dict[0].get('percentComplete', None ))
            #Check again in 10 seconds
            time.sleep(10)

        download_file = lmslib.DownloadFile( environment,
           application_key=store.ebay_app_id,
           developer_key=store.ebay_dev_id,
           certificate_key=store.ebay_cert_id,
           auth_token=store.ebay_token )
        download_file.buildRequest( jobId, downloadFileId )

        response = download_file.sendRequest()

        response, resp_struc =  download_file.getResponse()

        if response == 'Success':
            print "Successfully downloaded response!"
            print resp_struc
            print '\n'
        elif response == "Failure":
            print "Failure! downloadFile failed"
            print resp_struc


        # file = open('/var/tmp/AddFixedPriceItems.txt','wb')
        # inventory_ids = []
        # result = self.env['sale.order'].autoplus_execute("""
        #     SELECT INV.InventoryID FROM InventoryMiscPrCur Price
        #     LEFT JOIN Inventory INV ON INV.InventoryID = Price.InventoryID
        #     LEFT JOIN InventoryPiesASST ASST ON ASST.InventoryID = Price.InventoryID
        #     LEFT JOIN InventoryPC INVPC ON INVPC.InventoryID = Price.InventoryID
        #     LEFT JOIN pc P ON P.pcID = INVPC.pcID
        #     LEFT JOIN pcPart Part ON Part.pcPartID = P.pcPartID
        #     WHERE INV.MfgID = 16 AND Price.Cost > 0 AND INV.QtyOnHand > 0 AND ASST.URI LIKE '%%liveautodata.com%%' AND Part.eBayCatID IS NOT NULL
        #     ORDER BY InventoryID
        #     OFFSET %s ROWS
        #     FETCH NEXT %s ROWS ONLY
        # """ %(0, 25))
        # for row in result:
        #     inventory_ids.append(row['InventoryID'])
        # file.write("<AddFixedItemRequest xmlns=\"urn:ebay:apis:eBLBaseComponents\">")
        # if inventory_ids:
        #     counter = 0
        #     for i in inventory_ids:
        #         item_dict = store.ebay_prepare_item_dict(i, raise_exception=False)
        #         xml = "<Item>\n"
        #         xml += dict2xml(item_dict)
        #         xml += "</Item>"
        #         file.write(xml)
        #         counter += 1
        #         print counter
        # file.write("</AddFixedItemRequest>")
        # file.close()

    # Post-Order API
    @api.multi
    def ebay_postorder_execute(self, action, args):
        url = 'https://api.ebay.com/post-order/v2/%s/%s' % (action, args)
        headers = {'Content-Type': 'application/json', 'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US', 'Authorization': 'TOKEN ' + self['ebay_token']}
        if self.is_external_store:
            ok = self.test_proxy()
            if not ok:
                _logger.error('Store has proxy but proxy is not working!')
                return False
            proxy_dict = {
                "https": self.https_proxy + ':' + str(self.https_port)
            }
        else:
            proxy_dict = {}
        response = requests.get(url=url, headers=headers, proxies=proxy_dict)
        return response

    def test_proxy(self):
        proxy_dict = {
            "https": self.https_proxy + ':' + str(self.https_port)
        }

        url = 'https://www.ipinfo.io/'
        r = requests.get(url, proxies=proxy_dict)
        if r.status_code == 200:
            _logger.info('Proxy IP info:%s' % r.text)
        else:
            return False
        return True

    @api.multi
    def ebay_getorderz_test(self, page=1):
        orders = self.ebay_execute('GetOrders', {'CreateTimeFrom': '2019-06-15 00:00:00',
                                                 'CreateTimeTo': '2019-06-15 23:59:59',
                                                 'OrderStatus': 'Completed',
                                                 'Pagination': {'EntriesPerPage': 10, 'PageNumber': page}}).dict()
        if orders['OrderArray']:
            for order in orders['OrderArray']['Order']:
                print order['OrderID'], ' ', order.get('CreatedTime')
        if orders['HasMoreOrders'] == 'true':
            return self.ebay_getorderz_test(page + 1)
