from odoo import fields, models, api
from odoo.addons import decimal_precision as dp
from py_linq import Enumerable


class UnpelledDried(models.Model):
    _name = 'unpelled.dried'
    _description = 'clase que para producción de secado y despelonado'

    active = fields.Boolean(
        'Activo',
        default=True
    )

    total_pending_lot_count = fields.Integer(
        'Lotes Pendientes',
        compute='_compute_total_pending_lot_count'
    )

    can_close = fields.Boolean(
        'Puede Cerrar',
    )

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('progress', 'En Proceso'),
        ('done', 'Terminado'),
        ('cancel', 'Cancelado')
    ],
        'Estado'
    )

    origin_location_id = fields.Many2one(
        'stock.location',
        'Origen del Movimiento'
    )

    dest_location_id = fields.Many2one(
        'stock.location',
        'Destino de Procesados'
    )

    name = fields.Char(
        'Proceso',
        compute='_compute_name'
    )

    producer_id = fields.Many2one(
        'res.partner',
        'Productor',
        required=True,
        domain=[('supplier', '=', True)]
    )

    product_in_id = fields.Many2one(
        'product.product',
        'Producto a ingresar',
        required=True,
        domain=[('categ_id.name', 'ilike', 'verde')]
    )

    in_lot_ids = fields.Many2many(
        'stock.production.lot',
        compute='_compute_in_lot_ids',
        string='Lote de Entrada'
    )

    in_variety = fields.Char(
        'Variedad Entrante',
        related='product_in_id.variety'
    )

    out_lot_id = fields.Many2one(
        'stock.production.lot',
        'Lote Producción'
    )

    out_serial_ids = fields.One2many(
        'stock.production.lot.serial',
        compute='_compute_out_serial_ids',
        inverse='_inverse_out_serial_ids',
        string='Series de Salida'
    )

    out_product_id = fields.Many2one(
        'product.product',
        'Producto de Salida',
        required=True
    )

    oven_use_ids = fields.One2many(
        'oven.use',
        'unpelled_dried_id',
        'Hornos',
        domain=[('history_id', '=', None)]
    )

    used_lot_ids = fields.One2many(
        'stock.production.lot',
        compute='_compute_used_lot_ids'
    )

    total_in_weight = fields.Float(
        'Total Ingresado',
        compute='_compute_total_in_weight',
        digits=dp.get_precision('Product Unit of Measure')
    )

    total_out_weight = fields.Float(
        'Total Secado',
        compute='_compute_total_out_weight',
        digits=dp.get_precision('Product Unit of Measure')
    )

    performance = fields.Float(
        'Rendimiento',
        compute='_compute_performance',
        digits=dp.get_precision('Product Unit of Measure')
    )

    history_ids = fields.One2many(
        'dried.unpelled.history',
        'unpelled_dried_id',
        'Historial'
    )

    canning_id = fields.Many2one(
        'product.product',
        'Envase',
        domain=[('categ_id.name', 'in', ['Maxisaco'])]
    )

    label_durability_id = fields.Many2one(
        'label.durability',
        'Durabilidad Etiqueta'
    )

    oven_in_use_ids = fields.Many2many(
        comodel_name='dried.oven',
        compute='_compute_oven_in_use_ids',
        string='Hornos en Uso')

    can_done = fields.Boolean('Se puede finalizar', compute='compute_can_done')

    locked = fields.Boolean('Bloqueado')

    show_new_process = fields.Boolean('Mostrar nuevo proceso',compute='compute_show_btn_new_process')

    @api.depends('oven_use_ids')
    @api.multi
    def compute_show_btn_new_process(self):
        for item in self:
            item.show_new_process = len(self.oven_use_ids) > 0


    @api.multi
    def compute_can_done(self):
        for item in self:
            item.can_done = all(oven.state == 'done' for oven in item.oven_use_ids) and item.oven_use_ids

    @api.multi
    def _compute_oven_in_use_ids(self):
        for item in self:
            item.oven_in_use_ids = item.oven_use_ids.filtered(lambda x: x.state != 'cancel').mapped('dried_oven_ids')

    @api.multi
    def _compute_used_lot_ids(self):
        for item in self:
            item.used_lot_ids = item.oven_use_ids.filtered(lambda x: x.state != 'cancel').mapped('used_lot_id')

    @api.multi
    def _compute_total_pending_lot_count(self):
        for item in self:
            lot_ids = self.env['stock.production.lot'].search([
                ('producer_id', '=', item.producer_id.id),
                ('product_id', '=', item.product_in_id.id),
                ('id', 'not in', item.oven_use_ids.mapped('used_lot_id.id')),
            ]).filtered(lambda x: not x.unpelled_dried_id and (x.balance > 0 or x.product_qty > 0))
            item.total_pending_lot_count = len(lot_ids)

    @api.multi
    def _compute_can_close(self):
        for item in self:
            item.can_close = any(oven.state == 'done' for oven in item.oven_use_ids) or all(
                oven.state == 'cancel' for oven in item.oven_use_ids)

    @api.multi
    def _compute_performance(self):
        for item in self:
            if item.total_in_weight > 0 and item.total_out_weight > 0:
                item.performance = (item.total_out_weight / item.total_in_weight) * 100

    @api.multi
    def _compute_total_out_weight(self):
        for item in self:
            item.total_out_weight = sum(item.out_serial_ids.mapped('display_weight'))

    @api.multi
    def _compute_total_in_weight(self):
        for item in self:
            if len(item.used_lot_ids) > 0:
                item.total_in_weight = sum(
                    item.used_lot_ids.mapped('stock_production_lot_serial_ids').mapped('display_weight'))
            else:
                item.total_in_weight = 0

    @api.multi
    def _compute_in_lot_ids(self):
        for item in self:
            item.in_lot_ids = item.oven_use_ids.filtered(lambda x: x.state != 'cancel').mapped('used_lot_id')

    @api.onchange('producer_id')
    def onchange_producer_id(self):
        if self.producer_id not in self.in_lot_ids.mapped('producer_id'):
            for oven_use_id in self.oven_use_ids:
                oven_use_id.used_lot_id = None

    @api.onchange('product_in_id')
    def onchange_product_in_id(self):
        if self.in_variety != self.out_product_id.get_variety():
            self.out_product_id = [(5,)]

    @api.onchange('out_product_id')
    def onchange_out_product_id(self):
        self.out_lot_id.write({
            'product_id': self.out_product_id.id
        })

    @api.multi
    def _compute_out_serial_ids(self):
        for item in self:
            item.out_serial_ids = item.out_lot_id.stock_production_lot_serial_ids

    @api.multi
    def _inverse_out_serial_ids(self):
        for item in self:
            item.out_lot_id.stock_production_lot_serial_ids = item.out_serial_ids

    @api.multi
    def _compute_name(self):
        for item in self:
            item.name = '{} {}'.format(item.out_lot_id.name, item.out_product_id.display_name)

    @api.model
    def create_out_lot(self):
        name = self.env['ir.sequence'].next_by_code('unpelled.dried')
        out_lot_id = self.env['stock.production.lot'].create({
            'name': name,
            'product_id': self.out_product_id.id,
            'is_dried_lot': True,
            'producer_id': self.producer_id.id
        })
        self.write({
            'out_lot_id': out_lot_id.id
        })

    @api.model
    def create_history(self):
        return self.env['dried.unpelled.history'].create({
            'is_old_version': True,
            'unpelled_dried_id': self.id,
            'total_in_weight': sum(self.oven_use_ids.filtered(
                lambda a: a.state == 'done'
            ).mapped('used_lot_id').mapped('stock_production_lot_serial_ids').mapped('display_weight'))
        })

    @api.model
    def create(self, values_list):
        res = super(UnpelledDried, self).create(values_list)
        res.state = 'draft'

        res.create_out_lot()

        return res

    @api.multi
    def write(self, values):
        res = super(UnpelledDried, self).write(values)
        for item in self:
            if item.out_lot_id.stock_production_lot_serial_ids:
                for serial_id in item.out_lot_id.stock_production_lot_serial_ids:
                    serial_id.canning_id = item.canning_id
                    serial_id.label_durability_id = item.label_durability_id
                    serial_id.producer_id = item.producer_id
        return res

    @api.multi
    def unlink(self):
        for item in self:
            item.oven_use_ids.mapped('dried_oven_ids').write({
                'is_in_use': False
            })

        return super(UnpelledDried, self).unlink()

    @api.multi
    def cancel_unpelled_dried(self):
        for item in self:
            item.write({
                'state': 'cancel'
            })
            item.oven_use_ids.filtered(lambda x: x.state != 'cancel').mapped('dried_oven_ids').set_is_in_use(False)

    @api.multi
    def finish_unpelled_dried(self):
        for item in self:
            if item.out_lot_id.product_id != item.out_product_id:
                item.out_lot_id.write({
                    'product_id': item.out_product_id.id
                })
            for oven_use in item.oven_use_ids.filtered(lambda a: a.state == 'done'):
                oven_use_id = item.oven_use_ids.filtered(
                    lambda a: a.state not in ('done', 'cancel') and a.dried_oven_id
                )
                if oven_use_id:
                    raise models.ValidationError('el lote {} no ha sido terminado en el cajón {}.'
                                                 ' no se puede cerrar un lote en que se encuentre en '
                                                 'cajones completos (no mezclados con otros lotes) y que '
                                                 'se encuentren todavía en proceso'.format(
                        oven_use_id.used_lot_id.name, oven_use_id.dried_oven_id.name
                    ))
                oven_use.used_lot_id.write({
                    'unpelled_state': 'done',
                })
            if not item.oven_use_ids.filtered(lambda a: a.state == 'done'):
                raise models.ValidationError('no hay hornos listos para cerrar por procesar')
            if not item.out_serial_ids:
                raise models.ValidationError('Debe agregar al menos una serie de salida al proceso')
            history_id = item.create_history()
            stock_move = self.env['stock.move'].create({
                'name': item.out_lot_id.name,
                'company_id': self.env.user.company_id.id,
                'location_id': item.origin_location_id.id,
                'location_dest_id': item.dest_location_id.id,
                'product_id': item.out_product_id.id,
                'product_uom': item.out_product_id.uom_id.id,
                'product_uom_qty': item.total_out_weight,
                'quantity_done': item.total_out_weight,
                'state': 'done',
            })
            consumed = []
            for used_lot_id in item.oven_use_ids.filtered(lambda a: a.state == 'done').mapped('used_lot_id'):
                quant_id = used_lot_id.get_stock_quant()
                if quant_id:
                    if used_lot_id.get_stock_quant().balance > 0:
                        consumed.append([0, 0, {
                            'lot_name': used_lot_id.name,
                            'reference': used_lot_id.name,
                            'product_id': used_lot_id.product_id.id,
                            'location_id': used_lot_id.get_stock_quant().location_id.id,
                            'location_dest_id': item.origin_location_id.id,
                            'qty_done': used_lot_id.get_stock_quant().balance,
                            'product_uom_qty': 0,
                            'product_uom_id': used_lot_id.product_id.uom_id.id,
                            'lot_id': used_lot_id.id,
                            'state': 'done',
                            'move_id': stock_move.id
                        }])
            self.env['stock.move.line'].create({
                'lot_name': item.out_lot_id.name,
                'consume_line_ids': consumed,
                'reference': item.out_lot_id.name,
                'product_id': item.out_product_id.id,
                'location_id': item.origin_location_id.id,
                'location_dest_id': item.dest_location_id.id,
                'qty_done': item.total_out_weight,
                'product_uom_qty': 0,
                'product_uom_id': item.out_product_id.uom_id.id,
                'lot_id': item.out_lot_id.id,
                'state': 'done',
                'move_id': stock_move.id
            })
            item.oven_use_ids.filtered(lambda a: a.state == 'done').mapped('dried_oven_ids').write({
                'is_in_use': False,
                'state': 'free'
            })
            item.oven_use_ids.filtered(lambda a: a.state == 'done').write({
                'unpelled_dried_id': None,
                'history_id': history_id.id,
            })
            process = self.env['unpelled.dried'].search([('state', 'in', ['draft', 'progress']),
                                                         ('out_product_id', '=', item.out_product_id.id),
                                                         ('producer_id', '=', item.producer_id.id),
                                                         ('id', '!=', self.id)])
            item.out_lot_id.verify_without_lot()
            item.out_lot_id.update_kg(item.out_lot_id.id)
            item.write({
                'state': 'done'
            })
            if len(process) > 0:
                view_id = self.env.ref('dimabe_manufacturing.dried_unpelled_history_form_view')
                return {
                    "name": 'Historial',
                    "type": 'ir.actions.act_window',
                    "view_type": 'form',
                    "view_mode": 'form',
                    "res_model": 'dried.unpelled.history',
                    'views': [(view_id.id, 'form')],
                    'view_id': view_id.id,
                    'target': 'current',
                    'res_id': history_id.id,
                    'context': self.env.context,
                }
            else:
                new_process = self.env['unpelled.dried'].create({
                    'producer_id': item.producer_id.id,
                    'state': 'draft',
                    'origin_location_id': item.origin_location_id.id,
                    'dest_location_id': item.dest_location_id.id,
                    'product_in_id': item.product_in_id.id,
                    'out_product_id': item.out_product_id.id,
                    'canning_id': item.canning_id.id,
                    'label_durability_id': item.label_durability_id.id,
                })
                view_id = self.env.ref('dimabe_manufacturing.unpelled_dried_form_view')
                return {
                    "name": 'Nuevo Proceso',
                    "type": 'ir.actions.act_window',
                    "view_type": 'form',
                    "view_mode": 'form',
                    "res_model": 'unpelled.dried',
                    'views': [(view_id.id, 'form')],
                    'view_id': view_id.id,
                    'target': 'current',
                    'res_id': new_process.id,
                    'context': self.env.context,
                }

    @api.multi
    def start_new_unpelled(self):
        for item in self:
            new_process = self.env['unpelled.dried'].create({
                'producer_id': item.producer_id.id,
                'state': 'draft',
                'origin_location_id': item.origin_location_id.id,
                'dest_location_id': item.dest_location_id.id,
                'product_in_id': item.product_in_id.id,
                'out_product_id': item.out_product_id.id,
                'canning_id': item.canning_id.id,
                'label_durability_id': item.label_durability_id.id,
            })
            view_id = self.env.ref('dimabe_manufacturing.unpelled_dried_form_view')
            return {
                "name": 'Nuevo Proceso',
                "type": 'ir.actions.act_window',
                "view_type": 'form',
                "view_mode": 'form',
                "res_model": 'unpelled.dried',
                'views': [(view_id.id, 'form')],
                'view_id': view_id.id,
                'target': 'current',
                'res_id': new_process.id,
                'context': self.env.context,
            }

    @api.multi
    def go_history(self):
        unpelled_dried_id = 'unpelled_dried_id' in self.env.context and self.env.context['unpelled_dried_id'] or False
        self.out_lot_id.verify_without_lot()
        self.out_lot_id.update_kg(self.out_lot_id.id)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dried.unpelled.history',
            'name': 'Historial',
            'views': [
                [self.env.ref('dimabe_manufacturing.dried_unpelled_history_tree_view').id, 'tree'],
                [False, 'form']
            ],
            'target': 'fullscreen',
            'domain': [('producer_id', '=', self.producer_id.id), ('out_product_id', '=', self.out_product_id.id)]
        }

    @api.multi
    def go_another_process(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'unpelled.dried',
            'name': f'Procesos Activos de {self.producer_id.name}',
            'views': [[self.env.ref('dimabe_manufacturing.unpelled_dried_tree_view').id, 'tree'], [False, 'form']],
            'target': 'fullscreen',
            'domain': [('producer_id', '=', self.producer_id.id), ('out_product_id', '=', self.out_product_id.id),
                       ('state', 'in', ['progress', 'draft'])]
        }

    def print_all_out_selection(self):
        serials = self.out_serial_ids.filtered(lambda x: x.to_print)
        serials.write({
            'printed': True,
            'to_print': False
        })
        return self.env.ref('dimabe_manufacturing.action_print_all_out_serial') \
            .report_action(serials)

    def print_all_out_serial(self):
        self.out_serial_ids.write({
            'printed': True
        })
        return self.env.ref('dimabe_manufacturing.action_print_all_out_serial') \
            .report_action(self.out_serial_ids)
