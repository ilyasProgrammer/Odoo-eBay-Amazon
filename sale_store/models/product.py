# -*- coding: utf-8 -*-

import urllib2
import base64
import logging
from datetime import datetime
from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ProductListing(models.Model):
    _name = 'product.listing'

    name = fields.Char('eBay Item ID/Amazon SKU', required=True, help="ID of the item as provided by the store", track_visibility='onchange')
    store_id = fields.Many2one('sale.store', 'Store', required=True)
    site = fields.Selection([], 'Site', related='store_id.site')
    product_id = fields.Many2one('product.product', 'Product', related='product_tmpl_id.product_variant_id')
    product_tmpl_id = fields.Many2one('product.template', 'Product Template')
    state = fields.Selection([('active', 'Active'), ('ended', 'Ended')], 'Status', default='active', track_visibility='onchange')

    @api.multi
    def button_end_item(self):
        self.ensure_one()
        now = datetime.now()
        if hasattr(self.store_id, '%s_end_item' % self.store_id.site):
            getattr(self.store_id, '%s_end_item' % self.store_id.site)(now, self)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    _sql_constraints = [
        ('barcode_uniq', '', _('')),
    ]

    inventory_id = fields.Integer('Inventory ID', help="Inventory ID from AutoPlus")
    listing_ids = fields.One2many('product.listing', 'product_id', 'Listings')
    alternate_ids = fields.Many2many('product.product', 'product_product_alt_rel', 'alt_product_id', 'product_id', 'Alternate Parts')
    inv_alternate_ids = fields.Many2many('product.product', 'product_product_alt_rel', 'product_id', 'alt_product_id', 'Alternate Parts (Inv)')
    length = fields.Float("Length", digits=dp.get_precision('Product Dimension'), help="Length in inches", track_visibility='onchange')
    width = fields.Float("Width", digits=dp.get_precision('Product Dimension'), help="Width in inches", track_visibility='onchange')
    height = fields.Float("Height", digits=dp.get_precision('Product Dimension'), help="Height in inches", track_visibility='onchange')
    weight = fields.Float(
        'Weight', digits=dp.get_precision('Stock Weight'),
        help="The weight of the contents in lbs", track_visibility='onchange')
    part_number = fields.Char("Part Number")
    barcode_case = fields.Char('Case Barcode')
    barcode_inner_case = fields.Char('Inner Case Barcode')
    qty_case = fields.Integer('Case Quantity')
    qty_inner_case = fields.Integer('Inner Case Quantity')
    cost_core = fields.Float('Core Cost', digits=dp.get_precision('Product Price'))
    list_price_core = fields.Float('Core Sell Price', digits=dp.get_precision('Product Price'))
    mfg_code = fields.Char("Mfr Line Code")
    mfg_name = fields.Char("Manufacturer")
    mfg_pop_code = fields.Char("Manufacturer's Pop Code")
    ave_landed_cost = fields.Float('Average Landed Cost', digits=dp.get_precision('Product Price'))
    ave_lead_time = fields.Float('Average Lead Time')

    @api.multi
    def button_sync_with_autoplus(self, raise_exception=True):
        for product in self:
            product.product_tmpl_id.button_sync_with_autoplus(raise_exception=raise_exception)

    @api.multi
    def update_autoplus(self):
        SaleOrder = self.env['sale.order']
        select_query = """SELECT InventoryID FROM Inventory WHERE PartNo = '%s'"""
        update_query = """UPDATE InventoryPIESPack SET Length=%s, Width=%s, Height=%s, Weight=%s WHERE InventoryID = %s"""
        for product in self:
            result = SaleOrder.autoplus_execute(select_query % product.part_number)
            if result:
                SaleOrder.with_context(update=True).autoplus_execute(update_query % (product.length, product.width, product.height, product.weight, result[0]['InventoryID']))
        return True


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # TEMPLATE ONLY FIELDS
    product_variant_id = fields.Many2one('product.product', 'Product', compute='_compute_product_variant_id', store=True)
    part_type = fields.Char("Part Type")
    ccc_part_type = fields.Selection([('aftermarket', 'Aftermarket'),
        ('oem_disc', 'OEM Discounted'),
        ('blemished', 'Optional OEM - Blemished'),
        ('overrun', 'Optional OEM - Overrun'),
        ('remanufactured', 'Re-manufactured'),
        ('reconditioned', 'Reconditioned'),
        ('recycled', 'Recycled')], 'CCC Part Type')
    grade = fields.Selection([('low', 'Low'), ('normal', 'Normal'), ('high', 'High')])
    country_origin_id = fields.Many2one('res.country', 'Country of Origin')
    date_created = fields.Date('Date Created')
    flat_rate_hours = fields.Float('Flat Rate Hours', digits=dp.get_precision('Product Price'))
    inspection = fields.Char('Inspection')
    tariff_code = fields.Char('Tariff Code')
    voc = fields.Char('VOC')
    short_description = fields.Char('Short Description')
    long_description = fields.Text('Long Description')
    mfg_label = fields.Char('Mfg Label')
    partslink = fields.Char("Partslink No.")

    # fields stored in product.product
    inventory_id = fields.Integer('Inventory ID', related='product_variant_id.inventory_id', help="Inventory ID from AutoPlus", store=True)
    listing_ids = fields.One2many('product.listing', 'product_tmpl_id', 'Listings')
    alternate_ids = fields.Many2many('product.template', 'product_template_alt_rel', 'alt_product_tmpl_id', 'product_tmpl_id', 'Alternate Parts')
    length = fields.Float("Length", compute='_compute_length', inverse='_set_length', digits=dp.get_precision('Product Dimension'), help="Length in inches", store=True, track_visibility='onchange')
    width = fields.Float("Width", compute='_compute_width', inverse='_set_width', digits=dp.get_precision('Product Dimension'), help="Width in inches", store=True, track_visibility='onchange')
    height = fields.Float("Height", compute='_compute_height', inverse='_set_height', digits=dp.get_precision('Product Dimension'), help="Height in inches", store=True, track_visibility='onchange')
    weight = fields.Float('Weight', compute='_compute_weight', inverse='_set_weight', digits=dp.get_precision('Stock Weight'), help="The weight of the contents in lbs", store=True, track_visibility='onchange')

    part_number = fields.Char("Part Number", related='product_variant_id.part_number', store=True)
    barcode_case = fields.Char('Case Barcode', related='product_variant_id.barcode_case')
    barcode_inner_case = fields.Char('Inner Case Barcode', related='product_variant_id.barcode_inner_case')
    qty_case = fields.Integer('Case Quantity', related='product_variant_id.qty_case')
    qty_inner_case = fields.Integer('Inner Case Quantity', related='product_variant_id.qty_inner_case')
    cost_core = fields.Float('Core Cost', digits=dp.get_precision('Product Price'), related='product_variant_id.cost_core')
    list_price_core = fields.Float('Core Sell Price', digits=dp.get_precision('Product Price'), related='product_variant_id.list_price_core')
    mfg_name = fields.Char("Manufacturer", related='product_variant_id.mfg_name')
    mfg_code = fields.Char("Mfr Line Code", related='product_variant_id.mfg_code', store=True)
    mfg_pop_code = fields.Char("Manufacturer's Pop Code", related='product_variant_id.mfg_pop_code')
    qty_onhand = fields.Float('Quantity OnHand', compute='_compute_qty_autoplus', digits=dp.get_precision('Product Unit of Measure'))

    @api.multi
    def update_autoplus(self):
        SaleOrder = self.env['sale.order']
        select_query = """SELECT InventoryID FROM Inventory WHERE PartNo = '%s'"""
        update_query = """UPDATE InventoryPIESPack SET Length=%s, Width=%s, Height=%s, Weight=%s WHERE InventoryID = %s"""
        for product in self:
            result = SaleOrder.autoplus_execute(select_query % product.part_number)
            if result:
                SaleOrder.with_context(update=True).autoplus_execute(update_query % (product.length, product.width, product.height, product.weight, result[0]['InventoryID']))
        return True

    @api.multi
    def write(self, vals):
        length = float(vals['length']) if vals.get('length') else self.length
        width = float(vals['width']) if vals.get('width') else self.width
        height = float(vals['height']) if vals.get('height') else self.height
        if length < width:
            length, width = width, length
        if length < height:
            length, height = height, length
            # raise ValidationError("Length must be longest dimension! Product: %s" % self.name)
        vals['length'] = length
        vals['width'] = width
        vals['height'] = height
        if vals.get('alternate_ids'):
            alt_ids = self.search([('id', 'in', vals.get('alternate_ids')[0][2])])
            variant_alt_ids = []
            for alt_id in alt_ids:
                variant_alt_ids.append(alt_id.product_variant_id.id)
            self.product_variant_id.write({'alternate_ids': [(6, 0, variant_alt_ids)]})
        res = super(ProductTemplate, self).write(vals)
        return res

    @api.model
    def create(self, vals):
        template = super(ProductTemplate, self).create(vals)
        related_vals = {}
        if vals.get('inventory_id'):
            related_vals['inventory_id'] = vals['inventory_id']
        if vals.get('part_number'):
            related_vals['part_number'] = vals['part_number']
        if vals.get('barcode_case'):
            related_vals['barcode_case'] = vals['barcode_case']
        if vals.get('barcode_inner_case'):
            related_vals['barcode_inner_case'] = vals['barcode_inner_case']
        if vals.get('qty_case'):
            related_vals['qty_case'] = vals['qty_case']
        if vals.get('qty_inner_case'):
            related_vals['qty_inner_case'] = vals['qty_inner_case']
        if vals.get('cost_core'):
            related_vals['cost_core'] = vals['cost_core']
        if vals.get('list_price_core'):
            related_vals['list_price_core'] = vals['list_price_core']
        if vals.get('mfg_code'):
            related_vals['mfg_code'] = vals['mfg_code']
        if vals.get('mfg_name'):
            related_vals['mfg_name'] = vals['mfg_name']
        if vals.get('mfg_pop_code'):
            related_vals['mfg_pop_code'] = vals['mfg_pop_code']
        if related_vals:
            template.write(related_vals)
        if vals.get('alternate_ids'):
            alt_ids = self.search([('id', 'in', vals.get('alternate_ids')[0][2])])
            variant_alt_ids = []
            for alt_id in alt_ids:
                variant_alt_ids.append(alt_id.product_variant_id.id)
            template.product_variant_id.write({'alternate_ids': [(6, 0, variant_alt_ids)]})
        return template

    @api.depends('product_variant_ids', 'product_variant_ids.length')
    def _compute_length(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.length = template.product_variant_ids.length
        for template in (self - unique_variants):
            template.length = 0.0

    @api.depends('product_variant_ids', 'product_variant_ids.width')
    def _compute_width(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.width = template.product_variant_ids.width
        for template in (self - unique_variants):
            template.width = 0.0

    @api.depends('product_variant_ids', 'product_variant_ids.height')
    def _compute_height(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.height = template.product_variant_ids.height
        for template in (self - unique_variants):
            template.height = 0.0

    @api.depends('product_variant_ids', 'product_variant_ids.weight')
    def _compute_weight(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.weight = template.product_variant_ids.weight
        for template in (self - unique_variants):
            template.weight = 0.0

    @api.one
    def _set_length(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.length = self.length

    @api.one
    def _set_width(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.width = self.width

    @api.one
    def _set_height(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.height = self.height

    @api.one
    def _set_weight(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.weight = self.weight

    @api.multi
    def _compute_qty_autoplus(self):
        query = """SELECT QtyOnHand FROM Inventory WHERE PartNo = '%s' AND MfgId IN (16, 17, 21, 30, 35, 36, 37, 38, 39)"""
        for product in self:
            qty_onhand = 0.0
            if product.mfg_code != 'ASE':
                result = self.env['sale.order'].autoplus_execute(query % product.part_number)
                if result:
                    qty_onhand = result[0]['QtyOnHand']
            product.qty_onhand = qty_onhand

    @api.multi
    def get_alt_product_tmpl_ids(self):
        self.ensure_one()
        self.env.cr.execute("""
            SELECT alt_product_tmpl_id FROM product_template_alt_rel WHERE product_tmpl_id = %s
            """ %self.id)
        alt_id_rows = self.env.cr.dictfetchall()
        alt_ids = []
        for row in alt_id_rows:
            alt_ids.append(row['alt_product_tmpl_id'])
        return self.env['product.template'].search([('id', 'in', alt_ids)])

    @api.model
    def get_kit_config_from_autoplus_by_inventory_id(self, inventory_id):
        query = """
            SELECT
            InventoryID
            FROM InventoryPiesKit
            WHERE InventoryID = %s
            """ %inventory_id
        result = self.env['sale.order'].autoplus_execute(query)
        if result:
            return result[0]
        return result

    @api.model
    def get_product_from_autoplus_by_inventory_id(self, inventory_id):
        query = """
            SELECT TOP 1
            INV.MfgLabel,
            INV.InventoryID,
            INV.PartNo,
            INV.ProdName,
            INV.ShortDesc,
            INV.LongDesc,
            MFG.MfgCode,
            MFG.MfgName,
            PACK.Barcode,
            PACK.Length,
            PACK.Width,
            PACK.Height,
            PACK.Weight,
            PR.Cost,
            PR.ListPrice,
            ASST.URI
            FROM Inventory INV
            LEFT JOIN InventoryPIESPack PACK ON INV.InventoryID = PACK.InventoryID
            LEFT JOIN InventoryMiscPrCur PR on INV.InventoryID = PR.InventoryID
            LEFT JOIN Mfg MFG on INV.MfgId = MFG.MfgID
            LEFT JOIN InventoryPiesASST ASST on INV.InventoryID = ASST.InventoryID
            WHERE NOT (INV.MfgID IN (3,6,18)) AND INV.InventoryID = %s
            AND (PACK.PackUOM != 'CA' or PACK.PackUOM IS NULL)
            """ %inventory_id
        result = self.env['sale.order'].autoplus_execute(query)
        if result:
            query = """
                SELECT PartNo as Partslink
                FROM InventoryPiesINTE WHERE InventoryID = %s AND BrandID = 'FLQV'
            """ %inventory_id
            partslink_result = self.env['sale.order'].autoplus_execute(query)
            if partslink_result:
                result[0].update(partslink_result[0])
            return result[0]
        return False

    @api.model
    def get_product_from_autoplus_by_part_number(self, part_number):
        query = """
            SELECT TOP 1
            INV.MfgLabel,
            INV.InventoryID,
            INV.PartNo,
            INV.ProdName,
            INV.ShortDesc,
            INV.LongDesc,
            MFG.MfgCode,
            MFG.MfgName,
            PACK.Length,
            PACK.Width,
            PACK.Height,
            PACK.Weight,
            PR.Cost,
            PR.ListPrice,
            ASST.URI
            FROM Inventory INV
            LEFT JOIN InventoryPIESPack PACK ON INV.InventoryID = PACK.InventoryID
            LEFT JOIN InventoryMiscPrCur PR on INV.InventoryID = PR.InventoryID
            LEFT JOIN Mfg MFG on INV.MfgId = MFG.MfgID
            LEFT JOIN InventoryPiesASST ASST on INV.InventoryID = ASST.InventoryID
            WHERE NOT (INV.MfgID IN (3,6,18)) AND INV.PartNo = '%s'
            AND (PACK.PackUOM != 'CA' or PACK.PackUOM IS NULL)
            """ %part_number
        result = self.env['sale.order'].autoplus_execute(query)
        if result:
            query = """
                SELECT PartNo as Partslink
                FROM InventoryPiesINTE WHERE InventoryID = %s AND BrandID = 'FLQV'
            """ %result[0]['InventoryID']
            partslink_result = self.env['sale.order'].autoplus_execute(query)
            if partslink_result:
                result[0].update(partslink_result[0])
            return result[0]
        return False

    @api.model
    def prepare_product_row_from_autoplus(self, row):
        image = ''
        if row['URI']:
            try:
                image = base64.encodestring(urllib2.urlopen(row['URI']).read())
            except:
                pass
            # try:
            #     Image.open(image)
            # except:
            #     image = False
            #     _logger.warning("Bad image for product %s %s", self, row['URI'])
        return {
            'name': row['PartNo'],
            'mfg_label': row['MfgLabel'],
            'inventory_id': row['InventoryID'],
            'part_number': row['PartNo'],
            'part_type': row['ProdName'],
            'short_description': row['ShortDesc'],
            'long_description': row['LongDesc'],
            'barcode': row['PartNo'].replace('-', ''),
            'length': row['Length'],
            'width': row['Width'],
            'height': row['Height'],
            'weight': row['Weight'],
            'standard_price': row['Cost'],
            'list_price': row['ListPrice'],
            'mfg_code': row['MfgCode'],
            'mfg_name': row['MfgName'],
            'type': 'product',
            'image': image,
            'partslink': row['Partslink'] if 'Partslink' in row else '',
            'sale_delay': 2
        }

    @api.model
    def get_alt_products_from_autoplus_by_inventory_id(self, inventory_id):
        result = self.env['sale.order'].autoplus_execute(
            """
                SELECT
                ALT.InventoryIDAlt
                FROM InventoryAlt ALT
                WHERE ALT.InventoryID = %s
            """
            % (inventory_id,))
        return result

    @api.multi
    def save_alt_products(self, alt_product_rows):
        self.ensure_one()
        alt_ids = []
        for row in alt_product_rows:
            alt_id = self.search([('inventory_id', '=', row['InventoryIDAlt'])])
            if not alt_id:
                product_row = self.get_product_from_autoplus_by_inventory_id(row['InventoryIDAlt'])
                if product_row:
                    product_values = self.prepare_product_row_from_autoplus(product_row)
                    alt_id = self.create(product_values)
            if alt_id:
                alt_ids.append(alt_id.id)
        if alt_ids:
            self.write({'alternate_ids': [(6, 0, alt_ids)]})

    @api.multi
    def button_sync_with_autoplus(self, raise_exception=True):
        for product_tmpl in self:

            # Sync main product fields

            if product_tmpl.inventory_id:
                product_row = self.env['product.template'].get_product_from_autoplus_by_inventory_id(product_tmpl.inventory_id)
                if product_row:
                    product_values = self.prepare_product_row_from_autoplus(product_row)
                    product_tmpl.write(product_values)
                else:
                    if raise_exception:
                        raise UserError(_('%s does not match any inventory from AutoPlus.' %(product_tmpl.name,)))
                    _logger.error('%s does not match any inventory from AutoPlus.' %(product_tmpl.name,))
            elif product_tmpl.part_number:
                product_row = self.env['product.template'].get_product_from_autoplus_by_part_number(product_tmpl.part_number)
                if product_row:
                    product_values = self.prepare_product_row_from_autoplus(product_row)
                    existing_product = self.env['product.template'].search([('inventory_id', '=', product_values['inventory_id'])])
                    if not existing_product:
                        self.write(product_values)
                    else:
                        if raise_exception:
                            raise UserError(_('%s is a duplicate of %s.' %(product_tmpl.name, existing_product.name)))
                        _logger.error('%s is a duplicate of %s.' %(product_tmpl.name, existing_product.name))
                else:
                    if raise_exception:
                        raise UserError(_('%s does not match any inventory from AutoPlus.' %(product_tmpl.name,)))
                    _logger.error('%s does not match any inventory from AutoPlus.' %(product_tmpl.name,))
            else:
                if raise_exception:
                    raise UserError(_('Please fill in inventory ID or part number for %s.' %(product_tmpl.name)))
                _logger.error('%s does not match any inventory from AutoPlus.' %(product_tmpl.name,))

            # Sync alternate products

            alt_result = self.get_alt_products_from_autoplus_by_inventory_id(product_tmpl.inventory_id)
            if alt_result:
                product_tmpl.save_alt_products(alt_result)

            # Sync routes
            kit_result = self.get_kit_config_from_autoplus_by_inventory_id(product_tmpl.inventory_id)
            if kit_result:
                product_tmpl.write({'route_ids': [(6, 0, [self.env.ref('stock.route_warehouse0_mto').id] )]})
                bom_id = self.env['mrp.bom'].search([('product_tmpl_id', '=', product_tmpl.id)])
                if bom_id:
                    bom_id.sync_bom_with_autoplus()
                else:
                    bom_id = self.env['mrp.bom'].create({'product_tmpl_id': product_tmpl.id, 'product_qty': 1, 'type': 'normal'})
                    bom_id.sync_bom_with_autoplus()
        _logger.info("SKU %s synced with AutoPlus" % product_tmpl.name)
        return True
