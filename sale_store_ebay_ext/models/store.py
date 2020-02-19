# -*- coding: utf-8 -*-

import logging
import random
import string
from datetime import datetime
from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
import math
from pytz import timezone

_logger = logging.getLogger(__name__)


class StoreAddListing(models.TransientModel):
    _inherit = 'sale.store.add.listing'

    template_id = fields.Many2one('listing.template', required=True)
    store_id = fields.Many2one('sale.store', 'Store to Publish the Product', required=False, domain=[('enabled', '=', True)])

    @api.multi
    def button_add_listing(self):
        # overriding method
        self.ensure_one()
        now = datetime.now()
        self.store_id = self.template_id.store_id
        params = {
            'product_name': self.product_name,
            'price': self.price,
            'quantity': self.quantity,
            'ebay_category_id': self.ebay_category_id,
            'template_id': self.template_id,
            'product_tmpl_id': self.product_tmpl_id,
        }
        if self.image:
            attachment = self.env['ir.attachment'].create({
                'name': 'ebay_listing_image_' + self.product_tmpl_id.name,
                'datas': self.image,
                'datas_fname': self.product_tmpl_id.name + '.png',
                'public': True,
                'res_model': 'sale.store.add.listing',
            })
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            params['image_url'] = base_url + '/web/content/' + str(attachment.id)
        if hasattr(self.store_id, '%s_list_new_product' % self.store_id.site):
            getattr(self.store_id, '%s_list_new_product' % self.store_id.site)(now, self.product_tmpl_id, params)
        return {'type': 'ir.actions.act_window_close'}


class OnlineStore(models.Model):
    _inherit = 'sale.store'

    @api.model
    def ebay_saveorder(self, order):
        PartnerObj = self.env['res.partner']
        ProductTemplateObj = self.env['product.template']
        ProductProductObj = self.env['product.product']
        SaleOrderObj = self.env['sale.order']
        SaleOrderLineObj = self.env['sale.order.line']
        ProductListingObj = self.env['product.listing']

        address_id = order['ShippingAddress']['AddressID']
        if order['IsMultiLegShipping'] == 'true':
            ShipToAddress = order['MultiLegShippingDetails']['SellerShipmentToLogisticsProvider']['ShipToAddress']
            partner_values = {
                'name': ShipToAddress['Name'],
                'phone': order['ShippingAddress']['Phone'],
                'street': 'Reference #' + ShipToAddress['ReferenceID'],
                'street2': ShipToAddress['Street1'],
                'city': ShipToAddress['CityName'],
                'zip': ShipToAddress['PostalCode'].strip(' '),
                'country_id': self.env['res.country'].search([('code', '=', ShipToAddress['Country'])], limit=1).id,
                'state_id': self.env['res.country.state'].search([('code', '=', ShipToAddress['StateOrProvince']), ('country_id.code', '=', ShipToAddress['Country'])], limit=1).id,
                'customer': True,
                'web_partner_id': address_id,
                'store_id': self.id
            }
            partner_id = PartnerObj.create(partner_values)
        else:
            partner_id = PartnerObj.search([('web_partner_id', '=', address_id)], limit=1)
            if not partner_id:
                partner_values = {
                    'name': order['ShippingAddress']['Name'],
                    'phone': order['ShippingAddress']['Phone'],
                    'street': order['ShippingAddress']['Street1'],
                    'street2': order['ShippingAddress']['Street2'],
                    'city': order['ShippingAddress']['CityName'],
                    'zip': order['ShippingAddress']['PostalCode'].strip(' '),
                    'country_id': self.env['res.country'].search([('code', '=', order['ShippingAddress']['Country'])], limit=1).id,
                    'state_id': self.env['res.country.state'].search([('code', '=', order['ShippingAddress']['StateOrProvince']), ('country_id.code', '=', order['ShippingAddress']['Country'])], limit=1).id,
                    'customer': True,
                    'web_partner_id': address_id,
                    'store_id': self.id
                }
                partner_id = PartnerObj.create(partner_values)
        paypal_fee = 0
        paypal_transaction = ''
        try:
            transaction_data = self.ebay_execute('GetOrderTransactions', {'OrderIDArray': [{'OrderID': order['OrderID']}],
                                                                          'DetailLevel': 'ReturnAll'}).dict()
            paypal_fee = dv(transaction_data, ('OrderArray', 'Order', 'MonetaryDetails', 'Payments', 'Payment', 'FeeOrCreditAmount', 'value'), 0.0)
            paypal_transaction = dv(transaction_data, ('OrderArray', 'Order', 'ExternalTransaction', 'ExternalTransactionID'), '')
            _logger.info('PayPal fee: %s', paypal_fee)
            _logger.info('PayPal paypal_transaction: %s', paypal_transaction)
        except Exception as e:
            _logger.warning(e)
        sale_order_id = SaleOrderObj.create({
            'partner_id': partner_id.id,
            'web_order_id': order['OrderID'],
            'store_id': self.id,
            'payment_term_id': self.env.ref('account.account_payment_term_immediate').id,
            'ebay_sales_record_number': order['ShippingDetails']['SellingManagerSalesRecordNumber'],
            # 'date_order': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date_order': convert_ebay_date(order.get('CreatedTime')),
            'paypal_fee': paypal_fee,
            'paypal_transaction': paypal_transaction,
            'ebay_created_time': convert_ebay_date(order.get('CreatedTime')),
            'ebay_paid_time': convert_ebay_date(order.get('PaidTime')),
            'ebay_shipped_time': convert_ebay_date(order.get('ShippedTime')),
        })

        for trans in order['TransactionArray']['Transaction']:
            sku = ''
            product_tmpl_id = ProductTemplateObj
            if 'SKU' in trans['Item'] and trans['Item']['SKU']:
                sku = trans['Item']['SKU']
                print sku
                if sku.startswith('NORDYS-'):
                    sku = sku.strip('NORDYS-')
                elif sku.startswith('X-'):
                    sku = sku.strip('X-')
                elif sku.startswith('V2F-'):
                    sku = sku.replace('V2F-', '')
                elif sku.startswith('MG-'):
                    sku_row = SaleOrderObj.autoplus_execute("""
                        SELECT INV.PartNo FROM Inventory INV
                        LEFT JOIN InventoryAlt ALT on ALT.InventoryIdAlt = INV.InventoryId
                        LEFT JOIN Inventory INV2 on ALT.InventoryId = INV2.InventoryId
                        WHERE INV2.PartNo = '%s' AND INV2.MfgID = 40 and INV.MfgID = 1
                    """ % sku)
                    if sku_row:
                        sku = sku_row[0]['PartNo']
                elif sku.startswith('APC-'):
                    sku_row = SaleOrderObj.autoplus_execute("""
                        SELECT INV.PartNo FROM Inventory INV
                        LEFT JOIN InventoryAlt ALT on ALT.InventoryIdAlt = INV.InventoryId
                        LEFT JOIN Inventory INV2 on ALT.InventoryId = INV2.InventoryId
                        WHERE INV2.PartNo = '%s' AND INV2.MfgID = 42 and INV.MfgID = 1
                    """ % sku)
                    if sku_row:
                        sku = sku_row[0]['PartNo']
                product_id = ProductProductObj.search([('part_number', '=', sku), ('mfg_code', '=', 'ASE')], limit=1)
                if not product_id:
                    product_id = ProductProductObj.search([('part_number', '=', sku)], limit=1)
                    ase_alt = product_id.alternate_ids.filtered(lambda p: p.mfg_code == 'ASE')
                    if ase_alt:
                        product_id = ase_alt
                product_tmpl_id = product_id.product_tmpl_id

            # If product is not found in odoo, look for it in autoplus and save it to odoo
            if not product_tmpl_id and sku:
                product_row = ProductTemplateObj.get_product_from_autoplus_by_part_number(sku)
                if product_row:
                    product_values = ProductTemplateObj.prepare_product_row_from_autoplus(product_row)
                    product_tmpl_id = ProductTemplateObj.create(product_values)

            # If product is not found in odoo and autoplus, create the product
            if not product_tmpl_id:
                product_values = {
                    'name': '[NOT FOUND] ' + trans['Item']['Title'],
                    'part_number': sku,
                    'type': 'product',
                    'list_price': trans['TransactionPrice']['value'],
                }
                product_tmpl_id = ProductTemplateObj.create(product_values)

            tax = self.env['account.tax']
            try:
                if trans.get('Taxes'):
                    if trans['Taxes'].get('TaxDetails'):
                        if type(trans['Taxes']['TaxDetails']) != list:
                            trans['Taxes']['TaxDetails'] = [trans['Taxes']['TaxDetails']]
                        for t in trans['Taxes']['TaxDetails']:
                            if t['Imposition'] == 'SalesTax':
                                tax_val = float(t['TaxAmount']['value'])
                                tax_percent = 100 * tax_val / float(trans['TransactionPrice']['value'])
                                tax_percent = truncate(tax_percent, 2)  # Because rounding might cause inaccuracy
                                tax = self.env['account.tax'].search([('state_id', '=', partner_id.state_id.id)])  # One state one tax
                                if len(tax) == 1:
                                    if abs(tax.amount - tax_percent) > 0.04:  # Difference to high. Skip tax.
                                        if tax_percent > 0:
                                            _logger.warning('Tax difference to high %s %s %s %s', sale_order_id.id, tax.name, tax.amount, tax_percent)
                                        tax = False
            except Exception as e:
                _logger.error(e)
                _logger.error(trans)

            SaleOrderLineObj.create({
                'product_id': product_tmpl_id.product_variant_id.id,
                'order_id': sale_order_id.id,
                'product_uom_qty': int(trans['QuantityPurchased']),
                'price_unit': trans['TransactionPrice']['value'],
                'web_orderline_id': trans['OrderLineItemID'],
                'item_id': trans['Item']['ItemID'],
                'tax_id': [(6, 0, [tax.id])] if tax else False
            })

            listing = ProductListingObj.search([('name', '=', trans['Item']['ItemID']), ('product_tmpl_id.id', '=', product_tmpl_id.id), ('store_id.id', '=', self.id)])
            if not listing:
                ProductListingObj.create({
                        'name': trans['Item']['ItemID'],
                        'product_tmpl_id': product_tmpl_id.id,
                        'store_id': self.id,
                    })

            if self.enabled:
                listing.update_availability()

        if len(sale_order_id.order_line) == 1:
            product_id = sale_order_id.order_line.product_id
            sale_order_id.write({
                'length': product_id.length,
                'width': product_id.width,
                'height': product_id.height,
                'weight': product_id.weight
            })
        self.env.cr.commit()
        return sale_order_id

    @api.multi  # TODO Check inheritance order
    def ebay_prepare_item_dict(self, inventory_id, params=None, raise_exception=False):
        # overriding method
        self.ensure_one()
        attrs = self.env['product.auto.attribute.line'].search([('product_tmpl_id', '=', params['product_tmpl_id'].id)])
        if raise_exception and len(attrs) < 1:
            raise UserError('There is no features (attributes) for this item.')
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
                    _logger.error("Error in listing SKU %s to %s: Product Name is not specified." % (inventory_id, self.name))
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
                    raise UserError('Category ID is not specified.')
                else:
                    _logger.error("Error in listing SKU %s to %s: Category ID is not specified." % (inventory_id, self.name))
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
                raise UserError("Pricing Error. No price found. And price is not set.")
            else:
                _logger.error("Error in listing SKU %s to %s: Pricing error." % (inventory_id, self.name))
                return False

        interchange_values = self.env['sale.order'].autoplus_execute("""
               SELECT
               INTE.PartNo,
               INTE.BrandID
               FROM Inventory INV
               LEFT JOIN InventoryPiesINTE INTE on INTE.InventoryID = INV.InventoryID
               WHERE INV.InventoryID = %s
               """ % (inventory_id,))

        ItemSpecifics = {'NameValueList': []}
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
                    _logger.error("Error in listing SKU %s to %s: No images found." % (inventory_id, self.name))
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
            safe_eval(params['template_id'].title, titlelocaldict, mode='exec', nocopy=True)
            Title = titlelocaldict['result']
        except Exception as e:
            if raise_exception:
                raise UserError('Wrong python code defined for Title: %s' % e)
            _logger.error("Error in listing SKU %s to %s: Wrong python code for Title." % (inventory_id, self.name))
            return False

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')

        logo = ''
        if self.image:
            # logo = base_url + '/web/image?model=sale.store&id=%s&field=image' % self.id
            logo = params['template_id'].brand_id.image

        PictureURL = []
        picture_counter = 1
        for p in picture_urls:
            if picture_counter > 12:
                break
            if p['URI'] != None:
                PictureURL.append(p['URI'])
            picture_counter += 1
        if PictureURL:
            PictureDetails = {'PictureURL': PictureURL}

        desclocaldict = dict(
            MFGLABEL=main_product_details[0]['MfgLabel'].replace("&", "&amp;"),
            PRODUCTNAME=main_product_details[0]['ProdName'].replace("&", "&amp;"),
            STORENAME=self.name,
            BRAND=self.ebay_brand,
            TITLE=Title,
            INTERCHANGE=parsed_interchange_values[:-2],
            LOGO=logo,
            MAINIMAGE=PictureURL[0] if PictureURL else '',
            OTHERIMAGES=PictureURL[1:] if len(PictureURL) > 1 else [],
            ATTRS=attrs
        )

        for i in self.image_ids:
            desclocaldict[i.code] = base_url + '/web/image?model=sale.store.image&id=%s&field=image' % i.id

        Description = ""
        try:
            safe_eval(params['template_id'].template, desclocaldict, mode='exec', nocopy=True)
            Description = desclocaldict['result']
        except Exception as e:
            if raise_exception:
                raise UserError('Wrong python code defined for Description: %s' % e)
            _logger.error("Error in listing SKU %s to %s: Wrong python code for description." % (inventory_id, self.name))
            return False

        if not manual_pricing:
            pricelocaldict = dict(
                COST=float(qty_and_price[0]['Cost'])
            )
            try:
                safe_eval(self.ebay_pricing_formula, pricelocaldict, mode='exec', nocopy=True)
                StartPrice = pricelocaldict['result']
            except Exception as e:
                if raise_exception:
                    raise UserError('Wrong python code defined for Pricing Formula: %s' % e)
                _logger.error("Error in listing SKU %s to %s: Wrong python code for pricing formula." % (inventory_id, self.name))
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
                'Description': self.ebay_return_description,
                'ShippingCostPaidByOption': self.ebay_shipping_cost_paid_by
            }
        }

        item_dict['ItemSpecifics'] = ItemSpecifics

        ItemCompatibilityList = {'Compatibility': []}
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
                    {'Name': 'Trim', 'Value': c['Trim'].replace("&", "&amp;")}
                )
            if c['EngineID']:
                Engine = self.compute_engine(c)
                row['NameValueList'].append(
                    {'Name': 'Engine', 'Value': Engine}
                )
            ItemCompatibilityList['Compatibility'].append(row)
        if vehicles:
            item_dict['ItemCompatibilityList'] = ItemCompatibilityList
        return item_dict


def truncate(f, n):
    return math.floor(f * 10 ** n) / 10 ** n


def dv(data, path, ret_type=None):
    # Deep value of nested dict. Return ret_type if cant find it
    for ind, el in enumerate(path):
        if data.get(el):
            return dv(data[el], path[ind+1:])
        else:
            return ret_type
    return data


def dt_to_utc(sdt):
    try:
        res = timezone('US/Eastern').localize(datetime.strptime(sdt, '%Y-%m-%d %H:%M:%S.%f')).astimezone(timezone('utc')).strftime('%Y-%m-%d %H:%M:%S')
        return res
    except:
        return False


def convert_ebay_date(raw_amz_time_str):
    # eBay has UTC time. Odoo will convert it to Michigan time EST or EDT  which is UTC-4
    try:
        t = raw_amz_time_str.replace('T', ' ').replace('Z', '')
        # return dt_to_utc(t)
        return t
    except:
        return False
