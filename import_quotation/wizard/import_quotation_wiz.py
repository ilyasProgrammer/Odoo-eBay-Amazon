# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import csv

from odoo import models, fields, api, _
from odoo.exceptions import UserError

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class ImportQuotationWizard(models.TransientModel):
    _name = 'import.quotation.wizard'

    data_file = fields.Binary(string='Quotation File', required=True)
    filename = fields.Char()

    def _create_quotation(self, datas):
        for data in datas:
            quotation_wiz = self.env['create.quotation.wizard'].create(data)
            quotation_wiz.create_quotation()
            self.env.cr.commit()

    @api.multi
    def import_file(self):
        self.ensure_one()
        if not self.filename.endswith('.csv'):
            raise UserError(_('Only csv file format is supported to import quotation'))
        data = csv.reader(StringIO(base64.b64decode(self.data_file)), quotechar='"', delimiter=',')
        # Read the column names from the first line of the file
        fields = data.next()
        datas = []
        for row in data:
            items = dict(zip(fields, row))
            datas.append(items)
        return self._create_quotation(datas)
