from odoo import models, fields, api
import base64
from datetime import date
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.addons import decimal_precision as dp
import json
from odoo.tools import date_utils


class ConfirmPrincipalOrder(models.TransientModel):
    _name = 'confirm.principal.order'
    _description = "Seleccionar Pedido Principal"

    sale_ids = fields.Many2many('sale.order',string="Pedidos")

    sale_id = fields.Many2one('sale.order',string="Pedido")

    picking_id = fields.Many2one('stock.picking',string="Transferencia")

    custom_dispatch_line_ids = fields.Many2many('custom.dispatch.line')

    @api.one
    def select(self):
        self.picking_id.packing_list_ids.write({
            'consumed': True
        })
        self.process_data()
        for item in self.custom_dispatch_line_ids:
            item.dispatch_id.write({
                'consignee_id': self.picking_id.consignee_id.id,
                'notify_ids': [(4, n.id) for n in self.picking_id.notify_ids],
                'picking_real_id': self.picking_id.id,
                'picking_principal_id': self.custom_dispatch_line_ids.filtered(
                    lambda a: a.sale_id.id == self.sale_id.id).dispatch_id.id
            })

    @api.one
    def cancel(self):
        self.picking_id.packing_list_ids.write({
            'consumed': True
        })

        self.process_data()
        for item in self.picking_id.dispatch_line_ids:
            item.dispatch_id.write({
                'consignee_id': self.picking_id.consignee_id.id,
                'notify_ids': [(4, n.id) for n in self.picking_id.notify_ids],
                'picking_principal_id': self.picking_id.id,
                'is_child_dispatch': True if item.dispatch_id.id != self.picking_id.id else False
            })

    def process_data(self):
        for item in self.custom_dispatch_line_ids:
            item.dispatch_id.clean_reserved()
            for line in item.move_line_ids:
                self.update_stock_quant(line.product_id.id,line.location_id.id)
                if item.dispatch_id.id != self.picking_id.id:
                    line_create = self.env['stock.move.line'].create({
                        'move_id': item.dispatch_id.move_ids_without_package.filtered(
                            lambda a: a.product_id.id == line.product_id.id).id,
                        'product_id': line.product_id.id,
                        'product_uom_qty': item.real_dispatch_qty,
                        'product_uom_id': line.product_id.uom_id.id,
                        'lot_id': line.lot_id.id,
                        'location_id': line.location_id.id,
                        'location_dest_id': line.location_dest_id.id,
                        'date': line.date,
                        'state': 'done',
                        'picking_id': item.dispatch_id.id,
                    })
            if item.real_dispatch_qty > 0:
                precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
                no_quantities_done = all(
                    float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in
                    item.dispatch_id.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel')))
                if no_quantities_done:
                    self.inmediate_transfer(item.dispatch_id)
                if self.check_backorder(item.dispatch_id):

                    self.process_backorder(item.dispatch_id)
                else:
                    item.dispatch_id.action_done()

    @api.multi
    def inmediate_transfer(self, picking):
        pick_to_backorder = self.env['stock.picking']
        pick_to_do = self.env['stock.picking']
        if picking.state == 'draft':
            picking.action_confirm()
            if picking.state != 'assigned':
                picking.action_assign()
                if picking.state != 'assigned':
                    raise models.ValidationError("Prueba 123")
                    raise models.UserError((
                        "Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
        for move in picking.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
            for move_line in move.move_line_ids:
                move_line.qty_done = move_line.product_uom_qty
        if self.check_backorder(picking):
            pick_to_backorder |= picking
        pick_to_do |= picking

    @api.multi
    def check_backorder(self, picking):
        quantity_todo = {}
        quantity_done = {}
        for move in picking.mapped('move_lines'):
            quantity_todo.setdefault(move.product_id.id, 0)
            quantity_done.setdefault(move.product_id.id, 0)
            quantity_todo[move.product_id.id] += move.product_uom_qty
            quantity_done[move.product_id.id] += move.quantity_done
        for ops in picking.mapped('move_line_ids').filtered(
                lambda x: x.package_id and not x.product_id and not x.move_id):
            for quant in ops.package_id.quant_ids:
                quantity_done.setdefault(quant.product_id.id, 0)
                quantity_done[quant.product_id.id] += quant.qty
        for pack in picking.mapped('move_line_ids').filtered(lambda x: x.product_id and not x.move_id):
            quantity_done.setdefault(pack.product_id.id, 0)
            quantity_done[pack.product_id.id] += pack.product_uom_id._compute_quantity(pack.qty_done,
                                                                                       pack.product_id.uom_id)
        return any(quantity_done[x] < quantity_todo.get(x, 0) for x in quantity_done)

    @api.multi
    def process_backorder(self, picking):
        for pick_id in picking:
            moves_to_log = {}
            for move in pick_id.move_lines:
                if float_compare(move.product_uom_qty, move.quantity_done,
                                 precision_rounding=move.product_uom.rounding) > 0:
                    moves_to_log[move] = (move.quantity_done, move.product_uom_qty)
            pick_id._log_less_quantities_than_expected(moves_to_log)
        picking.action_done()

    def update_stock_quant(self,product_id,location_id):
        lots = self.env['stock.production.lot'].search([('product_id.id', '=', product_id)])
        for lot in lots:
            if lot.stock_production_lot_serial_ids.filtered(lambda a: not a.consumed):
                quant = self.env['stock.quant'].sudo().search(
                    [('lot_id', '=', lot.id), ('location_id.usage', '=', 'internal')])
                if quant:
                    quant.write({'reserved_quantity': sum(lot.stock_production_lot_serial_ids.filtered(lambda
                                                                                                           x: x.reserved_to_stock_picking_id and x.reserved_to_stock_picking_id.state != 'done' and not x.consumed).mapped(
                        'display_weight')),
                                 'quantity': sum(lot.stock_production_lot_serial_ids.filtered(lambda
                                                                                                  x: x.reserved_to_stock_picking_id and x.reserved_to_stock_picking_id.state != 'done' and not x.consumed).mapped(
                                     'display_weight'))})
                else:
                    self.env['stock.quant'].sudo().create({
                        'lot_id': lot.id,
                        'product_id': lot.product_id.id,
                        'reserved_quantity': sum(lot.stock_production_lot_serial_ids.filtered(lambda
                                                                                                  x: x.reserved_to_stock_picking_id and x.reserved_to_stock_picking_id.state != 'done' and not x.consumed).mapped(
                            'display_weight')),
                        'quantity': sum(lot.stock_production_lot_serial_ids.filtered(
                            lambda x: not x.reserved_to_stock_picking_id and not x.consumed).mapped('display_weight')),
                        'location_id': location_id
                    })
