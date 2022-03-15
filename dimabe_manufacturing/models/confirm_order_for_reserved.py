from odoo import models, fields, api
from datetime import date


class ConfirmOrderForReserved(models.TransientModel):
    _name = 'confirm.order.reserved'
    _description = "Seleccionar Orden a reservar"

    sale_ids = fields.Many2many('sale.order')

    sale_id = fields.Many2one('sale.order', 'Order')

    picking_id = fields.Many2one('stock.picking', 'Despacho')

    picking_principal_id = fields.Many2one('stock.picking',string="Despachos")

    lot_id = fields.Many2one('stock.production.lot', 'Lote')

    custom_dispatch_line_ids = fields.Many2many('custom.dispatch.line')

    picking_ids = fields.Many2many('stock.picking', compute='compute_picking_ids')

    @api.one
    def reserved(self, no_reserved=True):
        if self.lot_id.pallet_ids.filtered(lambda a: a.add_picking):
            self.lot_id.add_selection_pallet(self.picking_principal_id.id, self.picking_principal_id.location_id.id)
        if self.lot_id.stock_production_lot_serial_ids.filtered(lambda a: a.to_add):
            self.lot_id.add_selection_serial(self.picking_principal_id.id, self.picking_principal_id.location_id.id)
        line = self.picking_principal_id.move_line_ids_without_package.filtered(
            lambda a: a.lot_id.id == self.id and a.product_id.id == self.lot_id.product_id.id)
        if line:
            line.write({
                'product_uom_qty': self.lot_id.get_reserved_quantity_by_picking(self.picking_principal_id.id)
            })
        else:
            line_create = self.env['stock.move.line'].create({
                'move_id': self.picking_id.move_ids_without_package.filtered(
                    lambda m: m.product_id.id == self.lot_id.product_id.id).id,
                'picking_id': self.picking_id.id,
                'product_id': self.lot_id.product_id.id,
                'product_uom_id': self.lot_id.product_id.uom_id.id,
                'product_uom_qty': self.lot_id.get_reserved_quantity_by_picking(self.picking_principal_id.id),
                'location_id': self.picking_principal_id.location_id.id,
                'location_dest_id': self.picking_principal_id.partner_id.property_stock_customer.id,
                'date': date.today(),
                'lot_id': self.lot_id.id
            })
            self.picking_principal_id.dispatch_line_ids.filtered(lambda
                                                                     a: a.sale_id.id == self.sale_id.id and a.dispatch_id.id == self.picking_id.id).write(
                {
                    'real_dispatch_qty': self.lot_id.get_reserved_quantity_by_picking(self.picking_principal_id.id),
                    'move_line_ids': [(4, line_create.id)]
                })

        self.lot_id.clean_add_pallet()
        self.lot_id.clean_add_serial()
        self.lot_id.update_stock_quant(self.picking_principal_id.location_id.id)

    @api.one
    def cancel(self):
        raise models.ValidationError('Prueba Cancelar')

    @api.multi
    def compute_picking_ids(self):
        for item in self:
            item.picking_ids = self.custom_dispatch_line_ids.mapped('dispatch_id')
