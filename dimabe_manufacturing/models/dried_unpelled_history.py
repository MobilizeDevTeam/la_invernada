from odoo import fields, models, api
from odoo.addons import decimal_precision as dp
import datetime
from ..helpers import date_helper

class DriedUnpelledHistory(models.Model):
    _name = 'dried.unpelled.history'
    _description = 'Historial de lotes terminados'

    _order = 'create_date desc'

    name = fields.Char(
        'Nombre',
        compute='_compute_name'
    )

    oven_use_ids = fields.One2many(
        'oven.use',
        'history_id',
        'Hornos',
        readonly=True
    )

    dried_oven_ids = fields.One2many(
        'dried.oven',
        compute='_compute_dried_oven_ids',
        string='Hornos'
    )

    unpelled_dried_id = fields.Many2one(
        'unpelled.dried',
        'Proceso de Secado',
        readonly=True,
        required=True,
    )

    producer_id = fields.Many2one(
        'res.partner',
        'Productor',
        domain=[('supplier', '=', True)],
        readonly=True
    )

    in_product_id = fields.Many2one(
        'product.product',
        'Producto a Ingresar',
        readonly=True
    )

    in_product_variety = fields.Char(
        'Variedad',
        compute='_compute_in_product_variety'
    )

    out_product_id = fields.Many2one(
        'product.product',
        'Producto de Salida',
        readonly=True
    )

    out_lot_id = fields.Many2one(
        'stock.production.lot',
        'Lote de Salida',
        readonly=True
    )

    in_lot_ids = fields.One2many(
        'stock.production.lot',
        string='Lotes de Entrada',
        compute='_compute_in_lot_ids'
    )

    out_serial_ids = fields.One2many(
        'stock.production.lot.serial',
        compute='_compute_out_serial_ids',
        inverse='_inverse_out_serial_ids',
        string='Series de Salida'
    )

    out_serial_count = fields.Integer(
        'Cantidad Envases',
        compute='_compute_out_serial_count'
    )

    out_serial_sum = fields.Float(
        'Total de Series',
        compute='_compute_out_serial_sum',
        digits=dp.get_precision('Product Unit of Measure')
    )

    total_in_weight = fields.Float(
        'Total Ingresado',
        readonly=True,
        digits=dp.get_precision('Product Unit of Measure')
    )

    total_out_weight = fields.Float(
        'Total Secado',
        readonly=True,
        digits=dp.get_precision('Product Unit of Measure')
    )

    performance = fields.Float(
        'Rendimiento',
        compute='_compute_performance',
        digits=dp.get_precision('Product Unit of Measure'),
        store=True
    )

    origin_location_id = fields.Many2one(
        'stock.location',
        'Origen del Movimiento',
        readonly=True
    )

    dest_location_id = fields.Many2one(
        'stock.location',
        'Destino de Procesados',
        readonly=True
    )

    lot_guide_numbers = fields.Char(
        string='N° Guías',
        compute='_compute_lot_guide_numbers'
    )

    picking_type_id = fields.Many2one(
        'stock.picking.type',
        compute='_compute_picking_type_id',
        string='Bodega'
    )

    init_date = fields.Datetime(
        'Inicio Secado',
        compute='_compute_oven_use_data'
    )

    finish_date = fields.Datetime(
        'Término Secado',
        compute='_compute_oven_use_data'
    )

    active_time = fields.Char(
        'Cantidad hrs',
        compute='_compute_oven_use_data'
    )

    canning_id = fields.Many2one(
        'product.product',
        'Envase',
        readonly=True
    )

    can_edit = fields.Boolean(
        'Puede Editar',
        compute='_compute_can_edit'
    )

    is_old_version = fields.Boolean(
        'Modo Antiguo (2020-2021)',
        default=True
    )

    can_adjust = fields.Boolean(
        'Se puede adjustar la diferencia?',
        compute='compute_can_adjust'
    )


    @api.multi
    def compute_can_adjust(self):
        for item in self:
            item.can_adjust = item.out_serial_sum != item.total_out_weight

    @api.multi
    def _compute_out_serial_sum(self):
        for item in self:
            item.out_serial_sum = sum(item.out_serial_ids.mapped('display_weight'))

    @api.multi
    def _compute_can_edit(self):
        for item in self:
            item.can_edit = self.env.user.has_group('base.group_system')

    @api.multi
    def _compute_out_serial_ids(self):
        for item in self:
            item.out_serial_ids = item.out_lot_id.stock_production_lot_serial_ids

    @api.multi
    def _inverse_out_serial_ids(self):
        for item in self:
            item.out_lot_id.stock_production_lot_serial_ids = item.out_serial_ids

    @api.multi
    def _compute_oven_use_data(self):
        for item in self:
            if item.is_old_version:
                for oven_use in item.oven_use_ids:
                    if (item.init_date and item.init_date > oven_use.init_date) or not item.init_date:
                        item.init_date = oven_use.init_date
                        item.finish_date = oven_use.finish_date
                        item.active_time = oven_use.active_time
            else:
                total_active_seconds = round(
                    sum(oven.active_seconds for oven in item.oven_use_ids) / len(item.oven_use_ids))
                item.active_time = date_helper.int_to_time(total_active_seconds)
                item.init_date = item.oven_use_ids[0].init_date
                item.finish_date = item.oven_use_ids[0].finish_date

    @api.multi
    def _compute_dried_oven_ids(self):
        for item in self:
            print()
            item.dried_oven_ids = item.oven_use_ids.filtered(lambda x: x.state == 'done').mapped('dried_oven_id')

    @api.multi
    def _compute_picking_type_id(self):
        for item in self:
            if len(item.in_lot_ids.mapped('picking_type_id')) > 0:
                item.picking_type_id = item.in_lot_ids.mapped('picking_type_id')[0]

    @api.multi
    def _compute_in_product_variety(self):
        for item in self:
            item.in_product_variety = item.in_product_id.get_variety()

    @api.multi
    def _compute_lot_guide_numbers(self):
        for item in self:
            tmp = ''
            for guide_number in item.in_lot_ids.mapped('reception_guide_number'):
                tmp += '{} '.format(guide_number)
                item.lot_guide_numbers = tmp

    @api.multi
    def _compute_in_lot_ids(self):
        for item in self:
            for guide in item.oven_use_ids.mapped('used_lot_id'):
                item.in_lot_ids = item.oven_use_ids.mapped('used_lot_id')

    @api.multi
    def _compute_out_serial_count(self):
        for item in self:
            item.out_serial_count = len(item.out_serial_ids)

    @api.multi
    def _compute_name(self):
        for item in self:
            item.name = f'{item.out_lot_id.name} {item.out_product_id.display_name}'

    @api.multi
    @api.depends('total_in_weight', 'total_out_weight')
    def _compute_performance(self):
        for item in self:
            if item.total_in_weight > 0 and item.total_out_weight > 0:
                item.performance = (item.total_out_weight / item.total_in_weight) * 100

    @api.model
    def create(self, values_list):
        values_list['is_old_version'] = False
        res = super(DriedUnpelledHistory, self).create(values_list)
        if 'unpelled_dried_id' in values_list:
            unpelled_dried_id = self.env['unpelled.dried'].search([('id', '=', values_list['unpelled_dried_id'])])

            if unpelled_dried_id:
                res.producer_id = unpelled_dried_id.producer_id.id
                res.in_product_id = unpelled_dried_id.product_in_id.id
                res.out_product_id = unpelled_dried_id.out_product_id.id
                res.out_lot_id = unpelled_dried_id.out_lot_id
                res.out_lot_id.verify_without_lot()
                res.out_lot_id.update_kg(res.out_lot_id.id)
                res.oven_use_ids = unpelled_dried_id.oven_use_ids.filtered(
                    lambda a: a.ready_to_close
                )
                res.total_out_weight = unpelled_dried_id.total_out_weight
                res.origin_location_id = unpelled_dried_id.origin_location_id.id
                res.dest_location_id = unpelled_dried_id.dest_location_id.id
                res.canning_id = unpelled_dried_id.canning_id
        return res

    @api.multi
    def adjust_stock(self):
        for item in self:
            if item.total_in_weight == 0:
                item.write({
                    'total_in_weight': sum(item.oven_use_ids.filtered(
                        lambda a: a.state == 'done'
                    ).mapped('used_lot_id').mapped('stock_production_lot_serial_ids').mapped('display_weight'))
                })
            if item.out_serial_ids.filtered(
                    lambda a: a.consumed
            ):
                raise models.ValidationError('este proceso no se puede realizar porque ya existen series consumidas')

            stock_move_line = self.env['stock.move.line'].search([
                ('lot_id', '=', item.out_lot_id.id)
            ])
            item.total_out_weight = item.out_serial_sum
            item.out_lot_id.verify_without_lot()
            item.out_lot_id.update_kg(item.out_lot_id.id)

            if not stock_move_line:
                raise models.ValidationError('no se encontró el registro de stock asociado a este proceso')
            stock_move_line.write({
                'qty_done': item.out_serial_sum
            })
