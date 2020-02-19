# -*- coding: utf-8 -*-

import base64
import csv
from cStringIO import StringIO
from odoo import api, models, tools


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def onchange_template_id(self, template_id, composition_mode, model, res_id):
        """ - mass_mailing: we cannot render, so return the template values
            - normal mode: return rendered values
            /!\ for x2many field, this onchange return command instead of ids
        """
        if template_id and composition_mode == 'mass_mail':
            template = self.env['mail.template'].browse(template_id)
            fields = ['subject', 'body_html', 'email_from', 'reply_to', 'mail_server_id']
            values = dict((field, getattr(template, field)) for field in fields if getattr(template, field))
            if template.attachment_ids:
                values['attachment_ids'] = [att.id for att in template.attachment_ids]
            if template.mail_server_id:
                values['mail_server_id'] = template.mail_server_id.id
            if template.user_signature and 'body_html' in values:
                signature = self.env.user.signature
                values['body_html'] = tools.append_content_to_html(values['body_html'], signature, plaintext=False)
        elif template_id:
            values = self.generate_email_for_composer(template_id, [res_id])[res_id]
            # transform attachments into attachment_ids; not attached to the document because this will
            # be done further in the posting process, allowing to clean database if email not send
            Attachment = self.env['ir.attachment']
            for attach_fname, attach_datas in values.pop('attachments', []):
                datas = []
                data_attach = {
                    'name': attach_fname,
                    'datas': attach_datas,
                    'datas_fname': attach_fname,
                    'res_model': 'mail.compose.message',
                    'res_id': 0,
                    'type': 'binary',  # override default_type from context, possibly meant for another model!
                }
                datas.append(data_attach)
                if self.env.context.get('active_model') == 'purchase.order':
                    fp = StringIO()
                    writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
                    data_list = [['product_number', 'vendor_product_number', 'mfg_label', 'partslink', 'qty_ordered', 'cost', 'extended_cost', 'volume_per_piece', 'extended_volume']]
                    lines = self.env['purchase.order'].browse(self.env.context.get('active_id')).order_line
                    for line in lines:
                        supplier_info = line.product_id.seller_ids.filtered(lambda rec: rec.name == line.order_id.partner_id)
                        if len(supplier_info) > 1:
                            for r in supplier_info:
                                if r.product_code:
                                    supplier_info = r
                            if len(supplier_info) > 1:
                                supplier_info = supplier_info[0]
                        volume = (supplier_info.cu_ft * line.product_qty)
                        data_list.append([
                            line.product_id.name or None,
                            supplier_info.product_code or None,
                            line.product_id.mfg_label or None,
                            line.partslink or None,
                            line.product_qty or None,
                            line.price_unit or None,
                            (line.price_unit * line.product_qty) or None,
                            volume or None,
                            (supplier_info.cu_ft * line.product_qty) or None,
                        ])

                    csv_writer = csv.writer(fp)
                    for i in data_list:
                        csv_writer.writerow([x for x in i])
                    fp.seek(0)
                    data = fp.read()
                    csv_attach_datas = base64.b64encode(data)

                    csv_data_attach = {
                        'name': attach_fname.split('.')[0] + '.csv',
                        'datas': csv_attach_datas,
                        'datas_fname': attach_fname.split('.')[0] + '.csv',
                        'res_model': 'mail.compose.message',
                        'res_id': 0,
                        'type': 'binary',  # override default_type from context, possibly meant for another model!
                    }
                    datas.append(csv_data_attach)
                if datas:
                    attch_ids = []
                    for j in datas:
                        att_id = Attachment.create(j)
                        attch_ids.append(att_id.id)
                    for k in attch_ids:
                        values.setdefault('attachment_ids', list()).append(k)
        else:
            default_values = self.with_context(default_composition_mode=composition_mode, default_model=model, default_res_id=res_id).default_get(['composition_mode', 'model', 'res_id', 'parent_id', 'partner_ids', 'subject', 'body', 'email_from', 'reply_to', 'attachment_ids', 'mail_server_id'])
            values = dict((key, default_values[key]) for key in ['subject', 'body', 'partner_ids', 'email_from', 'reply_to', 'attachment_ids', 'mail_server_id'] if key in default_values)

        if values.get('body_html'):
            values['body'] = values.pop('body_html')

        # This onchange should return command instead of ids for x2many field.
        # ORM handle the assignation of command list on new onchange (api.v8),
        # this force the complete replacement of x2many field with
        # command and is compatible with onchange api.v7
        values = self._convert_to_write(values)
        return {'value': values}
