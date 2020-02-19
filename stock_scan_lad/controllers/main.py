# -*- coding: utf-8 -*-

import csv

from cStringIO import StringIO
from datetime import datetime, timedelta
from pytz import timezone

from odoo import http, _
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class StockScanLadController(http.Controller):

    @http.route('/scan_lad/get_products', type='json', auth='user')
    def scan_lad_get_product(self, barcode, **kw):
        res = []
        prod_recs = []
        barcode = barcode.strip()
        prod_mod = request.env['product.template']
        info_mod = request.env['product.supplierinfo']
        domain = ['|', '|',
                  ('partslink', '=', barcode),  # Char
                  ('part_number', '=', barcode),  # Char
                  ('barcode', '=', barcode)]  # Char
        all_prod_recs = prod_mod.search(domain)
        if not all_prod_recs:  # then maybe present in product.supplierinfo
            infos = info_mod.search([('barcode_unit', '=', barcode)])
            if len(infos) == 1:
                all_prod_recs = infos.product_tmpl_id
            elif len(infos) > 1:  # take product from every info
                for info in infos:
                    all_prod_recs += info.product_tmpl_id
        orig_prod_recs = all_prod_recs.filtered(lambda r: r.mfg_code == 'ASE')
        if orig_prod_recs:
            prod_recs = orig_prod_recs
        else:
            alter_prod_recs = all_prod_recs.filtered(lambda r: r.mfg_code != 'ASE')
            if len(alter_prod_recs) == 1:
                if alter_prod_recs.alternate_ids:
                    prod_recs = alter_prod_recs.alternate_ids
                else:
                    prod_recs = alter_prod_recs  # only case when shown nonoriginal parts
            elif len(alter_prod_recs) > 1:
                for alter_prod_rec in alter_prod_recs:
                    if alter_prod_rec.alternate_ids:
                        prod_recs += alter_prod_rec.alternate_ids
                    else:
                        prod_recs += alter_prod_rec  # there is no original for that item. then take nonoriginal
        if prod_recs:
            for prod_rec in prod_recs:
                res.append({'name': prod_rec.name,
                            'id': prod_rec.id,
                            'long_description': prod_rec.long_description,
                            'mfg_label': prod_rec.mfg_label,
                            'mfg_code': prod_rec.mfg_code})
        else:
            res = None
        return res

    @http.route('/scan_lad/print_label', type='json', auth='user')
    def scan_lad_print_label(self, product_id, **kw):
        prod_mod = request.env['product.template']
        prod_rec = prod_mod.browse(int(product_id))
        action_product_report = request.env.ref('lable_zabra_printer.report_product_template_label')
        action_product_report = action_product_report.read()[0]
        action_product_report['domain'] = [('id', '=', prod_rec.id)]
        if kw.get('copies'):
            action_product_report['context'] = {'copies': int(kw['copies'])}
        return {'action': action_product_report}
