# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pymssql

from odoo import http
from odoo.http import request

class ProductMoreInfo(http.Controller):

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

    @http.route('/autoplus/products/<model("product.template"):product_tmpl>', type='http', auth="user")
    def autoplus_products(self, product_tmpl=None):
        values = {}
        product_row = request.env['sale.order'].autoplus_execute("""
            SELECT 
            PartNo,
            ProdName,
            MfgLabel 
            FROM Inventory INV 
            WHERE INV.InventoryID = %s
        """ %product_tmpl.inventory_id)
        if product_row:
            values.update(product_row[0])
            picture_urls = request.env['sale.order'].autoplus_execute("""
                SELECT
                ASST.URI
                FROM Inventory INV
                LEFT JOIN InventoryPiesASST ASST on INV.InventoryID = ASST.InventoryID
                WHERE INV.InventoryID = %s
            """ %product_tmpl.inventory_id)

            PictureURLs = []
            for p in picture_urls:
                if p['URI'] != None:
                    PictureURLs.append(p['URI'])

            values.update({'PictureURLs': PictureURLs})

            vehicles = request.env['sale.order'].autoplus_execute("""
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
            """ %product_tmpl.inventory_id)

            vehicle_rows = []
            for c in vehicles:
                row = {'Make': c['MakeName'], 'Model': c['ModelName'], 'Year': c['YearID'], 'Trim': 'All', 'Engine': 'All'}
                if c['Trim']:
                    row['Trim'] = c['Trim']
                if c['EngineID']:
                    row['Engine'] = self.compute_engine(c)
                vehicle_rows.append(row)

            values.update({'Vehicles': vehicle_rows})

        return request.render('product_info.autoplus_product_info', values)
