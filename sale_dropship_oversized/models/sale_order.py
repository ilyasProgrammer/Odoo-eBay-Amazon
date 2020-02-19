# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def button_set_routes(self, raise_exception=True):
        self.ensure_one()
        # Check availability in warehouse
        for line in self.order_line:
            if self.amz_order_type == 'fba':
                loc = self.env['stock.location'].search([('barcode', '=', 'Amazon FBA')])
                query = """
                    SELECT QUANT.qty,  LOC.id, LOC.complete_name
                    FROM stock_quant QUANT
                    LEFT JOIN stock_location LOC
                    ON QUANT.location_id = LOC.id
                    LEFT JOIN product_product PRODUCT
                    ON PRODUCT.id = QUANT.product_id
                    LEFT JOIN product_template TEMPLATE ON TEMPLATE.id = PRODUCT.product_tmpl_id
                    WHERE LOC.usage = 'internal' AND QUANT.qty > 0 AND QUANT.reservation_id IS NULL
                    AND (TEMPLATE.oversized = False OR TEMPLATE.oversized IS NULL)
                    AND LOC.id = %s
                    AND PRODUCT.id = %s
                    AND QUANT.qty >= %s
                """ % (loc.id, line.product_id.id, line.product_uom_qty)
                self.env.cr.execute(query)
                quants = self.env.cr.fetchall()
                if not len(quants):
                    self.write({'not_available_in_all': True})
                    return
                else:
                    route_id = self.env['stock.location.route'].search([('name', '=', 'Amazon FBA')])
                    if route_id:
                        line.write({'route_id': route_id.id})
            else:
                query = """
                    SELECT QUANT.qty,  LOC.id, LOC.complete_name
                    FROM stock_quant QUANT
                    LEFT JOIN stock_location LOC
                    ON QUANT.location_id = LOC.id
                    LEFT JOIN product_product PRODUCT
                    ON PRODUCT.id = QUANT.product_id
                    LEFT JOIN product_template TEMPLATE ON TEMPLATE.id = PRODUCT.product_tmpl_id
                    WHERE LOC.usage = 'internal' AND QUANT.qty > 0 AND QUANT.reservation_id IS NULL
                    -- AND (TEMPLATE.oversized = False OR TEMPLATE.oversized IS NULL)  we have new FedEx Oversized account in 2019
                    AND PRODUCT.id = %s
                    AND QUANT.qty >= %s
                    AND LOC.name NOT IN ('Output', 'Amazon FBA')
                """ % (line.product_id.id, line.product_uom_qty)
                self.env.cr.execute(query)
                quants = self.env.cr.fetchall()
                if quants:
                    route_id = self.warehouse_id.delivery_route_id.id
                    line.write({'route_id': route_id})

        # Check which supplier has all the remaining and which has lower price
        # If no warehouse can accommodate all lines, choose cheapest per line
        lines_to_process = self.order_line.filtered(lambda r: len(r.route_id) == 0)
        if lines_to_process:
            inventory_ids = []
            for line in lines_to_process:
                inventory_ids.append(line.product_id.inventory_id)
            proc_rules = self.env['procurement.rule'].search([('action', '=', 'buy'), ('mfg_codes', '!=', False)])
            supplier_costs = []
            supplier_totals = []
            for rule in proc_rules:
                query = ""
                counter = 1
                for line in lines_to_process:
                    reqd_qty = max(rule.min_qty, line.product_uom_qty)
                    subquery = """
                        (SELECT ALT.InventoryID, PR.Cost
                        FROM InventoryAlt ALT
                        LEFT JOIN Inventory INV on ALT.InventoryIDAlt = INV.InventoryID
                        LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
                        LEFT JOIN Mfg MFG ON INV.MfgID = MFG.MfgId
                        WHERE MFG.MfgCode IN (%s) AND INV.QtyOnHand >= %s AND ALT.InventoryID = %s AND (PR.Cost - %s) < 20)

                        UNION

                        (SELECT INV.InventoryID, PR.Cost
                        FROM Inventory INV
                        LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
                        LEFT JOIN Mfg MFG ON INV.MfgID = MFG.MfgId
                        WHERE MFG.MfgCode IN (%s) AND INV.QtyOnHand >= %s AND INV.InventoryID = %s AND (PR.Cost - %s) < 20)

                    """ % (rule.mfg_codes, reqd_qty, line.product_id.inventory_id, line.price_unit, rule.mfg_codes, reqd_qty, line.product_id.inventory_id, line.price_unit)
                    if len(lines_to_process) == 1:
                        subquery = subquery[1:-1]
                    query += subquery
                    if counter < len(lines_to_process):
                        query += ' UNION '
                    counter += 1
                result = self.autoplus_execute(query)

                total_cost = 0
                for row in result:
                    total_cost += float(row['Cost'])
                    row.update({'rule': rule.id})

                supplier_costs += result

                # This part checks if all inventory ids are present in the result
                complete = False
                for inventory_id in inventory_ids:
                    found = False
                    for row in result:
                        if row['InventoryID'] == inventory_id:
                            found = True
                            break
                    if not found:
                        break
                else:
                    complete = True
                if complete:
                    supplier_totals.append({'rule': rule.id, 'cost': total_cost})

            if supplier_totals:
                supplier_totals = sorted(supplier_totals, key=lambda k: k['cost'])
                proc_rules = self.env['procurement.rule'].search([('action', '=', 'buy'), ('mfg_codes', '!=', False)])
                rule_id = self.env['procurement.rule'].browse([supplier_totals[0]['rule']])
                for line in lines_to_process:
                    cost = list(filter(lambda d: d['InventoryID'] == line.product_id.inventory_id and d['rule'] == rule_id.id, supplier_costs))[0]['Cost']
                    route_id = rule_id.route_id
                    if 'PPR' in route_id.name and line.product_id.product_tmpl_id.avoid_ppr:
                        # Bad code for bad business logic
                        route_id = route_id.search([('name', '=', 'Fairchild: Drop Shipping')])
                        pricelist_id = self.env['product.supplierinfo'].search([
                            ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                            ('name', '=', 17)
                        ])
                        if len(pricelist_id) > 1:  # tmp fix
                            pricelist_id = pricelist_id[0]
                        cost = pricelist_id.price if pricelist_id.price > 0 else cost
                    line.write({'route_id': route_id.id, 'dropship_cost': cost })

            else:
                for line in lines_to_process:
                    costs = sorted(list(filter(lambda d: d['InventoryID'] == line.product_id.inventory_id, supplier_costs)), key=lambda k: k['Cost'])
                    if costs:
                        cost = float(costs[0]['Cost'])
                        rule_id = self.env['procurement.rule'].browse([costs[0]['rule']])
                        route_id = rule_id.route_id
                        if 'PPR' in route_id.name and line.product_id.product_tmpl_id.avoid_ppr:
                            # Bad code for bad business logic
                            route_id = route_id.search([('name', '=', 'Fairchild: Drop Shipping')])
                            pricelist_id = self.env['product.supplierinfo'].search([
                                ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                                ('name', '=', 17)
                            ])
                            cost = pricelist_id.price if pricelist_id.price > 0 else cost
                        line.write({'route_id': route_id.id, 'dropship_cost': cost})

        for line in self.order_line:
            if not line.route_id:
                self.write({'not_available_in_all': True})
                break
        else:
            self.write({'not_available_in_all': False})

    @api.multi
    def button_set_losy_routes(self, raise_exception=True):
        self.ensure_one()
        # Check availability in warehouse
        for line in self.order_line:
            if self.amz_order_type == 'fba':
                loc = self.env['stock.location'].search([('barcode', '=', 'Amazon FBA')])
                query = """
                    SELECT QUANT.qty,  LOC.id, LOC.complete_name
                    FROM stock_quant QUANT
                    LEFT JOIN stock_location LOC
                    ON QUANT.location_id = LOC.id
                    LEFT JOIN product_product PRODUCT
                    ON PRODUCT.id = QUANT.product_id
                    LEFT JOIN product_template TEMPLATE ON TEMPLATE.id = PRODUCT.product_tmpl_id
                    WHERE LOC.usage = 'internal' AND QUANT.qty > 0 AND QUANT.reservation_id IS NULL
                    AND (TEMPLATE.oversized = False OR TEMPLATE.oversized IS NULL)
                    AND LOC.id = %s
                    AND PRODUCT.id = %s
                    AND QUANT.qty >= %s
                """ % (loc.id, line.product_id.id, line.product_uom_qty)
                self.env.cr.execute(query)
                quants = self.env.cr.fetchall()
                if not len(quants):
                    self.write({'not_available_in_all': True})
                    return
                else:
                    route_id = self.env['stock.location.route'].search([('name', '=', 'Amazon FBA')])
                    if route_id:
                        line.write({'route_id': route_id.id})
            else:
                query = """
                    SELECT QUANT.qty,  LOC.id, LOC.complete_name
                    FROM stock_quant QUANT
                    LEFT JOIN stock_location LOC
                    ON QUANT.location_id = LOC.id
                    LEFT JOIN product_product PRODUCT
                    ON PRODUCT.id = QUANT.product_id
                    LEFT JOIN product_template TEMPLATE ON TEMPLATE.id = PRODUCT.product_tmpl_id
                    WHERE LOC.usage = 'internal' AND QUANT.qty > 0 AND QUANT.reservation_id IS NULL
                    -- AND (TEMPLATE.oversized = False OR TEMPLATE.oversized IS NULL)
                    AND PRODUCT.id = %s
                    AND QUANT.qty >= %s
                    AND LOC.name NOT IN ('Output', 'Amazon FBA')
                """ % (line.product_id.id, line.product_uom_qty)
                self.env.cr.execute(query)
                quants = self.env.cr.fetchall()
                if quants:
                    route_id = self.warehouse_id.delivery_route_id.id
                    line.write({'route_id': route_id})

        # Check which supplier has all the remaining and which has lower price
        # If no warehouse can accommodate all lines, choose cheapest per line
        lines_to_process = self.order_line.filtered(lambda r: len(r.route_id) == 0)
        if lines_to_process:
            inventory_ids = []
            for line in lines_to_process:
                inventory_ids.append(line.product_id.inventory_id)
            proc_rules = self.env['procurement.rule'].search([('action', '=', 'buy'), ('mfg_codes', '!=', False)])
            supplier_costs = []
            supplier_totals = []
            for rule in proc_rules:
                query = ""
                counter = 1
                for line in lines_to_process:
                    reqd_qty = max(rule.min_qty, line.product_uom_qty)
                    subquery = """
                        (SELECT ALT.InventoryID, PR.Cost
                        FROM InventoryAlt ALT
                        LEFT JOIN Inventory INV on ALT.InventoryIDAlt = INV.InventoryID
                        LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
                        LEFT JOIN Mfg MFG ON INV.MfgID = MFG.MfgId
                        WHERE MFG.MfgCode IN (%s) AND INV.QtyOnHand >= %s AND ALT.InventoryID = %s)

                        UNION

                        (SELECT INV.InventoryID, PR.Cost
                        FROM Inventory INV
                        LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
                        LEFT JOIN Mfg MFG ON INV.MfgID = MFG.MfgId
                        WHERE MFG.MfgCode IN (%s) AND INV.QtyOnHand >= %s AND INV.InventoryID = %s)

                    """ % (rule.mfg_codes, reqd_qty, line.product_id.inventory_id, rule.mfg_codes, reqd_qty, line.product_id.inventory_id)
                    if len(lines_to_process) == 1:
                        subquery = subquery[1:-1]
                    query += subquery
                    if counter < len(lines_to_process):
                        query += ' UNION '
                    counter += 1
                result = self.autoplus_execute(query)

                total_cost = 0
                for row in result:
                    total_cost += float(row['Cost'])
                    row.update({'rule': rule.id})

                supplier_costs += result

                # This part checks if all inventory ids are present in the result
                complete = False
                for inventory_id in inventory_ids:
                    found = False
                    for row in result:
                        if row['InventoryID'] == inventory_id:
                            found = True
                            break
                    if not found:
                        break
                else:
                    complete = True
                if complete:
                    supplier_totals.append({'rule': rule.id, 'cost': total_cost})

            if supplier_totals:
                supplier_totals = sorted(supplier_totals, key=lambda k: k['cost'])
                proc_rules = self.env['procurement.rule'].search([('action', '=', 'buy'), ('mfg_codes', '!=', False)])
                rule_id = self.env['procurement.rule'].browse([supplier_totals[0]['rule']])
                for line in lines_to_process:
                    cost = list(filter(lambda d: d['InventoryID'] == line.product_id.inventory_id and d['rule'] == rule_id.id, supplier_costs))[0]['Cost']
                    route_id = rule_id.route_id
                    if 'PPR' in route_id.name and line.product_id.product_tmpl_id.avoid_ppr:
                        # Bad code for bad business logic
                        route_id = route_id.search([('name', '=', 'Fairchild: Drop Shipping')])
                        pricelist_id = self.env['product.supplierinfo'].search([
                            ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                            ('name', '=', 17)
                        ])
                        if len(pricelist_id) > 1:  # tmp fix
                            pricelist_id = pricelist_id[0]
                        cost = pricelist_id.price if pricelist_id.price > 0 else cost
                    line.write({'route_id': route_id.id, 'dropship_cost': cost })

            else:
                for line in lines_to_process:
                    costs = sorted(list(filter(lambda d: d['InventoryID'] == line.product_id.inventory_id, supplier_costs)), key=lambda k: k['Cost'])
                    if costs:
                        cost = float(costs[0]['Cost'])
                        rule_id = self.env['procurement.rule'].browse([costs[0]['rule']])
                        route_id = rule_id.route_id
                        if 'PPR' in route_id.name and line.product_id.product_tmpl_id.avoid_ppr:
                            # Bad code for bad business logic
                            route_id = route_id.search([('name', '=', 'Fairchild: Drop Shipping')])
                            pricelist_id = self.env['product.supplierinfo'].search([
                                ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                                ('name', '=', 17)
                            ])
                            cost = pricelist_id.price if pricelist_id.price > 0 else cost
                        line.write({'route_id': route_id.id, 'dropship_cost': cost})

        for line in self.order_line:
            if not line.route_id:
                self.write({'not_available_in_all': True})
                break
        else:
            self.write({'not_available_in_all': False})
