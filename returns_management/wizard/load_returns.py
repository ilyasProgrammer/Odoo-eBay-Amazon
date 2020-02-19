# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.exceptions import UserError, ValidationError
import logging
import openpyxl
import tempfile
import binascii
import string
from datetime import datetime

_logger = logging.getLogger(__name__)


class LoadReturns(models.TransientModel):
    _name = 'load.returns.wizard'
    _description = 'Load Returns Wizard'

    data_file = fields.Binary(string='XLS File', required=True)
    filename = fields.Char()

    @api.multi
    def import_file(self):
        """ General:
                SO exists?
                Product exists?
            Return Specific:
                Old return exists?
                    Old return line exists?
                        Old return line qty correct?
            Picking Specific:
                Old pick exists?
                    Old pick lines exists?
                    Old pick qty correct?

            """
        if not self.filename.endswith('.xlsx'):
            raise UserError('Only xlsx file format is supported to import')
        fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.data_file))
        fp.seek(0)
        data = self.excel_to_dict(fp.name, ['SO', 'LAD', 'Qty', 'Correct', 'Scrap'])
        returns_transit_location = self.env.ref('returns_management.returns_transit_location')
        returns_receipt_location = self.env['stock.location'].browse(1807)
        report = 'Execution report: \n'
        for r in data:
            # General checks
            so = self.env['sale.order'].search([('name', '=', r['SO'])])
            if len(so) < 1:
                report += '%s Sale Order does not exists\n' % r['SO']
                continue
            product = self.env['product.product'].search([('name', '=', r['LAD'])])
            if len(product) < 1:
                report += 'Cant find product for SO %s LAD %s\n' % (r['SO'], r['LAD'])
                continue
            old_return = self.env['sale.return'].search([('sale_order_id', '=', so.id)])
            report += '\n'
            # Old return
            if old_return:
                # TODO check all here
                report += '%s return for %s already exists\n' % (old_return.id, r['SO'])
                has_line = False
                if old_return.return_line_ids:
                    for l in old_return.return_line_ids:
                        if l.product_id.name == r['LAD']:
                            report += '%s return for %s has this LAD %s\n' % (old_return.id, r['SO'], r['LAD'])
                            has_line = True
                            if l.product_uom_qty == int(r['Qty']):
                                report += '%s return for %s has correct qty %s for LAD %s\n' % (old_return.id, r['SO'], r['Qty'], r['LAD'])
                            else:
                                report += '%s return for %s had WRONG qty %s for LAD %s\n' % (old_return.id, r['SO'], r['Qty'], r['LAD'])
                                l.product_uom_qty = int(r['Qty'])
                            break
                    if not has_line:
                        line_vals = {
                            'sale_order_id': so.id,
                            'return_id': old_return.id,
                            'name': r['LAD'],
                            'product_id': product.id,
                            'product_uom_qty': r['Qty'],
                            'sale_line_id': False,
                        }
                        new_ret_line = self.env['sale.return.line'].create(line_vals)
                if old_return.receipt_picking_ids:
                    for rp in old_return.receipt_picking_ids:
                        if rp.state not in ['cancel', 'done']:
                            report += '%s return has picking\n' % old_return.id
                            has_pick_line = False
                            for rpl in rp.move_lines:
                                if rpl.product_id == product:
                                    has_pick_line = True
                                    report += '%s return has correct LAD in picking %s\n' % (old_return.id, rp.id)
                                    if rpl.product_qty == int(r['Qty']):
                                        report += '%s return has correct Qty in picking %s\n' % (old_return.id, rp.id)
                                    else:
                                        report += '%s return for %s had WRONG qty %s for LAD %s in picking %s\n' % (old_return.id, r['SO'], r['Qty'], r['LAD'], rp.id)
                                        rpl.product_qty = int(r['Qty'])
                                    break
                            if not has_pick_line:
                                # TODO Create move line
                                pass
                else:
                    # TODO Create picking and move
                    pass

            # New return
            else:
                new_ret_id = self.env['sale.return'].create({'sale_order_id': so.id, 'request_date': datetime.now()})
                line_vals = {
                    'sale_order_id': False,
                    'return_id': new_ret_id.id,
                    'name': r['LAD'],
                    'product_id': product.id,
                    'product_uom_qty': int(r['Qty']),
                    'qty_received': int(r['Qty']),
                    'product_uom': self.env.ref('product.product_uom_unit').id,
                    'sale_line_id': False,
                }
                new_ret_line = self.env['sale.return.line'].create(line_vals)
                new_ret_id.create_picking_for_receipt()
                report += 'New return created %s %s %s\n' % (r['SO'], r['Qty'], r['LAD'])

                # Picking
                new_ret_id.receive_return_in_wh_button(triggered=True, location=returns_receipt_location)
                # self.env.cr.commit()

                # Scrap
                if bool(r['Scrap']):
                    pick = new_ret_id.receipt_picking_ids
                    for move in pick.move_lines:
                        self.env['stock.scrap'].create({
                            'location_id': returns_receipt_location.id,
                            'scrap_location_id': returns_transit_location.id,
                            'product_id': move.product_id.id,
                            'product_uom_id': move.product_id.uom_id.id,
                            'scrap_qty': move.product_uom_qty,
                            'picking_id': pick.id,
                            'origin': pick.name
                        })
                        report += 'Scrapped %s %s %s\n' % (r['SO'], r['Qty'], r['LAD'])
                        for quant in move.quant_ids:
                            quant.landed_cost = move.landed_cost
                            quant.cost = quant.product_cost + move.landed_cost if quant.product_cost else move.price_unit + move.landed_cost
        return {
            'name': 'Report',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'custom.message',
            'target': 'new',
            'context': {'default_text': report}
        }

    @api.model
    def excel_to_dict(self, excel_path, headers=[]):
        wb = openpyxl.load_workbook(excel_path)
        sheet = wb.worksheets[0]
        result_dict = []
        for row in range(2, sheet.max_row + 1):
            line = dict()
            for header in headers:
                cell_value = sheet[self.index_to_col(headers.index(header)) + str(row)].value
                if type(cell_value) is unicode:
                    cell_value = cell_value.encode('utf-8').decode('ascii', 'ignore')
                    cell_value = cell_value.strip()
                elif type(cell_value) is int:
                    cell_value = str(cell_value)
                elif cell_value is None:
                    cell_value = ''
                line[header] = cell_value
            result_dict.append(line)
        return result_dict

    @api.model
    def index_to_col(self, index):
        return string.uppercase[index]
