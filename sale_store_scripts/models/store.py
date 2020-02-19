# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import json
import linecache
import uuid

from datetime import datetime

from odoo import models, fields, api
from odoo.addons.sale_store_ebay.models import lmslib
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

class Store(models.Model):
    _inherit = 'sale.store'

    @api.multi
    def get_item_compatibilty_count(self, page, counter):
        self.ensure_one()
        local_counter = 0
        item_list = []
        result = self.ebay_execute('GetMyeBaySelling', {
            'ActiveList': {
                'Include': True,
                'Pagination': {'EntriesPerPage': 200, 'PageNumber': page},
                'Sort': 'ItemID'
            }, 
            'DetailLevel': 'ReturnSummary'
        }).dict()
        my_items = result['ActiveList']['ItemArray']['Item']
        if not isinstance(my_items, list):
            my_items = [my_items]
        for item in my_items:
            get_item = self.ebay_execute('GetItem', {
                'ItemID': item['ItemID'],
                'IncludeItemCompatibilityList': True
            }).dict()
            if 'ItemCompatibilityCount' in get_item['Item']:
                _logger.info("Has fitment data: %s, ItemID %s" %(counter + local_counter, item['ItemID']))
                continue
            else:
                if 'SKU' in item:
                    item_list.append([item['ItemID'], item['SKU'], item['Title']])
                else:
                    item_list.append([item['ItemID'], '', item['Title']])
                _logger.info("Has no fitment data: %s, ItemID %s" %(counter + local_counter, item['ItemID']))
                local_counter += 1
        return local_counter, item_list

    @api.model
    def cron_rhino_get_no_fitment_items(self, page_start):
        store = self.search([('code', '=', 'rhino')])
        store.ensure_one()
        counter = 0
        page = page_start
        # get total pages first
        file = open('/var/tmp/NoFitment.csv', 'wb')
        result = store.ebay_execute('GetMyeBaySelling', {
            'ActiveList': {
                'Include': True,
                'Pagination': {'EntriesPerPage': 200, 'PageNumber': page}
            }, 
            'DetailLevel': 'ReturnSummary'
        }).dict()
        total_pages = int(result['ActiveList']['PaginationResult']['TotalNumberOfPages'])
        while page <= total_pages:
            local_counter, item_list = store.get_item_compatibilty_count(page, counter)
            for item in item_list:
                to_write = "%s;%s;%s\n" %(item[0], item[1], item[2])
                file.write(to_write)
            counter += local_counter
            _logger.info("Process page %s" %(page))
            page += 1
        file.close()

    @api.model
    def cron_rhino_remove_duped_items(self):
        lines = open('/var/tmp/duplicates.csv', 'r').readlines()
        lines_set = set(lines)
        store_id = self.search([('code', '=', 'rhino')])
        store_id.ensure_one()
        for line in lines_set:
            print line[:-1]
            item = store_id.ebay_execute('EndFixedPriceItem', {
                'EndingReason': 'NotAvailable',
                'ItemID': line[:-1]
            }, raise_exception=False)
            _logger.info("Ended Item ID %s" %line)
        _logger.info("DONE")


    @api.model
    def ebay_get_created_job_list(self, code, jobType):
        store_id = self.search([('code', '=', code), ('site', '=', 'ebay')])
        store_id.ensure_one()
        environment = 'sandbox' if store_id.ebay_domain == 'sand' else 'production'
        ebay_api = lmslib.GetJobs(environment,
                       application_key=store_id.ebay_app_id,
                       developer_key=store_id.ebay_dev_id,
                       certificate_key=store_id.ebay_cert_id,
                       auth_token=store_id.ebay_token)
        ebay_api.buildRequest(jobType=jobType)
        ebay_api.sendRequest()
        response, resp_struct = ebay_api.getResponse()
        if response == 'Success':
            _logger.info("Created Jobs on %s: %s" %(code, json.dumps(resp_struct)))

    @api.model
    def ebay_abort_jobs(self, code, job_ids):
        store_id = self.search([('code', '=', code), ('site', '=', 'ebay')])
        store_id.ensure_one()
        environment = 'sandbox' if store_id.ebay_domain == 'sand' else 'production'
        for job_id in job_ids:
            ebay_api = lmslib.AbortJob(environment,
               application_key=store_id.ebay_app_id,
               developer_key=store_id.ebay_dev_id,
               certificate_key=store_id.ebay_cert_id,
               auth_token=store_id.ebay_token)
            ebay_api.buildRequest(job_id)
            ebay_api.sendRequest()
            response, resp_struct = ebay_api.getResponse()
            print json.dumps(resp_struct)
            if response == 'Success':
                _logger.info("Aborted JobID from %s: %s" %(code, job_id))
            else:
                _logger.error("Error aborting job %s: %s" %(code, job_id))

    @api.model
    def ebay_get_active_listings(self, code, from_page, to_page):
        store_id = self.search([('code', '=', code), ('site', '=', 'ebay')])
        store_id.ensure_one()
        counter = 0
        page = from_page
        # get total pages first
        file = open('/var/tmp/ActiveListingsByStartTime_%s_to_%s.txt' %(from_page, to_page), 'wb')
        while page <= to_page:
            _logger.info("Processing %s of %s" %(page, to_page))
            result = store_id.ebay_execute('GetMyeBaySelling', {
                'ActiveList': {
                    'Include': True,
                    'Pagination': {'EntriesPerPage': 200, 'PageNumber': page},
                    'Sort': 'StartTime'
                }, 
                'DetailLevel': 'ReturnSummary'
            }).dict()
            my_items = result['ActiveList']['ItemArray']['Item']
            if not isinstance(my_items, list):
                my_items = [my_items]
            for item in my_items:
                if 'SKU' in item:
                    to_write = "%s;%s;%s\n" %(item['ItemID'], item['SKU'], item['Title'])
                else:
                    to_write = "%s;;%s\n" %(item['ItemID'], item['Title'])
                file.write(to_write)
            _logger.info("PROCESSED %s" %(page))
            page += 1
        file.close()

    @api.model
    def ebay_revise_active_listings(self, code, line_start, line_to):
        store_id = self.search([('code', '=', code), ('site', '=', 'ebay')])
        store_id.ensure_one()
        searchfile = "/var/tmp/ActiveListingsByStartTimeDescending.csv"
        current_line_count = line_start
        while current_line_count <= line_to:
            line = linecache.getline(searchfile, current_line_count)
            list_line = line.split(';')

            item_id = list_line[0]
            inventory_id = list_line[1]

            mfg_code_result = self.env['sale.order'].autoplus_execute("""
                SELECT 
                INV.PartNo,
                INV.MfgID
                FROM Inventory INV
                WHERE INV.InventoryID = %s
            """ %(inventory_id,))

            new_sku = mfg_code_result[0]['PartNo']

            if mfg_code_result[0]['MfgID'] != 1:
                print "NOT ASE"
                ase_sku_result = self.env['sale.order'].autoplus_execute("""
                    SELECT 
                    INV2.PartNo
                    FROM Inventory INV
                    LEFT JOIN InventoryAlt ALT on ALT.InventoryID = INV.InventoryID
                    LEFT JOIN Inventory INV2 on ALT.InventoryIDAlt = INV2.InventoryID
                    WHERE INV.InventoryID = %s AND INV2.MfgId = 1
                """ %(inventory_id,))
                new_sku = ase_sku_result[0]['PartNo']

            qty_and_price = self.env['sale.order'].autoplus_execute("""
                SELECT INV.QtyOnHand, PR.Cost
                FROM Inventory INV
                LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
                WHERE INV.InventoryID = %s
            """ 
            % (inventory_id, ))

            pricelocaldict = dict(
                COST=float(qty_and_price[0]['Cost'])
            )
            try:
                safe_eval(store_id.ebay_pricing_formula, pricelocaldict, mode='exec', nocopy=True)
                StartPrice = pricelocaldict['result']
            except:
                _logger.error("Error in listing SKU %s to %s: Wrong python code for pricing formula." %(inventory_id, self.name))
                continue

            Quantity = 0
            if qty_and_price[0]['QtyOnHand'] > 3:
                Quantity = min(qty_and_price[0]['QtyOnHand'], store_id.ebay_max_quantity)

            store_id.ebay_execute('ReviseItem', {'Item': {
                'ItemID': item_id,
                'SKU': new_sku,
                'StartPrice': StartPrice,
                'Quantity': Quantity,
            }})
            _logger.info("Line %s, Revising ItemID: %s, Custom Label: %s, New SKU: %s, StartPrice: %s, Quantity: %s" 
                %(current_line_count, item_id, inventory_id, new_sku, StartPrice, Quantity))
            current_line_count += 1

    @api.model
    def cron_store_rhino_upload_fitments(self, line_start, line_to):
        store_id = self.search([('code', '=', 'rhino')])
        store_id.ensure_one()
        searchfile = "/var/tmp/NoFitment.csv"
        current_line_count = line_start
        while current_line_count <= line_to:
            line = linecache.getline(searchfile, current_line_count)
            current_line_count += 1
            list_line = line.split(';')
            item_id = list_line[0]
            part_number = list_line[2]

            inventory_id_res = self.env['sale.order'].autoplus_execute("""
                SELECT INV.InventoryID
                FROM Inventory INV
                WHERE INV.PartNo = '%s' AND MfgID = 1
            """ 
            % (part_number, ))

            if not inventory_id_res:
                _logger.error("No inventory found with Part No %ss" %(part_number))
                continue
            inventory_id =  inventory_id_res[0]['InventoryID']

            vehicles = self.get_vehicles(inventory_id)
            category_id = self.get_category_id(inventory_id)
            if not category_id:
                _logger.error("No category assigned to item id %s, Inventory ID %s" %(item_id, inventory_id))
                continue
            
            item_dict = {'ItemID': item_id, 'PrimaryCategory': {
                'CategoryID': category_id[0]['eBayCatID']
            }}

            ItemCompatibilityList = {'Compatibility': [], 'ReplaceAll': True}
            for c in vehicles:
                Note = ''
                row = {'CompatibilityNotes': Note,
                    'NameValueList': [
                        {'Name': 'Make', 'Value': c['MakeName'].replace("&", "&amp;") if c['MakeName'] else ''}, 
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
                        {'Name': 'Engine', 'Value': Engine.replace("&", "&amp;") }
                    )
                ItemCompatibilityList['Compatibility'].append(row)
            if vehicles:
                item_dict['ItemCompatibilityList'] = ItemCompatibilityList
                store_id.ebay_execute('ReviseItem', {'Item': item_dict})
                _logger.info("Done Line %s, Item ID %s" %(current_line_count, item_id))

    @api.multi
    def ebay_bulk_list_from_file(self, code, file_name, from_line, to_line):
        store_id = self.search([('code', '=', code)])
        store_id.ensure_one()
        now = datetime.now()
        current_line_count = from_line
        while current_line_count <= to_line:
            line = linecache.getline(file_name, current_line_count)
            part_number = line[:-1] #Remove the \n

            # get USAP Inventory ID

            inventory_id_res = self.env['sale.order'].autoplus_execute("""
                SELECT INV2.InventoryID
                FROM Inventory INV
                LEFT JOIN InventoryAlt ALT on ALT.InventoryID = INV.InventoryID
                LEFT JOIN Inventory INV2 on ALT.InventoryIDAlt = INV2.InventoryID
                WHERE INV.MfgID = 1 AND INV.PartNo = '%s' AND INV2.MfgID = 16
            """ %(part_number))

            inventory_id = inventory_id_res[0]['InventoryID']
            product_tmpl = self.env['product.template'].search([('inventory_id', '=', inventory_id)])
            if not product_tmpl:
                product_tmpl = self.env['product.template'].create({'name': 'New', 'inventory_id': inventory_id})
                product_tmpl.button_sync_with_autoplus()
            store_id.ebay_list_new_product(now, product_tmpl, raise_exception=False)
            _logger.info('Processed Inventory ID %s of line %s.' %(inventory_id, current_line_count))
            current_line_count += 1
        _logger.info('DONE PROCESSING BULK LISTING.')


    @api.model
    def ebay_create_inventory_status_from_file(self, code, filename, from_line, to_line):
        store_id = self.search([('code', '=', code), ('site', '=', 'ebay')])
        store_id.ensure_one()
        current_line_count = from_line

        output_file = open('/var/tmp/2016_12_19_Inventory_Update.xml', 'wb')
        output_file.write("<?xml version='1.0' encoding='UTF-8'?>\n")
        output_file.write("<BulkDataExchangeRequests>\n")
        output_file.write("<Header>\n")
        output_file.write("<Version>1</Version>\n")
        output_file.write("<SiteID>0</SiteID>\n")
        output_file.write("</Header>\n")
        output_file.write("<ReviseInventoryStatusRequest xmlns='urn:ebay:apis:eBLBaseComponents'>\n")

        while current_line_count <= to_line:
            line = linecache.getline(filename, current_line_count)
            current_line_count += 1
            list_line = line.split(',')

            item_id = list_line[0]
            sku = list_line[1]
            
            inv_result = self.env['sale.order'].autoplus_execute("""
                SELECT
                INV2.QtyOnHand, 
                PR.Cost
                FROM Inventory INV
                LEFT JOIN InventoryAlt ALT on ALT.InventoryID = INV.InventoryID
                LEFT JOIN Inventory INV2 on ALT.InventoryIDAlt = INV2.InventoryID
                LEFT JOIN InventoryMiscPrCur PR ON INV2.InventoryID = PR.InventoryID
                WHERE INV.PartNo = '%s' and INV.MfgID = 1 
                AND INV2.MfgID = 16
            """ %(sku,))
            
            if not inv_result:
                inv_result = self.env['sale.order'].autoplus_execute("""
                    SELECT
                    INV.QtyOnHand, 
                    PR.Cost
                    FROM Inventory INV
                    LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
                    WHERE INV.PartNo = '%s' and INV.MfgID = 16
                """ %(sku,))

            if not inv_result:
                _logger.error("No inventory found for line %s, SKU %s" %(current_line_count, sku))
                continue

            pricelocaldict = dict(
                COST=float(inv_result[0]['Cost'])
            )
            try:
                safe_eval(store_id.ebay_pricing_formula, pricelocaldict, mode='exec', nocopy=True)
                StartPrice = pricelocaldict['result']
            except:
                _logger.error("Error in listing SKU %s to %s: Wrong python code for pricing formula." %(inventory_id, self.name))
                continue

            Quantity = 0
            if inv_result[0]['QtyOnHand'] >= 3:
                Quantity = min(inv_result[0]['QtyOnHand'], store_id.ebay_max_quantity)
            xml = """
            <InventoryStatus>
            <ItemID>%s</ItemID>
            <Quantity>%s</Quantity>
            <SKU>%s</SKU>
            <StartPrice>%s</StartPrice>
            </InventoryStatus>
            """%(item_id, Quantity, sku, StartPrice)
            output_file.write(xml)
            _logger.info("Processed %s, ItemID: %s, SKU: %s, Quantity: %s, Price: %s" %(current_line_count, item_id, sku, Quantity, StartPrice))
        output_file.write("</ReviseInventoryStatusRequest>\n")
        output_file.write("</BulkDataExchangeRequests>")
        output_file.close()

    @api.model
    def ebay_download_active_inventory_report(self, code):
        store_id = self.search([('code', '=', code), ('site', '=', 'ebay')])
        store_id.ensure_one()
        download_uuid = uuid.uuid4()
        environment = 'sandbox' if store_id.ebay_domain == 'sand' else 'production'
        ebay_api = lmslib.StartDownloadJob(environment,
                       application_key=store_id.ebay_app_id,
                       developer_key=store_id.ebay_dev_id,
                       certificate_key=store_id.ebay_cert_id,
                       auth_token=store_id.ebay_token)
        ebay_api.buildRequest(jobType='ActiveInventoryReport', uuid=download_uuid)
        ebay_api.sendRequest()
        response, resp_struct = ebay_api.getResponse()
        if response == 'Success':
            _logger.info("Started Download Job on %s with uuid %s: %s" % (code, download_uuid, json.dumps(resp_struct)))

        # 2d92763d-4d67-4573-86cc-ea51d3a0e4dd: {"ack": "Success", "timestamp": "2016-12-19T18:08:04.700Z", "version": "1.5.0", "jobId": "6054399771"} fileref 6146774301

    @api.model
    def ebay_get_job_status(self, code, job_id):
        store_id = self.search([('code', '=', code), ('site', '=', 'ebay')])
        store_id.ensure_one()
        environment = 'sandbox' if store_id.ebay_domain == 'sand' else 'production'
        ebay_api = lmslib.GetJobStatus(environment,
                   application_key=store_id.ebay_app_id,
                   developer_key=store_id.ebay_dev_id,
                   certificate_key=store_id.ebay_cert_id,
                   auth_token=store_id.ebay_token)
        ebay_api.buildRequest(job_id)
        response = ebay_api.sendRequest()
        response, response_dict = ebay_api.getResponse()
        if response == 'Success':
            _logger.info("Job Status %s" %response_dict[0])
        else:
            _logger.error('ERROR getting job Status %s' %json.dumps(response_dict))

    @api.model
    def ebay_get_job_status(self, code, job_id):
        store_id = self.search([('code', '=', code), ('site', '=', 'ebay')])
        store_id.ensure_one()
        environment = 'sandbox' if store_id.ebay_domain == 'sand' else 'production'
        ebay_api = lmslib.GetJobStatus(environment,
                   application_key=store_id.ebay_app_id,
                   developer_key=store_id.ebay_dev_id,
                   certificate_key=store_id.ebay_cert_id,
                   auth_token=store_id.ebay_token)
        ebay_api.buildRequest(job_id)
        response = ebay_api.sendRequest()
        response, response_dict = ebay_api.getResponse()
        if response == 'Success':
            _logger.info("Job Status %s" %response_dict[0])
        else:
            _logger.error('ERROR getting job Status %s' %json.dumps(response_dict))

    @api.model
    def ebay_download_file(self, code, job_id, file_reference_id):
        store_id = self.search([('code', '=', code), ('site', '=', 'ebay')])
        store_id.ensure_one()
        environment = 'sandbox' if store_id.ebay_domain == 'sand' else 'production'
        ebay_api = lmslib.DownloadFile(environment,
                   application_key=store_id.ebay_app_id,
                   developer_key=store_id.ebay_dev_id,
                   certificate_key=store_id.ebay_cert_id,
                   auth_token=store_id.ebay_token)
        ebay_api.buildRequest(job_id, file_reference_id)
        response = ebay_api.sendRequest()
        response, response_dict = ebay_api.getResponse()
        if response == 'Success':
            _logger.info("File Downloaded %s" %response_dict[0])
        else:
            _logger.error('ERROR getting job Status %s' %json.dumps(response_dict))

    @api.model
    def ebay_generate_title_revision_file(self, code, filename, from_line, to_line):
        store_id = self.search([('code', '=', code), ('site', '=', 'ebay')])
        store_id.ensure_one()

        output_file = open('/var/tmp/title_updates/2016_12_20_Title_Revisions_%s_to_%s.xml' %(from_line, to_line), 'wb')
        output_file.write("<?xml version='1.0' encoding='UTF-8'?>\n")
        output_file.write("<BulkDataExchangeRequests>\n")
        output_file.write("<Header>\n")
        output_file.write("<Version>837</Version>\n")
        output_file.write("<SiteID>100</SiteID>\n")
        output_file.write("</Header>\n")

        current_line_count = from_line
        while current_line_count <= to_line:
            line = linecache.getline(filename, current_line_count)
            list_line = line.split(',')

            item_id = list_line[0]
            sku = list_line[1][:-1]

            inv_result = self.env['sale.order'].autoplus_execute("""
                SELECT
                INV2.InventoryID
                FROM Inventory INV
                LEFT JOIN InventoryAlt ALT on ALT.InventoryID = INV.InventoryID
                LEFT JOIN Inventory INV2 on ALT.InventoryIDAlt = INV2.InventoryID
                WHERE INV.PartNo = '%s' and INV.MfgID = 1 
                AND INV2.MfgID = 16
            """ %(sku,))
            
            if not inv_result:
                inv_result = self.env['sale.order'].autoplus_execute("""
                    SELECT
                    INV.InventoryID
                    FROM Inventory INV
                    WHERE INV.PartNo = '%s' and INV.MfgID = 16
                """ %(sku,))

            if not inv_result:
                current_line_count += 1
                _logger.error("No inventory found for line %s, SKU %s" %(current_line_count, sku))
                continue

            inventory_id =  inv_result[0]['InventoryID']

            main_product_details = self.get_main_product_details(inventory_id)

            interchange_values = self.env['sale.order'].autoplus_execute("""
            SELECT 
            INTE.PartNo,
            INTE.BrandID
            FROM Inventory INV
            LEFT JOIN InventoryPiesINTE INTE on INTE.InventoryID = INV.InventoryID
            WHERE INV.InventoryID = %s
            """ % (inventory_id, ))

            partslink = ''
            if interchange_values:
                oem_part_number = ''
                parsed_interchange_values = ''
                for i in interchange_values:
                    if i['BrandID'] == 'FLQV':
                        partslink = i['PartNo']

            vehicles = self.get_vehicles(inventory_id)
            if not (vehicles[0]['MakeName'] and vehicles[0]['ModelName'] and vehicles[0]['YearID']):
                for alt_id in alt_ids:
                    vehicles = self.get_vehicles(alt_id)
                    if vehicles[0]['MakeName'] and vehicles[0]['ModelName'] and vehicles[0]['YearID']:
                        break
                else:
                    if raise_exception:
                        raise UserError(_('No fitments found.'))
                    _logger.error("Error in listing SKU %s to %s: No fitments found." %(inventory_id, self.name))
                    return False

            titlelocaldict = dict(
                PRODUCTNAME=main_product_details[0]['ProdName'].replace("&", "&amp;"),
                PARTSLINK=partslink,
                MAKENAME=vehicles[0]['MakeName'].replace("&", "&amp;"),
                MODELNAME=vehicles[0]['ModelName'].replace("&", "&amp;"),
                MINYEAR=str(vehicles[0]['YearID']),
                MAXYEAR=str(vehicles[-1]['YearID'])
            )
            print titlelocaldict
            Title = ""
            try:
                safe_eval(store_id.ebay_title, titlelocaldict, mode='exec', nocopy=True)
                Title = titlelocaldict['result']
            except:
                _logger.error('Wrong python code defined for Title.')
                current_line_count += 1
                continue
            output_file.write("<ReviseFixedPriceItemRequest xmlns='urn:ebay:apis:eBLBaseComponents'>\n")
            output_file.write("<Version>837</Version>\n")
            xml = "<Item><ItemID>%s</ItemID><Title>%s</Title></Item>" %(item_id, Title)
            output_file.write(xml)
            output_file.write("</ReviseFixedPriceItemRequest>")

            _logger.info("Processed %s, ItemID: %s, SKU: %s" %(current_line_count, item_id, sku))
            current_line_count += 1
        output_file.write("</BulkDataExchangeRequests>")
        output_file.close()