# -*- coding: utf-8 -*-

import json
from odoo import http
from odoo.http import request


class StockScanLadController(http.Controller):
    @http.route('/website/get_parts', type='json', auth="none", website=True)
    def select_parts(self, year, make, model, name, **kw):
        so = request.env['sale.order']
        parts = []
        try:
            if year and make and model:
                condition = "YearID = '%s' AND MakeName = '%s' AND ModelName = '%s'" % (year, make, model)
                if name:
                    condition += " AND ProdName like '%" + name + "%'"
            else:
                return  # TODO Sure ?
            res = so.autoplus_execute("""
                SELECT 
                VEH.YearID,
                VEH.MakeName,
                VEH.ModelName,
                VEH.Trim,
                INV.PartNo,
                INV.ProdName,
                INV.MFGLabel
                FROM Inventory INV
                LEFT JOIN InventoryVcVehicle IVEH ON INV.InventoryID = IVEH.InventoryID
                LEFT JOIN VcVehicle VEH ON IVEH.VehicleID = VEH.VehicleID
                LEFT JOIN vcVehicleEngine VENG ON VEH.VehicleID = VENG.VehicleID
                WHERE %s""" % condition)
            for r in res:
                parts.append({
                    'MakeName': r['MakeName'],
                    'ModelName': r['ModelName'],
                    'YearID': r['YearID'],
                    'ProdName': r['ProdName'],
                    'PartNo': r['PartNo'],
                    'MFGLabel': r['MFGLabel'],
                    'Trim': r['Trim'],
                })
            return parts
        except Exception as e:
            return str(e)

    @http.route('/select/make', type='http', auth="none", methods=['GET'], csrf=False)
    def select_make(self, **kw):
        so = request.env['sale.order']
        makes = []
        try:
            year = int(request.params.get('year', False))
            names = so.autoplus_execute("""
                            SELECT DISTINCT MakeName
                            FROM VcVehicle
                            WHERE YearID = %s
                            ORDER BY MakeName""" % year)
            for r in names:
                makes.append({r['MakeName']: r['MakeName']})
            return json.dumps(makes)
        except Exception as e:
            return str(e)

    @http.route('/select/model', type='http', auth="none", methods=['GET'], csrf=False)
    def select_model(self, **kw):
        so = request.env['sale.order']
        models = []
        condition = '1 = 1'
        try:
            year = request.params.get('year', False)
            make = request.params.get('make', False)
            if year and make:
                condition = "YearID = '%s' AND MakeName = '%s'" % (year, make)
            elif year:
                condition = "YearID = '%s'" % year
            elif make:
                condition = "MakeName = '%s'" % make
            names = so.autoplus_execute("""
                            SELECT DISTINCT ModelName
                            FROM VcVehicle
                            WHERE %s
                            ORDER BY ModelName""" % condition)
            for r in names:
                models.append({r['ModelName']: r['ModelName']})
            return json.dumps(models)
        except Exception as e:
            return str(e)
