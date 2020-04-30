from odoo import fields, models, api
from odoo.addons import decimal_precision as dp


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'
    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'el lote que intenta crear, ya existe en el sistema')
    ]

    unpelled_state = fields.Selection([
        ('waiting', 'En Espera'),
        ('drying', 'Secando'),
        ('done', 'Terminado')
    ],
        'Estado',
    )

    can_add_serial = fields.Boolean(
        'Puede Agregar Series',
        compute='_compute_can_add_serial'
    )

    producer_ids = fields.One2many(
        'res.partner',
        compute='_compute_producer_ids'
    )

    product_variety = fields.Char(
        'Variedad',
        compute='_compute_product_variety'
    )

    producer_id = fields.Many2one(
        'res.partner',
        string='Productor'
    )

    reception_guide_number = fields.Integer(
        'Guía',
        related='stock_picking_id.guide_number',
        store=True
    )

    reception_state = fields.Selection(
        string='Estado de la reecepción',
        related='stock_picking_id.state'
    )

    product_canning = fields.Char(
        'Envase',
        compute='_compute_reception_data'
    )

    is_prd_lot = fields.Boolean('Es Lote de salida de Proceso')

    is_standard_weight = fields.Boolean(
        'Series Peso Estandar',
        related='product_id.is_standard_weight'
    )

    standard_weight = fields.Float(
        'Peso Estandar',
        related='product_id.weight',
        digits=dp.get_precision('Product Unit of Measure')
    )

    qty_standard_serial = fields.Integer('Cantidad de Series')

    stock_production_lot_serial_ids = fields.One2many(
        'stock.production.lot.serial',
        'stock_production_lot_id',
        string="Detalle"
    )

    serial_without_pallet_ids = fields.One2many(
        'stock.production.lot.serial',
        compute='_compute_serial_without_pallet_ids',
        string='Series sin Pallet'
    )

    stock_production_lot_available_serial_ids = fields.One2many(
        'stock.production.lot.serial',
        compute='_compute_stock_production_lot_available_serial_ids',
        string='Series Disponibles'
    )

    total_serial = fields.Float(
        'Total',
        compute='_compute_total_serial',
        digits=dp.get_precision('Product Unit of Measure')
    )

    count_serial = fields.Integer(
        'Total Series',
        compute='_compute_count_serial'
    )

    available_total_serial = fields.Float(
        'Total Disponible',
        compute='_compute_available_total_serial',
        search='_search_available_total_serial',
        digits=dp.get_precision('Product Unit of Measure')
    )

    qty_to_reserve = fields.Float(
        'Cantidad a Reservar',
        digits=dp.get_precision('Product Unit of Measure')
    )

    is_reserved = fields.Boolean('Esta reservado?', compute='reserved', default=False)

    context_picking_id = fields.Integer(
        'picking del contexto',
        compute='_compute_context_picking_id'
    )

    pallet_ids = fields.One2many(
        'manufacturing.pallet',
        compute='_compute_pallet_ids'
    )

    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Bodega',
        related='stock_picking_id.picking_type_id',
        store=True

    )

    reception_net_weight = fields.Float(
        'kg. Neto',
        related='stock_picking_id.net_weight',
        digits=dp.get_precision('Product Unit of Measure'),
        store=True
    )

    reception_date = fields.Datetime(
        'Fecha Recepción',
        related='stock_picking_id.truck_in_date',
        store=True
    )

    reception_elapsed_time = fields.Char(
        'Hr Camión en Planta',
        related='stock_picking_id.elapsed_time',
        store=True
    )

    oven_init_active_time = fields.Integer(
        'Inicio Tiempo Activo',
        related='oven_use_ids.init_active_time'
    )

    finish_active_time = fields.Integer(
        'Fin Tiempo Activo',
        related='oven_use_ids.finish_active_time'
    )

    oven_use_ids = fields.One2many(
        'oven.use',
        'used_lot_id',
        'Uso de Hornos',
        sort='active_seconds desc'
    )

    drier_counter = fields.Integer(
        'Hr en Secador',
        related='oven_use_ids.active_seconds'
    )

    stock_picking_id = fields.Many2one(
        'stock.picking',
        'Recepción'
    )

    all_pallet_ids = fields.One2many(
        'manufacturing.pallet',
        compute='_compute_all_pallet_ids',
        string='pallets'
    )

    label_durability_id = fields.Many2one(
        'label.durability',
        'Durabilidad Etiqueta'
    )

    is_dried_lot = fields.Boolean(
        'Es lote de Secado'
    )

    is_dimabe_team = fields.Boolean(
        'Es Equipo Dimabe',
        compute='_compute_is_dimabe_team'
    )

    product_variety = fields.Char(
        'Variedad del Producto',
        related='product_id.variety'
    )

    product_caliber = fields.Char(
        'Calibre del Producto',
        related='product_id.caliber'
    )

    serial_not_consumed = fields.Integer('Envases Disponible',compute='_compute_serial_not_consumed')

    dried_report_product_name = fields.Char(compute='_compute_lot_oven_use')

    location_id = fields.Many2one('stock.location',compute='_compute_lot_location')

    serial_not_consumed = fields.Integer('Envases disponible',compute='_compute_serial_not_consumed',store=True)

    available_weight = fields.Float('Kilos Disponible',compute='_compute_available_weight')


    @api.multi
    def _compute_available_weight(self):
        for item in self:
            item.available_weight = sum(item.stock_production_lot_serial_ids.filtered(
                lambda a: not a.consumed
            ).mapped('real_weight'))


    @api.multi
    def _compute_serial_not_consumed(self):
        for item in self:
            item.serial_not_consumed = len(item.stock_production_lot_serial_ids.filtered(
                lambda a: not a.consumed))


    @api.multi
    def _compute_lot_location(self):
        for item in self:
            dried = self.env['dried.unpelled.history'].search([('out_lot_id','=',item.id)])
            item.location_id = dried.dest_location_id

    @api.multi
    def _compute_lot_oven_use(self):
        for item in self:
            if item.is_dried_lot:
                dried = self.env['dried.unpelled.history'].search([('out_lot_id','=',item.id)])
                dried_oven = []
                for oven in dried.oven_use_ids.mapped('dried_oven_ids'):
                    dried_oven.append(oven.name+" ")
                    if oven.id == dried.oven_use_ids.mapped('dried_oven_ids')[-1].id:
                        dried_oven.append(oven.name)
                ovens = ''
                item.dried_report_product_name = item.product_id.display_name + ' ' + ovens.join(dried_oven)



    @api.multi
    def _compute_serial_not_consumed(self):
        for item in self:
            item.serial_not_consumed = len(item.stock_production_lot_serial_ids.filtered(lambda a: not a.consumed))

    @api.multi
    def _compute_can_add_serial(self):
        for item in self:
            if item.is_prd_lot:
                item.can_add_serial = True

    @api.multi
    def _compute_serial_without_pallet_ids(self):
        for item in self:
            item.serial_without_pallet_ids = item.stock_production_lot_serial_ids.filtered(
                lambda a: not a.pallet_id
            )

    @api.multi
    def _compute_is_dimabe_team(self):
        for item in self:
            item.is_dimabe_team = self.env.user.is_dimabe_team

    @api.onchange('label_durability_id')
    def onchange_label_durability_id(self):
        if self.stock_production_lot_serial_ids:
            for serial_id in self.stock_production_lot_serial_ids:
                serial_id.write({
                    'label_durability_id': self.label_durability_id.id
                })

    @api.multi
    def _compute_producer_ids(self):

        for item in self:
            if item.is_prd_lot:
                workorder = self.env['mrp.workorder'].search([
                    '|',
                    ('final_lot_id', '=', item.id),
                    ('production_finished_move_line_ids.lot_id', '=', item.id)
                ])

                producers = workorder.mapped('potential_serial_planned_ids.stock_production_lot_id.producer_id')

                item.producer_ids = self.env['res.partner'].search([
                    '|',
                    ('id', 'in', producers.mapped('id')),
                    ('always_to_print', '=', True)
                ])

            elif item.is_dried_lot:
                dried_data = self.env['unpelled.dried'].search([
                    ('out_lot_id', '=', item.id)
                ])
                if not dried_data:
                    dried_data = self.env['dried.unpelled.history'].search([
                        ('out_lot_id', '=', item.id)
                    ])
                if dried_data:

                    item.producer_ids = self.env['res.partner'].search([
                        '|',
                        ('id', '=', dried_data.in_lot_ids.mapped('stock_picking_id.partner_id.id')),
                        ('always_to_print', '=', True)
                    ])

            else:
                item.producer_ids = self.env['res.partner'].search([
                    '|',
                    ('supplier', '=', True),
                    ('always_to_print', '=', True)

                ])
            if item.producer_ids:
                item.producer_ids = item.producer_ids.filtered(
                    lambda a: a.company_type == 'company' or a.always_to_print
                )

    # @api.onchange('producer_id')
    # def _onchange_producer_id(self):
    #
    #     self.stock_production_lot_serial_ids.write({
    #         'producer_id': self.producer_id.id
    #     })
    #
    #     self.all_pallet_ids.write({
    #         'producer_id': self.producer_id.id
    #     })

    @api.multi
    def _compute_all_pallet_ids(self):
        for item in self:
            item.all_pallet_ids = item.stock_production_lot_serial_ids.mapped('pallet_id')

    @api.multi
    def _compute_count_serial(self):
        for item in self:
            item.count_serial = len(item.stock_production_lot_serial_ids)

    @api.multi
    def print_all_serial(self):
        return self.env.ref('dimabe_manufacturing.action_print_all_serial') \
            .report_action(self.stock_production_lot_serial_ids)

    @api.multi
    def _compute_product_variety(self):
        for item in self:
            item.product_variety = item.product_id.get_variety()

    @api.multi
    def _compute_pallet_ids(self):
        for item in self:
            item.pallet_ids = item.stock_production_lot_available_serial_ids.mapped('pallet_id')

    @api.multi
    def _compute_context_picking_id(self):
        for item in self:
            if 'stock_picking_id' in self.env.context:
                item.context_picking_id = self.env.context['stock_picking_id']

    @api.multi
    def _compute_stock_production_lot_available_serial_ids(self):
        for item in self:
            item.stock_production_lot_available_serial_ids = item.stock_production_lot_serial_ids.filtered(
                lambda a: not a.reserved_to_stock_picking_id
            )

    @api.multi
    def _compute_available_total_serial(self):
        for item in self:
            item.available_total_serial = sum(item.stock_production_lot_serial_ids.filtered(
                lambda a: not a.reserved_to_stock_picking_id
            ).mapped('display_weight'))

    @api.multi
    def _search_available_total_serial(self, operator, value):
        stock_production_lot_ids = self.env['stock.production.lot.serial'].search([
            ('consumed', '=', False),
            ('reserved_to_stock_picking_id', '=', False)
        ]).mapped('stock_production_lot_id')

        if operator == '>':
            stock_production_lot_ids = stock_production_lot_ids.filtered(
                lambda a: sum(a.stock_production_lot_serial_ids.mapped('display_weight')) > value
            )
        elif operator == '=':
            stock_production_lot_ids = stock_production_lot_ids.filtered(
                lambda a: sum(a.stock_production_lot_serial_ids.mapped('display_weight')) == value
            )
        elif operator == '<':
            stock_production_lot_ids = stock_production_lot_ids.filtered(
                lambda a: sum(a.stock_production_lot_serial_ids.mapped('display_weight')) < value
            )
        elif operator == '>=':
            stock_production_lot_ids = stock_production_lot_ids.filtered(
                lambda a: sum(a.stock_production_lot_serial_ids.mapped('display_weight')) >= value
            )
        elif operator == '<=':
            stock_production_lot_ids = stock_production_lot_ids.filtered(
                lambda a: sum(a.stock_production_lot_serial_ids.mapped('display_weight')) <= value
            )

        return [('id', 'in', stock_production_lot_ids.mapped('id'))]

    @api.multi
    def _compute_reception_data(self):
        for item in self:
            if item.stock_picking_id:
                item.product_canning = item.stock_picking_id.get_canning_move().name

    @api.multi
    def _compute_total_serial(self):
        for item in self:
            item.total_serial = sum(item.stock_production_lot_serial_ids.mapped('display_weight'))

    @api.multi
    def add_to_packing_list(self):
        picking_id = None
        if 'stock_picking_id' in self.env.context:
            picking_id = self.env.context['stock_picking_id']
            stock_picking = self.env['stock.picking'].search([('id','=',picking_id)])
        for item in self:
            serial_to_assign_ids = item.stock_production_lot_serial_ids.filtered(
                lambda a: not a.consumed and not a.reserved_to_stock_picking_id
            )
            lot_id = serial_to_assign_ids.mapped('stock_production_lot_id')
            models._logger.error(lot_id)
            for lot in lot_id:
                available_total_serial = lot.available_total_serial
                serial_to_assign_ids.update({
                    'reserved_to_stock_picking_id': stock_picking.id
                })

                item.all_pallet_ids.update({
                    'is_reserved': True
                })
                stock_move = stock_picking.move_lines.filtered(
                    lambda a: a.product_id == item.product_id
                )

                stock_quant = item.get_stock_quant()

                if not stock_quant:
                    raise models.ValidationError('El lote {} aún se encuentra en proceso.'.format(
                        item.name
                    ))

                move_line = self.env['stock.move.line'].create({
                    'product_id': lot.product_id.id,
                    'lot_id': lot.id,
                    'product_uom_qty': available_total_serial,
                    'product_uom_id': stock_move.product_uom.id,
                    'location_id': stock_quant.location_id.id,
                    # 'qty_done': item.display_weight,
                    'location_dest_id': stock_picking.partner_id.property_stock_customer.id
                })

                stock_move.sudo().update({
                    'move_line_ids': [
                        (4, move_line.id)
                    ]
                })

                stock_picking.update({
                    'move_line_ids': [
                        (4, move_line.id)
                    ]
                })

                stock_quant.sudo().update({
                    'reserved_quantity': stock_quant.total_reserved
                })

            #serial_to_assign_ids.with_context(stock_picking_id=picking_id).reserve_picking()

    @api.multi
    def reserved(self):
        print('')
        # for item in self:
        #     if item.qty_standard_serial == 0:
        #         if 'stock_picking_id' in self.env.context:
        #             stock_picking_id = self.env.context['stock_picking_id']
        #             reserve = self.env.context['reserved']
        #             models._logger.error(reserve)
        #             stock_picking = self.env['stock.picking'].search([('id', '=', stock_picking_id)])
        #             if stock_picking:
        #                 stock_move = stock_picking.move_ids_without_package.filtered(
        #                     lambda x: x.product_id == item.product_id
        #                 )
        #                 stock_quant = item.get_stock_quant()
        #                 stock_quant.sudo().update({
        #                     'reserved_quantity': stock_quant.reserved_quantity + item.qty_to_reserve
        #                 })
        #                 item.update({
        #                     'qty_to_reserve': reserve,
        #                     'is_reserved': True
        #                 })
        #                 models._logger.error(item.is_reserved)
        #                 item.is_reserved = True
        #                 models._logger.error(item.is_reserved)
        #                 move_line = self.env['stock.move.line'].create({
        #                     'product_id': item.product_id.id,
        #                     'lot_id': item.id,
        #                     'product_uom_qty': reserve,
        #                     'product_uom_id': stock_move.product_uom.id,
        #                     'location_id': stock_quant.location_id.id,
        #                     'location_dest_id': stock_picking.partner_id.property_stock_customer.id
        #                 })
        #                 models._logger.error(item.is_reserved)
        #                 stock_move.sudo().update({
        #                     'move_line_ids': [
        #                         (4, move_line.id)
        #                     ]
        #                 })

    @api.multi
    def unreserved(self):
        for item in self:
            stock_picking = None
            if 'stock_picking_id' in self.env.context:
                stock_picking_id = self.env.context['stock_picking_id']
                stock_picking = self.env['stock.picking'].search([('id', '=', stock_picking_id)])
            if stock_picking:

                item.stock_production_lot_serial_ids.filtered(
                    lambda a: a.reserved_to_stock_picking_id.id == stock_picking_id
                ).unreserved_picking()

                stock_move = stock_picking.move_ids_without_package.filtered(
                    lambda x: x.product_id == item.product_id
                )
                move_line = stock_move.move_line_ids.filtered(
                    lambda a: a.lot_id.id == item.id and a.product_uom_qty == stock_move.reserved_availability
                )
                item.update({
                    'qty_to_reserve': 0,
                    'is_reserved': False
                })

                stock_quant = item.get_stock_quant()

                stock_quant.sudo().update({
                    'reserved_quantity': stock_quant.reserved_quantity - stock_move.product_uom_qty
                })

                for ml in move_line:
                    ml.write({'move_id': None, 'reserved_availability': 0})

    @api.multi
    def write(self, values):
        for item in self:
            res = super(StockProductionLot, self).write(values)
            counter = 0
            if not item.is_standard_weight:
                for serial in item.stock_production_lot_serial_ids:
                    counter += 1
                    tmp = '00{}'.format(counter)
                    serial.serial_number = item.name + tmp[-3:]
            return res

    @api.multi
    def generate_standard_pallet(self):
        for item in self:

            if not item.producer_id:
                raise models.ValidationError('debe seleccionar un productor')
            pallet = self.env['manufacturing.pallet'].create({
                'producer_id': item.producer_id.id
            })

            for counter in range(item.qty_standard_serial):
                tmp = '00{}'.format(1 + len(item.stock_production_lot_serial_ids))

                item.env['stock.production.lot.serial'].create({
                    'stock_production_lot_id': item.id,
                    'display_weight': item.product_id.weight,
                    'serial_number': item.name + tmp[-3:],
                    'belongs_to_prd_lot': True,
                    'pallet_id': pallet.id,
                    'producer_id': pallet.producer_id.id
                })

            pallet.update({
                'state': 'close'
            })

    @api.model
    def get_stock_quant(self):
        return self.quant_ids.filtered(
            lambda a: a.location_id.name == 'Stock'
        )

    def show_available_serial(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.production.lot',
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(self.env.ref('dimabe_manufacturing.available_lot_form_view').id, 'form')],
            'target': 'new',
            'context': self.env.context
        }
