from odoo import fields, models, api
from odoo.addons import decimal_precision as dp
from datetime import datetime
import inspect
import re
from py_linq import Enumerable


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    positioning_state = fields.Selection([
        ('pending', 'Pendiente'),
        ('done', 'Listo')
    ],
        'Estado movimiento de bodega a producción',
        default='pending'
    )

    client_id = fields.Many2one(
        'res.partner',
        related='stock_picking_id.partner_id',
        string='Cliente',
        readonly=True
    )

    destiny_country_id = fields.Many2one(
        'res.country',
        related='stock_picking_id.arrival_port.country_id',
        string='País'
    )

    charging_mode = fields.Selection(
        related='stock_picking_id.charging_mode',
        string='Modo de Carga'
    )

    client_label = fields.Boolean(
        'Etiqueta Cliente',
        related='stock_picking_id.client_label'
    )

    unevenness_percent = fields.Float(
        '% Descalibre',
        digits=dp.get_precision('Product Unit of Measure')
    )

    etd = fields.Date(
        'Fecha Despacho',
        related='stock_picking_id.etd'
    )

    observation = fields.Text('Observación')

    label_durability_id = fields.Many2one(
        'label.durability',
        'Durabilidad Etiqueta'
    )

    pt_balance = fields.Float(
        'Saldo Bodega PT',
        digits=dp.get_precision('Product Unit of Measure'),
        compute='_compute_pt_balance'
    )

    stock_picking_id = fields.Many2one('stock.picking', 'Despacho')

    sale_order_id = fields.Many2one(
        'sale.order',
        related='stock_picking_id.sale_id'
    )

    stock_lots = fields.Many2one("stock.production.lot")

    client_search_id = fields.Many2one(
        'res.partner',
        'Buscar Cliente',
        nullable=True
    )

    show_finished_move_line_ids = fields.One2many(
        'stock.move.line',
        compute='_compute_show_finished_move_line_ids'
    )

    consumed_material_ids = fields.One2many(
        'stock.production.lot.serial',
        related='workorder_ids.potential_serial_planned_ids'
    )

    required_date_moving_to_production = fields.Datetime(
        'Fecha Requerida de Movimiento a Producción',
        default=datetime.utcnow()
    )

    product_search_id = fields.Many2one(
        'product.product',
        'Buscar Producto',
        nullable=True,
    )

    product_lot = fields.Many2one(
        'product.product',
        related="stock_lots.product_id",
        string="Producto del Lote"
    )

    requested_qty = fields.Float(
        'Cantidad Solicitada',
        digits=dp.get_precision('Product Unit of Measure')
    )

    serial_lot_ids = fields.One2many(
        'stock.production.lot.serial',
        related="stock_lots.stock_production_lot_serial_ids"
    )

    potential_lot_ids = fields.One2many(
        'potential.lot',
        'mrp_production_id',
        'Posibles Lotes'
    )

    materials = fields.Many2many('product.product', compute='get_product_bom')

    manufactureable = fields.Many2many('product.product', compute='get_product_route')

    @api.multi
    def _compute_pt_balance(self):
        for item in self:
            item.pt_balance = sum(item.stock_picking_id.packing_list_ids.filtered(
                lambda a: a.production_id != item
            ).mapped('display_weight'))

    @api.model
    def get_product_route(self):
        list = []
        for item in self:
            products = item.env['product.product'].search([])
            for p in products:
                if "Fabricar" in p.route_ids.mapped('name'):
                    list.append(p.id)
            item.manufactureable = item.env['product.product'].search([('id', 'in', list)])

    @api.multi
    def get_product_bom(self):
        for item in self:
            item.update({
                'materials': item.bom_id.bom_line_ids.mapped('product_id')
            })

    @api.multi
    def _compute_show_finished_move_line_ids(self):
        for item in self:
            for move_line in item.finished_move_line_ids:
                existing_move = item.show_finished_move_line_ids.filtered(
                    lambda a: a.lot_id == move_line.lot_id
                )
                if not existing_move:
                    move_line.write({
                        'tmp_qty_done': move_line.qty_done
                    })
                    item.show_finished_move_line_ids += move_line
                else:
                    existing_move.write({
                        'tmp_qty_done': existing_move.tmp_qty_done + move_line.qty_done
                    })

    @api.model
    def get_potential_lot_ids(self):
        domain = [
            ('balance', '>', 0),
            ('product_id.id', 'in', list(self.move_raw_ids.filtered(
                lambda a: not a.product_id.categ_id.reserve_ignore
            ).mapped('product_id.id'))),
        ]
        if self.product_search_id:
            domain += [('product_id.id', '=', self.product_search_id.id)]

        if self.client_search_id:
            client_lot_ids = self.env['quality.analysis'].search([
                ('potential_client_id', '=', self.client_search_id.id),
                ('potential_workcenter_id.id', 'in', list(self.routing_id.operation_ids.mapped('workcenter_id.id')))
            ]).mapped('stock_production_lot_ids.name')

            domain += [('name', 'in', list(client_lot_ids) if client_lot_ids else [])]

        res = self.env['stock.production.lot'].search(domain)

        return [{
            'stock_production_lot_id': lot.id,
            'mrp_production_id': self.id
        } for lot in res]

    @api.multi
    def set_stock_move(self):
        product = self.env['stock.move'].create({'product_id': self.product_id})
        product_qty = self.env['stock.move'].create({'product_qty': self.product_qty})
        self.env.cr.commit()

    @api.multi
    def calculate_done(self):
        for item in self:
            if item.product_id.categ_id.parent_id.name == 'Producto Terminado':
                list_serial_pt = Enumerable(self.workorder_ids[0].summary_out_serial_ids).where(
                    lambda x: x.product_id.id == item.product_id.id).count()
                for move in item.move_raw_ids.filtered(lambda x: not x.needs_lots):
                    move.active_move_line_ids.sudo().unlink()
                    component_ids = Enumerable(item.bom_id.bom_line_ids).where(
                        lambda x: x.product_id.id == move.product_id.id)
                    self.env['stock.move.line'].create({
                        'product_id': move.product_id.id,
                        'production_id': item.id,
                        'qty_done': list_serial_pt * component_ids.first_or_default().product_qty,
                        'location_id': item.location_src_id.id,
                        'product_uom_id': move.product_id.uom_id.id,
                        'location_dest_id': self.env['stock.location'].search([('usage', '=', 'production')],
                                                                              limit=1).id,
                        'move_id': move.id,
                        'state': 'done',
                        'lot_produced_id': item.finished_move_line_ids.filtered(
                            lambda x: x.product_id.id == item.product_id.id).lot_id.id
                    })
                    quant = self.env['stock.quant'].search(
                        [('product_id', '=', move.product_id.id), ('location_id', '=', item.location_src_id.id)])
                    if quant:
                        quant.sudo().write({
                            'quantity': quant.quantity - (list_serial_pt * component_ids.first_or_default().product_qty)
                        })
                    else:
                        test = 0 - (list_serial_pt * component_ids.first_or_default().product_qty)
                        quant = self.env['stock.quant'].sudo().create({
                            'quantity': 0 - (list_serial_pt * component_ids.first_or_default().product_qty),
                            'location_id': item.location_src_id.id,
                            'product_id': move.product_id.id,
                            'in_date': datetime.now()
                        })
                        print(quant)

    @api.multi
    def button_mark_done(self):
        self.calculate_done()
        final_lot_id = self.finished_move_line_ids.filtered(lambda x: x.product_id.id == self.product_id.id)
        if len(final_lot_id.lot_id.stock_production_lot_serial_ids) == 0:
            self.move_raw_ids.write({
                'lot_id': self.finished_move_line_ids.filtered(lambda x: len(x.lot_id.stock_production_lot_serial_ids) > 0)[0].id
            })
        if len(final_lot_id.lot_id.temporary_serial_ids) > 0:
            final_lot_id.lot_id.temporary_serial_ids.unlink()
        for item in self.workorder_ids:
            item.organize_move_line()
        for fin in self.finished_move_line_ids:
            if not fin.lot_id.stock_production_lot_serial_ids:
                fin.write({
                    'state': 'draft',
                })
                fin.unlink()
            else:
                fin.write({
                    'state': 'draft',
                    'qty_done': sum(fin.lot_id.stock_production_lot_serial_ids.mapped('display_weight'))
                })
                fin.lot_id.write({
                    'is_finished': True
                })
                fin.write({
                    'state': 'done'
                })
        res = super(MrpProduction, self).button_mark_done()
        for move in self.move_raw_ids:
            if move.quantity_done == 0 or move.product_uom_qty == 0:
                move.write({
                    'state': 'draft'
                })
                move.unlink()

        return res

    @api.model
    def create(self, values_list):
        res = super(MrpProduction, self).create(values_list)
        res.stock_picking_id.update({
            'has_mrp_production': True
        })
        return res

    def fix_reserved(self, move):
        query = 'DELETE FROM stock_move_line where move_id = {}'.format(move.id)
        cr = self._cr
        cr.execute(query)

    def get_measure(self, measure):
        list_char = []
        for m in measure:
            if m.isdigit() or m == '.':
                list_char.append(m)
        return float(''.join(list_char))
