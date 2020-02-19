# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.exceptions import ValidationError
import pymssql
import logging

_logger = logging.getLogger(__name__)


class SyncProducts(models.TransientModel):
    _name = 'product.sync.wizard'
    _description = 'Product Sync Wizard'

    lads = fields.Text('LADs to import')
    for_vendor_pns = fields.Boolean("By Vendor Part Numbers", default=False)
    vendor_id = fields.Many2one('res.partner', 'Vendor', domain=[('supplier', '=', True), ('is_company', '=', True)])
    vendor_pns = fields.Text('Vendor Part Numbers')

    @api.multi
    def button_sync_products(self):
        _logger.info('Started Product syncing called by product sync wizard.')
        res = 'Execution report: \n'
        conn = pymssql.connect('192.169.152.87', 'UsmanRaja', 'Nop@ss786', 'AutoPlus')
        cur = conn.cursor(as_dict=True)
        if self.for_vendor_pns:
            if not self.vendor_pns or len(self.vendor_pns) == 0:
                raise ValidationError("Please enter Vendor Part Numbers.")  # REPA311520,REPA462957
            if not self.vendor_id:
                raise ValidationError("Please select Vendor.")
            pns_list = self.vendor_pns.replace(' ', '').split(',')
            query = """SELECT INV.PartNo VENDOR_SKU, INV2.PartNo PartNo, INV2.InventoryId
                       FROM Inventory INV
                       LEFT JOIN InventoryAlt ALT ON ALT.InventoryIDAlt = INV.InventoryID
                       LEFT JOIN Inventory INV2 ON ALT.InventoryID = INV2.InventoryID
                       LEFT JOIN Mfg MFG on MFG.MfgID = INV.MfgID
                       WHERE MFG.MfgCode in (%s) AND INV.PartNo in %s
                       ORDER BY INV.InventoryID ASC""" % (self.vendor_id.mfg_codes, list_to_sql_str(pns_list))
        else:
            if not self.lads or len(self.lads) == 0:
                raise ValidationError("Please enter LAD SKUs.")
            lads_list = self.lads.replace(' ', '').split(',')
            query = """SELECT INV.InventoryId, INV.PartNo FROM Inventory INV
                       WHERE INV.MfgId = 1 AND PartNo in %s
                       ORDER BY INV.InventoryID ASC""" % list_to_sql_str(lads_list)
        cur.execute(query)
        inv_ids = cur.fetchall()
        for inv_id in inv_ids:
            old_prod = self.env['product.template'].search(['|', ('name', '=', inv_id['PartNo']), ('inventory_id', '=', int(inv_id['InventoryId']))])
            if old_prod:
                _logger.info('Product already exist %s' % old_prod.name)
                prod = old_prod
                res += '%s already exist \n' % old_prod.name
            else:
                prod = self.env['product.template'].create({'name': inv_id['PartNo'], 'inventory_id': inv_id['InventoryId']})
                _logger.info('New product created: %s %s', prod.name, prod.inventory_id)
                res += '%s created \n' % prod.name
            prod.button_sync_with_autoplus()
            # Sync specs and attributes
            self.sync_specs(prod)
            self.sync_attrs(prod)
            res += '%s synced \n' % prod.name

        return {
            'name': 'Report',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'custom.message',
            'target': 'new',
            'context': {'default_text': res}
        }

    def sync_specs(self, prod):
        LISTING_SPECIFIC = ['Brand', 'Manufacturer Part Number', 'Warranty']
        mssql_conn = pymssql.connect('192.169.152.87', 'UsmanRaja', 'Nop@ss786', 'AutoPlus')

        mssql_cur = mssql_conn.cursor(as_dict=True)
        query = """SELECT INV2.PartNo , SPEC.Specification, SPEC.Description 
                    FROM USAPFitment.dbo.Specifications SPEC
                    LEFT JOIN USAPFitment.dbo.PartNumbers PN ON SPEC.PartID = PN.PartID
                    LEFT JOIN Inventory INV ON INV.PartNo = PN.PartNo
                    LEFT JOIN InventoryAlt ALT ON ALT.InventoryIDAlt = INV.InventoryID
                    LEFT JOIN Inventory INV2 ON ALT.InventoryID = INV2.InventoryID
                    WHERE INV2.MfgID = 1  
                    AND INV2.PartNo = '%s'
                    ORDER BY partno, Specification, Description""" % prod.name
        logging.info('Reading specs from autoplus ...')
        mssql_cur.execute(query)
        autoplus_vals = mssql_cur.fetchall()
        for attr in autoplus_vals:
            if attr['Specification'] in LISTING_SPECIFIC:
                continue
            attr_id = self.env['product.item.specific.attribute'].search([('name', '=', attr['Specification'])])
            if not attr_id:
                attr_id = self.env['product.item.specific.attribute'].create({'name': attr['Specification']})
                _logger.info('New item specific: %s', attr['Specification'])
            else:
                attr_id = attr_id[0]
            val_id = self.env['product.item.specific.value'].search([('name', '=', attr['Description']), ('item_specific_attribute_id', '=', attr_id.id)])
            if not val_id:
                val_id = self.env['product.item.specific.value'].create({'name': attr['Description'],
                                                                         'item_specific_attribute_id': attr_id.id})
            if len(val_id) > 1:
                val_id = val_id[0]
                _logger.info('New spec value: %s %s', attr['Specification'], attr['Description'])
            line_id = self.env['product.item.specific.line'].search([('product_tmpl_id', '=', prod.id),
                                                                     ('item_specific_attribute_id', '=', attr_id.id),
                                                                     ('value_id', '=', val_id.id)])
            if not line_id:
                self.env['product.item.specific.line'].create({'product_tmpl_id': prod.id,
                                                               'item_specific_attribute_id': attr_id.id,
                                                               'value_id': val_id.id})
                _logger.info('New spec line: %s %s %s', prod.name, attr['Specification'], attr['Description'])

    def sync_attrs(self, prod):
        mssql_conn = pymssql.connect('192.169.152.87', 'UsmanRaja', 'Nop@ss786', 'AutoPlus')

        mssql_cur = mssql_conn.cursor(as_dict=True)
        query = """SELECT  *
                   FROM USAPFitment.dbo.Features FEA
                   LEFT JOIN USAPFitment.dbo.PartNumbers PN on FEA.PartID = PN.PartID
                   LEFT JOIN Inventory INV on INV.PartNo = PN.PartNo
                   LEFT JOIN InventoryAlt ALT on ALT.InventoryIDAlt = INV.InventoryID
                   LEFT JOIN Inventory INV2 on ALT.InventoryID = INV2.InventoryID
                   WHERE INV2.MfgID = 1   
                   AND INV2.PartNo = '%s'""" % prod.name
        logging.info('Reading attrs from autoplus ...')
        mssql_cur.execute(query)
        autoplus_vals = mssql_cur.fetchall()
        for attr in autoplus_vals:
            attr_id = self.env['product.auto.attribute'].search([('name', '=', attr['Feature'])])
            if not attr_id:
                attr_id = self.env['product.auto.attribute'].create({'name': attr['Feature']})
                _logger.info('New product auto attribute: %s', attr['Feature'])
            else:
                attr_id = attr_id[0]

            val_id = self.env['product.auto.attribute.value'].search([('name', '=', attr['Description']), ('auto_attribute_id', '=', attr_id.id)])
            if not val_id:
                val_id = self.env['product.auto.attribute.value'].create({'name': attr['Description'],
                                                                          'auto_attribute_id': attr_id.id})
                _logger.info('New attribute value: %s %s', attr['Feature'], attr['Description'])
            if len(val_id) > 1:
                val_id = val_id[0]

            line_id = self.env['product.auto.attribute.line'].search([('product_tmpl_id', '=', prod.id),
                                                                      ('auto_attribute_id', '=', attr_id.id),
                                                                      ('value_ids', 'in', val_id.id)])
            if not line_id:
                self.env['product.auto.attribute.line'].create({'product_tmpl_id': prod.id,
                                                                'auto_attribute_id': attr_id.id,
                                                                'value_ids': [(6, 0, [val_id.id])]})
                _logger.info('New attribute line: %s %s %s', prod.name, attr['Feature'], attr['Description'])

    def execute_with_commit(self, q):
        self._cr.execute(q)
        self._cr.commit()


def list_to_sql_str(data_list):
    qry = ''
    for el in data_list:
        qry += "'" + el + "' ,"
    qry = '(' + qry[:-1] + ")"
    return qry


