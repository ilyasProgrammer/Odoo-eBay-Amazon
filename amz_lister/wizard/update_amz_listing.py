# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import xlsxwriter

from datetime import datetime

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class UpdateAmzListing(models.TransientModel):
    _name = 'product.update.amz.listing.wizard'

    listing_id = fields.Many2one('product.listing', 'Listing', required=True)
    store_id = fields.Many2one('sale.store', 'Store', related='listing_id.store_id')
    title = fields.Char('Title', required=True)
    upc = fields.Char('UPC', required=True)
    update_images = fields.Boolean('Update Images?', default=True)
    update_other_details = fields.Boolean('Update Other Details?', default=True)

    @api.model
    def default_get(self, fields):
        res = super(UpdateAmzListing, self).default_get(fields)
        if self.env.context.get('active_id') and self.env.context.get('active_model') == 'product.listing':
            listing_id = self.env['product.listing'].browse([self.env.context.get('active_id')])
            res['listing_id'] = listing_id.id
            res['title'] = listing_id.title
            res['upc'] = listing_id.upc
        return res

    @api.multi
    def button_update_listing(self):
        template_row_1 = [
            'Seller SKU', 'Product ID',	'Product ID Type', 'Product Name',
            'Manufacturer', 'Manufacturer Part Number', 'Product Type',
            'Item Type Keyword', 'Clothing Type', 'Product Description',
            'Brand Name', 'Update Delete', 'Package Quantity', 'Product Tax Code',
            'Launch Date', 'Release Date', 'Restock Date',
            'Minimum Advertised Price', "Manufacturer's Suggested Retail Price",
            'Standard Price', 'Sale Price', 'Sale Start Date', 'Sale End Date',
            'Item Condition', 'Offer Condition Note', 'Quantity',
            'Fulfillment Latency', 'Max Aggregate Ship Quantity',
            'Offering Can Be Gift Messaged', 'Is Gift Wrap Available',
            'Is Discontinued by Manufacturer', 'Registered Parameter',
            'Shipping-Template', 'Item Volume Unit Of Measure', 'Volume',
            'Item Weight Unit Of Measure', 'Item Weight',
            'Item Length Unit Of Measure', 'Item Length', 'Item Height',
            'Item Width', 'Website Shipping Weight Unit Of Measure',
            'Shipping Weight', 'Item Display Diameter Unit Of Measure', 'Diameter',
            'Style-specific Terms',	'Key Product Features1',
            'Key Product Features2', 'Key Product Features3',
            'Key Product Features4', 'Key Product Features5', 'Intended Use',
            'Target Audience', 'Search Terms', 'Catalog Number', 'Subject Matter',
            'Main Image URL', 'Other Image URL1', 'Other Image URL2',
            'Other Image URL3', 'Other Image URL4', 'Other Image URL5',
            'Other Image URL6', 'Other Image URL7', 'Swatch Image URL',
            'Fulfillment Center ID', 'Package Length', 'Package Width',
            'Package Height', 'Package Length Unit Of Measure', 'Package Weight',
            'Package Weight Unit Of Measure', 'Parentage', 'Parent SKU', 'Relationship Type',
            'Variation Theme', 'Legal Disclaimer', 'Consumer Notice', 'Cpsia Warning',
            'CPSIA Warning Description', 'Country of Publication', 'Fabric Type',
            'Please provide the Executive Number (EO) required for sale into California.',
            'Please provide the expiration date of the EO Number.',
            'Body Part Exterior Finish', 'Color', 'Color Map', 'OE Manufacturer',
            'Part Interchange Info', 'Department', 'Series', 'Other Attributes',
            'Part Type ID', 'Size', 'Size Map', 'Material', 'Viscosity',
            'Orientation', 'Mirror Adjustment', 'Mirror Turn Signal Indicator',
            'Additional Features', 'External Testing Certification',
            'Light Source Type', 'Window Regulator Lift Type',
            'Manufacturer Warranty Description', 'Occasion Lifestyle',
            'Inner Material', 'Outer Material', 'Sole Material',
            'Vehicle Type Compatibility', 'Voltage', 'Wattage',
            'Amperage Unit Of Measure',	'Amperage',
            'Manufacturer Warranty Type', 'Partslink Number1',
            'Partslink Number2', 'Partslink Number3', 'Partslink Number4'
        ]

        template_row_2 = [
            'item_sku', 'external_product_id', 'external_product_id_type',
            'item_name', 'manufacturer', 'part_number', 'feed_product_type',
            'item_type', 'product_subtype', 'product_description', 'brand_name',
            'update_delete', 'item_package_quantity', 'product_tax_code',
            'product_site_launch_date',	'merchant_release_date', 'restock_date',
            'map_price', 'list_price', 'standard_price', 'sale_price',
            'sale_from_date', 'sale_end_date', 'condition_type', 'condition_note',
            'quantity', 'fulfillment_latency', 'max_aggregate_ship_quantity',
            'offering_can_be_gift_messaged', 'offering_can_be_giftwrapped',
            'is_discontinued_by_manufacturer', 'missing_keyset_reason',
            'merchant_shipping_group_name', 'item_volume_unit_of_measure',
            'item_volume', 'item_weight_unit_of_measure', 'item_weight',
            'item_length_unit_of_measure', 'item_length', 'item_height',
            'item_width', 'website_shipping_weight_unit_of_measure',
            'website_shipping_weight', 'item_display_diameter_unit_of_measure',
            'item_display_diameter', 'style_keywords', 'bullet_point1',
            'bullet_point2', 'bullet_point3', 'bullet_point4', 'bullet_point5',
            'specific_uses_keywords', 'target_audience_keywords', 'generic_keywords',
            'catalog_number', 'thesaurus_subject_keywords',	'main_image_url',
            'other_image_url1', 'other_image_url2', 'other_image_url3', 'other_image_url4',
            'other_image_url5', 'other_image_url6', 'other_image_url7',
            'swatch_image_url', 'fulfillment_center_id', 'package_length',
            'package_width', 'package_height', 'package_length_unit_of_measure',
            'package_weight', 'package_weight_unit_of_measure', 'parent_child',
            'parent_sku', 'relationship_type', 'variation_theme',
            'legal_disclaimer_description', 'prop_65', 'cpsia_cautionary_statement',
            'cpsia_cautionary_description',	'country_of_origin', 'fabric_type',
            'legal_compliance_certification_metadata',
            'legal_compliance_certification_expiration_date', 'exterior_finish',
            'color_name', 'color_map', 'oe_manufacturer', 'part_interchange_info',
            'department_name', 'model_name', 'thesaurus_attribute_keywords',
            'part_type_id', 'size_name', 'size_map', 'material_type', 'viscosity',
            'orientation', 'control_type', 'light_type', 'special_features',
            'external_testing_certification', 'light_source_type', 'operation_mode',
            'warranty_description', 'lifestyle', 'inner_material_type',
            'outer_material_type', 'sole_material', 'compatible_with_vehicle_type',
            'voltage', 'wattage', 'amperage_unit_of_measure', 'amperage',
            'mfg_warranty_description_type', 'abpa_partslink_number1',
            'abpa_partslink_number2', 'abpa_partslink_number3',
            'abpa_partslink_number4'
        ]

        if not (self.update_images or self.update_other_details):
            return {'type': 'ir.actions.act_window_close'}

        feed_file_path = '/Users/ajporlante/auto/amazon/lister.xlsx'
        workbook = xlsxwriter.Workbook(feed_file_path)
        worksheet = workbook.add_worksheet()

        worksheet.write(0, 0, 'TemplateType=autoaccessory')
        worksheet.write(0, 1, 'Version=2016.0909')

        col = 0
        for r in template_row_1:
            worksheet.write(1, col, r)
            col += 1
        col = 0
        for r in template_row_2:
            worksheet.write(2, col, r)
            col += 1

        data_row = [''] * 118
        data_row[0] = self.listing_id.name
        data_row[3] = self.title
        data_row[5] = self.upc
        data_row[10] = 'Make Auto Parts Manufacturing'
        data_row[11] = 'PartialUpdate'

        if self.update_images:
            images = self.listing_id.product_tmpl_id.get_image_urls()
            col = 56
            for i in images:
                data_row[col] = i
                col += 1

        print self.update_other_details
        if self.update_other_details:
            attr_line_ids = self.listing_id.product_tmpl_id.auto_attribute_line_ids
            print attr_line_ids
            attr_dict = {}
            for l in attr_line_ids:
                if l.value_ids:
                    attr_dict[l.auto_attribute_id.name] = l.value_ids[0].name

            if 'Finish' in attr_dict:
                data_row[84] = attr_dict['Finish']
            elif 'Color finish' in attr_dict:
                data_row[84] = attr_dict['Color finish']

            interchange = ''
            partslink_list = []
            if 'Partslink' in attr_dict:
                interchange += attr_dict['Partslink']
                partslink_list = attr_dict['Partslink'].strip().split(',')
            elif 'Replaces partslink number' in attr_dict:
                interchange += attr_dict['Replaces partslink number']
                partslink_list = attr_dict['Replaces partslink number'].strip().split(',')

            if partslink_list:
                col = 115
                for p in partslink_list:
                    if col < 188:
                        data_row[col] = p
                        col += 1

            if 'Replaces OEM number' in attr_dict:
                if interchange:
                    interchange += ', '
                interchange += attr_dict['Replaces OEM number']

            if interchange:
                data_row[88] = interchange
        print data_row
        col = 0
        for r in data_row:
            worksheet.write(3, col, r)
            col += 1

        workbook.close()

        feed_file = open(feed_file_path , 'r')
        feed_content = feed_file.read()
        md5value = self.listing_id.store_id.get_md5(feed_content)

        params = {
            'ContentMD5Value': md5value,
            'Action': 'SubmitFeed',
            'FeedType': '_POST_FLAT_FILE_LISTINGS_DATA_',
            'PurgeAndReplace': 'false'
        }
        _logger.info('Updating listing: %s' %self.listing_id.name)
        now = datetime.now()
        response = self.listing_id.store_id.process_amz_request('POST', '/Feeds/2009-01-01', now, params, feed_content)

        return {'type': 'ir.actions.act_window_close'}
