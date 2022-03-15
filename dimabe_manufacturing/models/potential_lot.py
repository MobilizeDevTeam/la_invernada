from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp


class PotentialLot(models.Model):
    _name = 'potential.lot'
    _description = 'posibles lotes para planificación de producción'

    name = fields.Char('lote', related='stock_production_lot_id.name')

    lot_product_id = fields.Many2one(
        'product.product',
        related='stock_production_lot_id.product_id'
    )

    lot_balance = fields.Float(
        related='stock_production_lot_id.balance',
        digits=dp.get_precision('Product Unit of Measure')
    )

    stock_production_lot_id = fields.Many2one('stock.production.lot', 'lote potencial')

    potential_serial_ids = fields.One2many(
        'stock.production.lot.serial',
        compute='_compute_potential_serial_ids',
    )

    consumed_serial_ids = fields.One2many(
        'stock.production.lot.serial',
        compute='_compute_consumed_serial_ids'
    )

    mrp_production_id = fields.Many2one('mrp.production', 'Producción')

    mrp_production_state = fields.Selection(
        string='estado',
        related='mrp_production_id.state'
    )

    qty_to_reserve = fields.Float(
        'Cantidad Reservada',
        compute='_compute_qty_to_reserve',
        digits=dp.get_precision('Product Unit of Measure')
    )

    is_reserved = fields.Boolean('Reservado')

    all_serial_consumed = fields.Integer('Cantidad de serie sin usar'
                                         , compute='_compute_all_serial_consumed'
                                         )

    producer_id = fields.Many2one('res.partner', related='stock_production_lot_id.producer_id')

    @api.multi
    def _compute_all_serial_consumed(self):
        for item in self:
            item.all_serial_consumed = len(item.stock_production_lot_id.stock_production_lot_serial_ids.filtered(
                lambda a: a.consumed is False and (
                        a.reserved_to_production_id == item.mrp_production_id or not a.reserved_to_production_id)
            ))

    @api.multi
    def _compute_potential_serial_ids(self):
        for item in self:
            item.potential_serial_ids = item.stock_production_lot_id.stock_production_lot_serial_ids.filtered(
                lambda a: a.consumed is False and (
                        a.reserved_to_production_id == item.mrp_production_id or not a.reserved_to_production_id)
            )

    @api.multi
    def _compute_consumed_serial_ids(self):
        for item in self:
            item.consumed_serial_ids = item.stock_production_lot_id.stock_production_lot_serial_ids.filtered(
                lambda a: a.consumed and a.reserved_to_production_id == item.mrp_production_id
            )

    @api.model
    def get_stock_quant(self, location_id=None):
        if self.location_id:
            stock_quant = self.stock_production_lot_id.quant_ids.filtered(
                lambda a: a.location_id.id == location_id)
            return None if not stock_quant else stock_quant
        else:
            return self.stock_production_lot_id.quant_ids.filtered(
                lambda a: a.location_id.name == 'Stock'
            )

    @api.model
    def get_production_quant(self):
        return self.stock_production_lot_id.quant_ids.filtered(
            lambda a: a.location_id.name == 'Production'
        )

    @api.multi
    def _compute_qty_to_reserve(self):
        for item in self:
            item.qty_to_reserve = sum(
                item.stock_production_lot_id.stock_production_lot_serial_ids.filtered(
                    lambda a: a.reserved_to_production_id == item.mrp_production_id
                ).mapped('display_weight')
            )

    @api.multi
    def reserve_stock_lot(self):
        for item in self:
            serial_to_reserve = item.potential_serial_ids.filtered(lambda a: not a.reserved_to_production_id and not
            a.reserved_to_stock_picking_id)
            if serial_to_reserve:

                serial_to_reserve.with_context(mrp_production_id=item.mrp_production_id.id,
                                               from_lot=True).reserve_serial()
                stock_quant = item.stock_production_lot_id.get_stock_quant()
                stock_quant.sudo().update({
                    'reserved_quantity': stock_quant.total_reserved
                })
                for stock in item.mrp_production_id.move_raw_ids.filtered(
                        lambda a: a.product_id == item.stock_production_lot_id.product_id
                ):
                    item.add_move_line(stock, stock_quant)
        item.is_reserved = True

    @api.model
    def add_move_line(self, stock_move, stock_quant):
        virtual_location_production_id = self.env['stock.location'].search([
            ('usage', '=', 'production'),
            ('location_id.name', 'like', 'Virtual Locations')
        ])
        # data = stock_move.mapped('active_move_line_ids')
        # for d in data:
        #     if d.lot_id.name == self.stock_production_lot_id.name:
        #         raise UserError("Error")
        stock_move.sudo().update({
            'active_move_line_ids': [
                (0, 0, {
                    'product_id': self.stock_production_lot_id.product_id.id,
                    'lot_id': self.stock_production_lot_id.id,
                    'product_uom_qty': self.qty_to_reserve + self.lot_balance,
                    'product_uom_id': stock_move.product_uom.id,
                    'location_id': stock_quant.location_id.id,
                    'location_dest_id': virtual_location_production_id.id
                })
            ]
        })

    @api.multi
    def confirm_reserve(self):

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.multi
    def unreserved_stock(self):
        for item in self:
            if 'from_lot' in self.env.context:
                from_lot = self.env.context['from_lot']
                if from_lot:
                    stock_move = item.mrp_production_id.move_raw_ids.filtered(
                        lambda a: a.product_id == item.stock_production_lot_id.product_id
                    )

                    move_line = stock_move.active_move_line_ids.filtered(
                        lambda
                            a: a.lot_id.id == item.stock_production_lot_id.id and a.product_qty == item.qty_to_reserve
                               and a.qty_done == 0
                    )
                    stock_quant = item.stock_production_lot_id.get_stock_quant()

                    for serial in item.stock_production_lot_id.stock_production_lot_serial_ids:
                        serial.update({
                            'reserved_to_production_id': None
                        })

                    stock_quant.sudo().update({
                        'reserved_quantity': 0
                    })

                    if move_line:
                        move_line[0].write({'move_id': None, 'product_uom_qty': 0})
