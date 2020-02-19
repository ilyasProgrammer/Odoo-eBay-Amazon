# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_log = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def action_assign(self, no_prepare=False):
        """ Checks the product type and accordingly writes the state. """
        # TDE FIXME: remove decorator once everything is migrated
        # TDE FIXME: clean me, please
        main_domain = {}
        Quant = self.env['stock.quant']
        moves_to_assign = self.env['stock.move']
        moves_to_do = self.env['stock.move']
        operations = self.env['stock.pack.operation']
        Bom = self.env['mrp.bom']
        BomLine = self.env['mrp.bom.line']
        ancestors_list = {}
        returns_list = {}

        # Sometimes, buyers buy kits from separate listings (meaning, order is a kit but has no kit lines)
        apparent_bom_ids = Bom  # kits formed by moves not ordered from a kit
        moves_with_apparent_bom_ids = []

        kit_moves = {}
        singles_moves = {}
        amz_loc = self.env['stock.location'].search([('barcode', '=', 'Amazon FBA')])

        # work only on in progress moves
        moves = self.filtered(lambda move: move.state in ['confirmed', 'waiting', 'assigned'])
        moves.filtered(lambda move: move.reserved_quant_ids).do_unreserve()

        pick_moves = moves.filtered(lambda m: m.picking_id.picking_type_id.name == 'Pick')
        if len(pick_moves) > 1:
            no_kit_line_moves = pick_moves.filtered(lambda m: not m.procurement_id.sale_line_id.kit_line_id)
            if len(no_kit_line_moves) > 1:
                for move in no_kit_line_moves:
                    bom_line_ids = BomLine.search([('product_id', '=', move.product_id.id)])
                    if bom_line_ids:
                        if apparent_bom_ids:
                            apparent_bom_ids &= bom_line_ids.mapped('bom_id')
                        else:
                            apparent_bom_ids = bom_line_ids.mapped('bom_id')
                        moves_with_apparent_bom_ids.append(move.id)
                    else:
                        apparent_bom_ids = Bom
                        moves_with_apparent_bom_ids = []
                        break

        for move in moves:
            if move.picking_type_id.name == 'Pick':
                # JAMES: Get which moves are moves from a kit (or possibly multiple kits)
                if move.procurement_id.sale_line_id.kit_line_id:
                    kit_product_tmpl_id = move.procurement_id.sale_line_id.kit_line_id.product_id.product_tmpl_id
                    if kit_product_tmpl_id.id in kit_moves:
                        kit_moves[kit_product_tmpl_id.id]['move_ids'] |= move
                    else:
                        kit_moves[kit_product_tmpl_id.id] = {'move_ids': move, 'product_tmpl_id': kit_product_tmpl_id}
                elif apparent_bom_ids and move.id in moves_with_apparent_bom_ids:
                    if apparent_bom_ids[0].product_tmpl_id.id in kit_moves:
                        kit_moves[apparent_bom_ids[0].product_tmpl_id.id]['move_ids'] |= move
                    else:
                        kit_moves[apparent_bom_ids[0].product_tmpl_id.id] = {'move_ids': move, 'product_tmpl_id': apparent_bom_ids[0].product_tmpl_id}
                # JAMES: For singles, find locations where they are available and then where they are stored with kits
                else:
                    all_locs = Quant.search([('product_id', '=', move.product_id.id),
                                             ('location_id.usage', '=', 'internal'),
                                             ('reservation_id', '=', False),
                                             ('qty', '>', 0)]).mapped('location_id').filtered(lambda r: r.id != amz_loc.id)
                    bom_ids = BomLine.search([('product_id', '=', move.product_id.id)]).mapped('bom_id')
                    boms_map = {}
                    for bom_id in bom_ids:
                        boms_map[bom_id.id] = bom_id.bom_line_ids.mapped('product_id')
                    common_locations = self.env['stock.location']
                    for bom_id in boms_map:
                        component_location_ids = []
                        common_locations_by_bom = self.env['stock.location']
                        for product_id in boms_map[bom_id]:
                            component_location_ids.append(Quant.search([('product_id', '=', product_id.id),
                                                                        ('location_id.usage', '=', 'internal'),
                                                                        ('reservation_id', '=', False),
                                                                        ('qty', '>', 0)]).mapped('location_id'))
                        if component_location_ids:
                            common_locations_by_bom = component_location_ids[0]
                        for c in component_location_ids:
                            common_locations_by_bom &= c
                        common_locations |= common_locations_by_bom
                    all_locs -= common_locations
                    if all_locs:
                        singles_moves[move.id] = all_locs.ids

        # JAMES: For each kit, try to find a common location where all components are present
        for k in kit_moves:
            singles_locations = []
            # init_max_qty = kit_moves[k]['move_ids'][0].product_qty  # moves have same qty cuz they are parts of kit
            init_max_qty = max([r.product_qty for r in kit_moves[k]['move_ids']])  # ^-this was wrong
            kit_quants = []
            loc_qty = []
            for move in kit_moves[k]['move_ids']:
                conds = [('product_id', '=', move.product_id.id),
                         ('location_id.usage', '=', 'internal'),
                         ('reservation_id', '=', False),
                         ('qty', '>=', 1)]
                if move.picking_id.amz_order_type != 'fba':
                    conds.append(('location_id.barcode', '!=', 'Amazon FBA'))
                qnts = Quant.search(conds)
                kit_quants.append((move, qnts, set([r.location_id.id for r in qnts])))
            common_locs_ids = set.intersection(*[r[2] for r in kit_quants])
            prods = [r.product_id.id for r in kit_moves[k]['move_ids']]
            for r in common_locs_ids:
                f = []
                for prod in prods:
                    f.append((prod, sum(r.qty for r in filter(lambda x: x.location_id.id == r, filter(lambda x: x[0].product_id.id == prod, kit_quants)[0][1]))))
                loc_qty.append((r, f, sum([r[1] for r in f])))
            loc_qty.sort(key=lambda tup: tup[2], reverse=True)  # In the top of list will be highest qty locations
            min_qty = 0
            for ind, lq in enumerate(loc_qty):
                min_qty += min([r[1] for r in lq[1]])
                if min_qty >= init_max_qty:
                    loc_qty = loc_qty[0:ind+1]  # cut the tail of list. Top has enough quantity of required products.
                    break
            kit_locs = [r[0] for r in loc_qty]
            if min_qty < init_max_qty:  # Not enough qty in combined location. Need to take some singles.
                for prod in prods:
                    prod_total = 0
                    for lq_row in loc_qty:
                        for lq_row_el in lq_row[1]:
                            if lq_row_el[0] == prod:
                                prod_total += lq_row_el[1]
                    prod_insufficient = init_max_qty - prod_total
                    if prod_insufficient > 0:
                        all_prod_quants = filter(lambda x: x[0].product_id.id == prod, kit_quants)
                        exact_quants = filter(lambda x: x.qty == prod_insufficient, all_prod_quants[0][1])  # Les try to get excact quants
                        if len(exact_quants) > 0:
                            singles_locations.append(exact_quants[0].location_id.id)
                            continue
                        large_quants = filter(lambda x: x.qty > prod_insufficient, all_prod_quants[0][1])  # No exact. Try to get Large quant.
                        if len(large_quants) > 0:
                            singles_locations.append(large_quants[0].location_id.id)
                            continue
                        sorted_all_prod_quants = sorted(all_prod_quants[0][1], key=lambda x: x.qty)  # There is no large quants. Got to collect singles. Worst case.
                        for quant in sorted_all_prod_quants:
                            if quant.location_id.id not in kit_locs and quant.qty > 0:
                                singles_locations.append(quant.location_id.id)
                                prod_insufficient -= quant.qty
                            if prod_insufficient < 1:  # can be even negative value. Still ok cuz we need only location.
                                break
            # JAMES: Just pick the first location for the case that there are multiple kit locations
            # JAMES: to ensure that components are picked from the same location
            # kit_moves[k]['location_ids'] = common_location_ids.ids[:1] if common_location_ids else []
            # kit_moves[k]['location_ids'] = self.get_kit_min_location(kit_quants, common_locs_ids)
            kit_moves[k]['location_ids'] = kit_locs + singles_locations

        for move in moves:
            if move.location_id.usage in ('supplier', 'inventory', 'production'):
                moves_to_assign |= move
                # TDE FIXME: what ?
                # in case the move is returned, we want to try to find quants before forcing the assignment
                if not move.origin_returned_move_id:
                    continue

            # JAMES: If prime, do not reserve quants which are from returns
            if move.picking_id.amz_order_type == 'fbm' and move.picking_type_id.name == 'Pick':
                returned_quants = Quant
                all_quants = Quant.search([
                    ('product_id', '=', move.product_id.id),
                    ('qty', '>', 0),
                    ('location_id.usage', '=', 'internal'),
                    ('reservation_id', '=', False)
                ])
                for q in all_quants:
                    for m in q.history_ids:
                        if m.picking_id and 'RET' in m.picking_id.name:
                            returned_quants |= q
                returns_list[move.id] = returned_quants.ids

            # if the move is proceeded, restrict the choice of quants in the ones moved previously in original move
            ancestors = move.find_move_ancestors()
            if move.product_id.type == 'consu' and not ancestors:
                moves_to_assign |= move
                continue
            else:
                moves_to_do |= move

                # we always search for yet unassigned quants
                main_domain[move.id] = [('reservation_id', '=', False), ('qty', '>', 0)]

                ancestors_list[move.id] = True if ancestors else False
                if move.state == 'waiting' and not ancestors:
                    # if the waiting move hasn't yet any ancestor (PO/MO not confirmed yet), don't find any quant available in stock
                    main_domain[move.id] += [('id', '=', False)]
                elif ancestors:
                    main_domain[move.id] += [('history_ids', 'in', ancestors.ids)]

                # if the move is returned from another, restrict the choice of quants to the ones that follow the returned move
                if move.origin_returned_move_id:
                    main_domain[move.id] += [('history_ids', 'in', move.origin_returned_move_id.id)]

                if move.picking_type_id.name == 'Pick':
                    if move.procurement_id.sale_line_id.kit_line_id:
                        kit_product_tmpl_id = move.procurement_id.sale_line_id.kit_line_id.product_id.product_tmpl_id
                        if kit_product_tmpl_id.id in kit_moves and kit_moves[kit_product_tmpl_id.id]['location_ids'] and not ancestors:
                            main_domain[move.id] += [('location_id', 'in', kit_moves[kit_product_tmpl_id.id]['location_ids'])]
                    elif move.id in moves_with_apparent_bom_ids and apparent_bom_ids and kit_moves[apparent_bom_ids[0].product_tmpl_id.id]['location_ids']:
                        main_domain[move.id] += [('location_id', 'in', kit_moves[apparent_bom_ids[0].product_tmpl_id.id]['location_ids'])]
                    elif move.id in singles_moves and not ancestors and singles_moves[move.id] and move.picking_id.amz_order_type != 'fba':
                        main_domain[move.id] += [('location_id', 'in', singles_moves[move.id])]
                    # elif move.id in singles_moves and not ancestors and move.picking_type_id.name == 'Pick' and singles_moves[move.id] and move.picking_id.amz_order_type == 'fba':
                if not ancestors and move.picking_id.amz_order_type == 'fba':
                    if amz_loc not in [move.location_id, move.location_dest_id]:
                        main_domain[move.id] += [('location_id', '=', amz_loc.id)]
                    else:  # TODO what to do ??
                        pass
                # exclude FBA location
                if move.picking_id.amz_order_type != 'fba':
                    main_domain[move.id] += [('location_id', '!=', amz_loc.id)]

                for link in move.linked_move_operation_ids:
                    operations |= link.operation_id

        # Check all ops and sort them: we want to process first the packages, then operations with lot then the rest
        operations = operations.sorted(key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))
        for ops in operations:
            # TDE FIXME: this code seems to be in action_done, isn't it ?
            # first try to find quants based on specific domains given by linked operations for the case where we want to rereserve according to existing pack operations
            if not (ops.product_id and ops.pack_lot_ids):
                for record in ops.linked_move_operation_ids:
                    move = record.move_id
                    if move.id in main_domain:
                        qty = record.qty
                        domain = main_domain[move.id]
                        if qty:
                            quants = Quant.quants_get_preferred_domain(qty, move, ops=ops, domain=domain, preferred_domain_list=[])
                            Quant.quants_reserve(quants, move, record)
            else:
                lot_qty = {}
                rounding = ops.product_id.uom_id.rounding
                for pack_lot in ops.pack_lot_ids:
                    lot_qty[pack_lot.lot_id.id] = ops.product_uom_id._compute_quantity(pack_lot.qty, ops.product_id.uom_id)
                for record in ops.linked_move_operation_ids:
                    move_qty = record.qty
                    move = record.move_id
                    domain = main_domain[move.id]
                    for lot in lot_qty:
                        if float_compare(lot_qty[lot], 0, precision_rounding=rounding) > 0 and float_compare(move_qty, 0, precision_rounding=rounding) > 0:
                            qty = min(lot_qty[lot], move_qty)
                            quants = Quant.quants_get_preferred_domain(qty, move, ops=ops, lot_id=lot, domain=domain, preferred_domain_list=[])
                            Quant.quants_reserve(quants, move, record)
                            lot_qty[lot] -= qty
                            move_qty -= qty

        # Sort moves to reserve first the ones with ancestors, in case the same product is listed in
        # different stock moves.
        for move in sorted(moves_to_do, key=lambda x: -1 if ancestors_list.get(x.id) else 0):
            # then if the move isn't totally assigned, try to find quants without any specific domain
            if move.state != 'assigned' and not self.env.context.get('reserve_only_ops'):
                qty_already_assigned = move.reserved_availability
                qty = move.product_qty - qty_already_assigned
                preferred_domain_list = [[('id', 'not in', returns_list[move.id])], []] if move.id in returns_list and returns_list[move.id] else []
                quants = Quant.quants_get_preferred_domain(qty, move, domain=main_domain[move.id], preferred_domain_list=preferred_domain_list)
                # Justin [2019-02-06 7:03 PM]
                # OK cool, so you already checked all of the international POs and they werent ever bought overseas?
                # If so, then yes, take the lowest price between PFG and LKQ
                # And use that as the landed cost in the warehouse
                # Then how do we prevent this from happening in the future?
                # Ilyas [7:05 PM]
                # reject all movements without cost
                # Justin [7:06 PM]
                # perfect!!
                good_quants = []
                if quants:
                    for quant, qty in quants:
                        if quant:
                            if quant.cost <= 0:
                                # raise ValidationError('Quants with 0 cost detected! \nProduct: %s ids: %s\n Operation terminated.' % (quant.product_id.name, quants))
                                _log.warning('\n\nQuants with 0 cost detected! \nProduct: %s ids: %s\n' % (quant.product_id.name, quants))
                            else:
                                good_quants.append((quant, qty))
                Quant.quants_reserve(good_quants, move)

        # force assignation of consumable products and incoming from supplier/inventory/production
        # Do not take force_assign as it would create pack operations
        if moves_to_assign:
            moves_to_assign.write({'state': 'assigned'})
        if not no_prepare:
            self.check_recompute_pack_op()

    @api.model
    def get_kit_min_location(self, quants_per_product, locs):
        if len(quants_per_product) < 2 or len(locs) < 2:
            return locs.ids[:1] if locs else []
        qnts = []
        for q in quants_per_product:
            qnts.append(q.filtered(lambda x: x.location_id.id in locs.ids))
        locs_qtys = []
        for product in qnts:
            for loc in locs:
                total = 0
                for q in product:
                    if q.location_id.id == loc.id:
                        total += q.qty
                locs_qtys.append((product, loc, total))
        return [sorted(locs_qtys, key=lambda tup: tup[2])[0][1].id]  # take location where one of products present in minimal qty
