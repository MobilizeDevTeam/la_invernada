from odoo import models, fields, api


class UpdateStockQuant(models.TransientModel):
    _name = 'update.stock.quant'
    _description = "Actualizar Stock Quant"

    product_id = fields.Many2one('product.product', 'Producto')

    picking_id = fields.Many2one('stock.picking')

    product_ids = fields.Many2many('product.product')

    @api.multi
    def update(self):
        lots = self.env['stock.production.lot'].search([('product_id.id', '=',self.product_id.id)])
        for lot in lots:
            if lot.stock_production_lot_serial_ids.filtered(lambda a: not a.consumed):
                quant = self.env['stock.quant'].sudo().search(
                    [('lot_id', '=', lot.id), ('location_id.usage', '=', 'internal'),
                     ('location_id', '=', self.picking_id.location_id.id)])

                if quant:
                    quant.write({
                        'reserved_quantity': sum(lot.stock_production_lot_serial_ids.filtered(lambda
                                                                                                  x: x.reserved_to_stock_picking_id and x.reserved_to_stock_picking_id.state != 'done' and not x.consumed).mapped(
                            'display_weight')),
                        'quantity': sum(lot.stock_production_lot_serial_ids.filtered(
                            lambda x: not x.reserved_to_stock_picking_id and not x.consumed).mapped('display_weight'))
                    })
                else:
                    self.env['stock.quant'].sudo().create({
                        'lot_id': lot.id,
                        'product_id': lot.product_id.id,
                        'reserved_quantity': sum(lot.stock_production_lot_serial_ids.filtered(lambda
                                                                                                  x: x.reserved_to_stock_picking_id and x.reserved_to_stock_picking_id.state != 'done' and not x.consumed).mapped(
                            'display_weight')),
                        'quantity': sum(lot.stock_production_lot_serial_ids.filtered(
                            lambda x: not x.reserved_to_stock_picking_id and not x.consumed).mapped('display_weight')),
                        'location_id': self.picking_id.location_id.id
                    })
