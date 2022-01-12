from odoo import models, api, fields, _
import base64
from odoo.addons import decimal_precision as dp
import datetime
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
import datetime


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    has_mrp_production = fields.Boolean('tiene orden de producción')

    # ya no se ocupa
    # shipping_id = fields.Many2one(
    #    'custom.shipment',
    #    'Embarque'
    # )
    variety = fields.Many2many(related="product_id.attribute_value_ids")

    country_id = fields.Char(related='partner_id.country_id.name')

    product_id = fields.Many2one(related="move_ids_without_package.product_id")

    quantity_requested = fields.Float(
        related='move_ids_without_package.product_uom_qty',
        digits=dp.get_precision('Product Unit of Measure')
    )

    packing_list_ids = fields.One2many(
        'stock.production.lot.serial',
        'reserved_to_stock_picking_id'
    )

    product_search_id = fields.Many2one(
        'product.product',
        string='Buscar Producto',
    )

    potential_lot_serial_ids = fields.One2many(
        'stock.production.lot.serial',
        compute='_compute_potential_lot_serial_ids',
        string='Stock Disponibles',
    )

    potential_lot_ids = fields.One2many(
        'stock.production.lot',
        compute='_compute_potential_lot',
        string='Lotes Disponibles'
    )

    assigned_pallet_ids = fields.One2many(
        'manufacturing.pallet',
        'reserved_to_stock_picking_id'
    )

    have_series = fields.Boolean('Tiene Serie', default=True, compute='_compute_potential_lot_serial_ids')

    packing_list_lot_ids = fields.One2many(
        'stock.production.lot',
        compute='_compute_packing_list_lot_ids'
    )

    sale_order_id = fields.Many2one('sale.order', 'Pedido',
                                    copy=False)

    sale_orders_id = fields.Many2one('sale.order', 'Pedidos', domain=[('state', '=', 'sale')],
                                     copy=False)

    dispatch_line_ids = fields.One2many('custom.dispatch.line', 'dispatch_real_id', copy=False)

    name_orders = fields.Char('Pedidos', compute='get_name_orders')

    dispatch_id = fields.Many2one('stock.picking', 'Despachos', domain=[('state', '!=', 'done')],
                                  copy=False)

    real_net_weigth = fields.Float('Kilos Netos Reales', compute='compute_net_weigth_real')

    packing_list_file = fields.Binary('Packing List')

    is_multiple_dispatch = fields.Boolean('Es Despacho Multiple?', copy=False)

    picking_real_id = fields.Many2one('stock.picking', 'Despacho Real', copy=False)

    picking_principal_id = fields.Many2one('stock.picking', 'Pedido Principal', copy=False)

    is_child_dispatch = fields.Boolean('Es despacho hijo', copy=False)

    @api.onchange('is_multiple_dispatch')
    def set_multiple_dispatch(self):
        if self.is_multiple_dispatch and self.move_ids_without_package:
            # Se busca objecto a causa de que self.id entrega otro tipo de campo (NewId)
            picking = self.env['stock.picking'].search([('name', '=', self.name)])
            self.env['custom.dispatch.line'].create({
                'dispatch_real_id': picking.id,
                'dispatch_id': picking.id,
                'product_id': self.move_ids_without_package.mapped('product_id').id if len(
                    self.move_ids_without_package) == 1 else self.move_ids_without_package[0].mapped('product_id').id,
                'required_sale_qty': self.move_ids_without_package.product_uom_qty if len(
                    self.move_ids_without_package) == 1 else self.move_ids_without_package[0].product_uom_qty,
                'sale_id': self.sale_id.id
            })

    @api.multi
    def compute_net_weigth_real(self):
        for item in self:
            item.real_net_weigth = sum(item.packing_list_ids.mapped('display_weight'))

    @api.multi
    def get_name_orders(self):
        for item in self:
            item.name_orders = ", ".join(item.dispatch_line_ids.mapped('sale_id').mapped('name'))

    @api.multi
    def update_stock_quant(self):
        view = self.env.ref('dimabe_manufacturing.update_quant_view')
        wiz = self.env['update.stock.quant'].create({
            'product_ids': [(4, p.id) for p in self.move_line_ids_without_package.mapped('product_id')],
            'picking_id': self.id
        })
        return {
            'name': 'Actualizar Lote',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'update.stock.quant',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': wiz.id,
            'context': self.env.context
        }

    @api.multi
    def test(self):
        raise models.ValidationError(self.is_satelite_reception)

    @api.multi
    def add_orders_to_dispatch(self):
        if self.is_multiple_dispatch:
            if not self.sale_orders_id:
                raise models.ValidationError('No se selecciono ningun numero de pedido')
            if not self.dispatch_id:
                raise models.ValidationError('No se selecciono ningun despacho')
            if self.dispatch_id in self.dispatch_line_ids.mapped('dispatch_id'):
                raise models.ValidationError('El despacho {} ya se encuentra agregado'.format(self.dispatch_id.id))
            for product in self.dispatch_id.move_ids_without_package:
                self.env['custom.dispatch.line'].create({
                    'dispatch_real_id': self.id,
                    'dispatch_id': self.dispatch_id.id,
                    'sale_id': self.sale_orders_id.id,
                    'product_id': product.product_id.id,
                    'required_sale_qty': product.product_uom_qty,
                })
                # No existe producto
                if not self.move_ids_without_package.filtered(lambda p: p.product_id.id == product.product_id.id):
                    self.env['stock.move'].create({
                        'product_id': product.product_id.id,
                        'picking_id': self.id,
                        'product_uom': product.product_id.uom_id.id,
                        'product_uom_qty': product.product_uom_qty,
                        'date': datetime.date.today(),
                        'date_expected': self.scheduled_date,
                        'location_dest_id': self.partner_id.property_stock_customer.id,
                        'location_id': self.location_id.id,
                        'name': product.product_id.name,
                        'procure_method': 'make_to_stock',
                    })
                else:
                    move = self.move_ids_without_package.filtered(lambda p: p.product_id.id == product.product_id.id)
                    move.write({
                        'product_uom_qty': move.product_uom_qty + product.product_uom_qty
                    })

    @api.onchange('picking_type_id')
    def on_change_picking_type(self):
        for item in self:
            if item.picking_type_id.code == 'incoming':
                res = {
                    'domain': {
                        'partner_id': [('is_company', '=', True), ('supplier', '=', True), ('name', '!=', ''),
                                       ('type', '=', 'contact'), ('parent_id', '=', None)],
                    }
                }
            else:
                res = {
                    'domain': {
                        'partner_id': [('is_company', '=', True), ('customer', '=', True), ('name', '!=', ''),
                                       ('type', '=', 'contact'), ('parent_id', '=', None)],
                    }
                }
        return res

    @api.multi
    def remove_reserved_serial(self):
        lots = self.packing_list_ids.filtered(lambda a: a.to_delete).mapped('stock_production_lot_id')
        self.packing_list_ids.filtered(lambda a: a.to_delete and a.reserved_to_stock_picking_id.id == self.id).write({
            'reserved_to_stock_picking_id': None,
            'to_delete': False
        })
        self.update_move(lots)

    @api.multi
    def remove_reserved_pallet(self):
        lots = self.assigned_pallet_ids.filtered(lambda a: a.remove_picking).mapped('lot_id')
        pallets = self.assigned_pallet_ids.filtered(
            lambda a: a.remove_picking and a.reserved_to_stock_picking_id.id == self.id)
        for pallet in pallets:
            pallet.lot_serial_ids.filtered(lambda a: a.reserved_to_stock_picking_id.id == self.id).write({
                'reserved_to_stock_picking_id': None
            })
            pallet.write({
                'reserved_to_stock_picking_id': None,
                'remove_picking': False
            })
        self.update_move(lots)

    def update_move(self, lots):
        for lot in lots:
            move = self.move_line_ids_without_package.filtered(lambda a: a.lot_id.id == lot.id)
            if move:
                if lot.get_reserved_quantity_by_picking(self.id) > 0:
                    move.write({
                        'product_uom_qty': lot.get_reserved_quantity_by_picking(self.id)
                    })
                else:
                    move.unlink()
                self.dispatch_line_ids.filtered(lambda a: a.product_id.id == lot.product_id.id).mapped(
                    'move_line_ids').filtered(lambda a: a.lot_id.id == lot.id).write({
                    'product_uom_qty': lot.get_reserved_quantity_by_picking(self.id)
                })
                self.dispatch_line_ids.filtered(
                    lambda a: a.product_id.id == lot.product_id.id and lot in a.move_line_ids.mapped('lot_id')).write({
                    'real_dispatch_qty': sum(
                        self.packing_list_ids.filtered(lambda a: a.stock_production_lot_id == lot).mapped('display_weight'))
                })

    @api.multi
    def _compute_packing_list_lot_ids(self):
        for item in self:
            if item.packing_list_ids and item.picking_type_code == 'outgoing':
                item.packing_list_lot_ids = item.packing_list_ids.mapped('stock_production_lot_id')
            else:
                item.packing_list_lot_ids = []

    @api.onchange('sale_order_id')
    def on_change_production_id(self):
        for item in self:
            if item.picking_type_code == 'outgoing':
                item.potential_lot_ids = self.env['stock.production.lot'].search(
                    [('sale_order_id', '=', item.sale_order_id.id),
                     ('product_id', '=', item.move_ids_without_package.mapped('product_id.id'))])

    @api.multi
    def _compute_potential_lot_serial_ids(self):
        for item in self:
            if item.picking_type_code == 'outgoing':
                domain = [
                    ('stock_product_id', 'in',
                     item.move_ids_without_package.mapped('product_id.id')),
                    ('consumed', '=', False),
                    ('reserved_to_stock_picking_id', '=', False)
                ]
                for id_pr in item.move_ids_without_package.mapped('product_id.id'):
                    data = self.env['stock.production.lot.serial'].search([('stock_product_id', '=', id_pr)])
                    if not data:
                        item.have_series = False

                item.potential_lot_serial_ids = self.env['stock.production.lot.serial'].search(
                    domain)

    @api.multi
    def action_cancel(self):
        for item in self:
            lot = self.env['stock.production.lot'].search([('name', '=', item.name)])
            if lot:
                lot.stock_production_lot_serial_ids.sudo().unlink()
                lot.sudo().unlink()
            return super(StockPicking, self).action_cancel()

    @api.multi
    def calculate_last_serial(self):
        if self.picking_type_code == 'incoming':
            if len(canning) == 1:
                if self.production_net_weight == self.net_weight:
                    self.production_net_weight = self.net_weight - self.quality_weight

                self.env['stock.production.lot.serial'].search([('stock_production_lot_id', '=', self.name)]).write({
                    'real_weight': self.avg_unitary_weight
                })
                diff = self.production_net_weight - (canning.product_uom_qty * self.avg_unitary_weight)
                self.env['stock.production.lot.serial'].search([('stock_production_lot_id', '=', self.name)])[-1].write(
                    {
                        'real_weight': self.avg_unitary_weight + diff
                    })

    @api.multi
    def _compute_potential_lot(self):
        for item in self:
            if item.picking_type_code == 'outgoing':
                domain = [
                    ('product_id', 'in', item.move_ids_without_package.mapped('product_id.id')),
                    ('available_total_serial', '>', 0)
                ]
                lot = self.env['stock.production.lot'].search(domain)
                item.potential_lot_ids = lot

    @api.multi
    def return_action(self):
        context = {
            'default_product_id': self.product_id.id,
            'default_product_uom_qty': self.quantity_requested,
            'default_origin': self.name,
            'default_stock_picking_id': self.id,
            'default_client_search_id': self.partner_id.id,
            'default_requested_qty': self.quantity_requested
        }
        return {
            "type": "ir.actions.act_window",
            "res_model": "mrp.production",
            "view_type": "form",
            "view_mode": "form",
            "views": [(False, "form")],
            "view_id ref='mrp.mrp_production_form_view'": '',
            "target": "current",
            "context": context
        }

    @api.multi
    def action_confirm(self):
        res = super(StockPicking, self).action_confirm()
        for stock_picking in self:
            mp_move = stock_picking.get_mp_move()
            if stock_picking.picking_type_id.require_dried:
                for move_line in mp_move.move_line_ids:
                    move_line.lot_id.unpelled_state = 'draft'
            mp_move.move_line_ids.mapped('lot_id').write({
                'stock_picking_id': stock_picking.id
            })
            for lot_id in mp_move.move_line_ids.mapped('lot_id'):
                if lot_id.stock_production_lot_serial_ids:
                    lot_id.stock_production_lot_serial_ids.write({
                        'producer_id': lot_id.stock_picking_id.partner_id.id
                    })
        return res

    def validate_barcode(self, barcode):
        custom_serial = self.packing_list_ids.filtered(
            lambda a: a.serial_number == barcode
        )
        if not custom_serial:
            raise models.ValidationError('el código {} no corresponde a este despacho'.format(barcode))
        return custom_serial

    def on_barcode_scanned(self, barcode):
        for item in self:
            custom_serial = item.validate_barcode(barcode)
            if custom_serial.consumed:
                raise models.ValidationError('el código {} ya fue consumido'.format(barcode))

            stock_move_line = self.move_line_ids_without_package.filtered(
                lambda a: a.product_id == custom_serial.stock_production_lot_id.product_id and
                          a.lot_id == custom_serial.stock_production_lot_id and
                          a.product_uom_qty == custom_serial.display_weight and
                          a.qty_done == 0
            )

            if len(stock_move_line) > 1:
                stock_move_line[0].write({
                    'qty_done': custom_serial.display_weight
                })
            else:
                stock_move_line.write({
                    'qty_done': custom_serial.display_weight
                })

            custom_serial.sudo().write({
                'consumed': True
            })
