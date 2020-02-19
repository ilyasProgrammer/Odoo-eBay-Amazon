# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import urllib


class report_zebra_producttemplatelabel(models.AbstractModel):
    _name = 'report.lable_zabra_printer.report_zebra_producttemplatelabel'
    _template = 'lable_zabra_printer.report_zebra_producttemplatelabel'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('lable_zabra_printer.report_zebra_producttemplatelabel')
        docargs = {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': self.env['product.template'].browse(docids),
        }
        return report_obj.render('lable_zabra_printer.report_zebra_producttemplatelabel', docargs)
