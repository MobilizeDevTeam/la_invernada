from odoo import fields, models, api
from odoo.addons import decimal_precision as dp
from datetime import date, datetime


class MrpWorkorder(models.Model):
    _name = 'mrp.workorder'
    _inherit = ['mrp.workorder', 'barcodes.barcode_events_mixin']

    show_manual_input = fields.Boolean(
        'Digitar Serie Manualmente'
    )

    positioning_state = fields.Selection(
        related='production_id.positioning_state',
        string='Estado movimiento de bodega a producción'
    )

    client_id = fields.Many2one(
        'res.partner',
        related='production_id.client_id',
        string='Cliente',
        store=True
    )

    destiny_country_id = fields.Many2one(
        'res.country',
        related='production_id.destiny_country_id',
        string='País',
        store=True
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        related='production_id.stock_picking_id.sale_id',
        string='Pedido de Venta',
        store=True
    )

    pt_balance = fields.Float(
        'Saldo Bodega PT',
        digits=dp.get_precision('Product Unit of Measure'),
        related='production_id.pt_balance'
    )

    charging_mode = fields.Selection(
        related='production_id.charging_mode',
        string='Modo de Carga'
    )

    client_label = fields.Boolean(
        'Etiqueta Cliente',
        related='production_id.client_label'
    )

    unevenness_percent = fields.Float(
        '% Descalibre',
        digits=dp.get_precision('Product Unit of Measure'),
        related='production_id.unevenness_percent'
    )

    etd = fields.Date(
        'Fecha de Despacho',
        related='production_id.etd'
    )

    label_durability_id = fields.Many2one(
        'label.durability',
        string='Durabilidad Etiqueta',
        related='production_id.label_durability_id'
    )

    observation = fields.Text(
        'Observación',
        related='production_id.observation'
    )

    production_finished_move_line_ids = fields.One2many(
        string='Productos Finalizados',
        related='production_id.finished_move_line_ids'
    )

    summary_out_serial_ids = fields.One2many(
        'stock.production.lot.serial',
        compute='_compute_summary_out_serial_ids',
        string='Resumen de Salidas'
    )

    material_product_ids = fields.One2many(
        'product.product',
        compute='_compute_material_product_ids'
    )

    byproduct_move_line_ids = fields.One2many(
        'stock.move.line',
        compute='_compute_byproduct_move_line_ids',
        string='subproductos'
    )

    potential_serial_planned_ids = fields.One2many(
        'stock.production.lot.serial',
        'used_in_workorder_id'
    )

    confirmed_serial = fields.Char('Codigo de Barra')

    manufacturing_pallet_ids = fields.One2many(
        'manufacturing.pallet',
        compute='_compute_manufacturing_pallet_ids',
        string='Pallets'
    )

    there_is_serial_without_pallet = fields.Boolean(
        'Hay Series sin pallet',
        compute='_compute_there_is_serial_without_pallet'
    )

    is_match = fields.Boolean('Es Partido', compute='compute_is_match')

    product_variety = fields.Char(related='product_id.variety')

    location_id = fields.Many2one('stock.location', related='production_id.location_dest_id')

    product_qty = fields.Float(related='production_id.product_qty')

    lot_produced_id = fields.Integer('Lote a producir', compute='_compute_lot_produced')

    in_weight = fields.Float('Kilos Ingresados',
                             digits=dp.get_precision('Product Unit of Measure'))

    out_weight = fields.Float('Kilos Producidos',
                              digits=dp.get_precision('Product Unit of Measure'))

    pt_out_weight = fields.Float('Kilos Producidos del PT',
                                 digits=dp.get_precision('Product Unit of Meausure'))

    producers_id = fields.Many2many('res.partner', string='Productores Filtro')

    producer_to_view = fields.Many2many('res.partner', string='Productores', compute='_compute_producers_id')

    pallet_qty = fields.Integer('Cantidad de Pallets', compute='_compute_pallet_qty')

    pallet_content = fields.Float('Kilos Totales', compute='_compute_pallet_content')

    pallet_serial = fields.Integer('Total de Series', compute='_compute_pallet_serial')

    have_subproduct = fields.Boolean('Tiene subproductos')

    component_id = fields.Many2one('product.product', readonly=False)

    to_done = fields.Boolean('Para Finalizar')

    supervisor_name = fields.Char('Supervisor')

    turn_name = fields.Char('Turno')

    start_date = fields.Datetime(
        required=False)

    start_date_show = fields.Datetime(
        string='Fecha de Inicio',
        compute='compute_start_date_show',
        required=False)

    @api.multi
    def compute_start_date_show(self):
        for item in self:
            if item.start_date:
                item.start_date_show = item.start_date
            else:
                item.start_date_show = item.create_date

    @api.multi
    def _compute_producers_id(self):
        for item in self:
            if item.producers_id:
                item.producer_to_view = item.producers_id
            elif item.potential_serial_planned_ids and item.state == 'done' and not item.producers_id:
                item.producer_to_view = item.potential_serial_planned_ids.mapped('producer_id')

    @api.multi
    def organize_move_line(self):
        for move in self.production_id.move_raw_ids:
            for active in move.active_move_line_ids:
                active.unlink()
        for item in self.potential_serial_planned_ids.mapped('stock_production_lot_id'):
            stock_move = self.production_id.move_raw_ids.filtered(lambda a: a.product_id.id == item.product_id.id)
            virtual_location_production_id = self.env['stock.location'].search([
                ('usage', '=', 'production'),
                ('location_id.name', 'like', 'Virtual Locations')
            ])
            if item not in stock_move.active_move_line_ids.mapped('lot_id'):
                if not self.lot_produced_id:
                    stock_move.update({
                        'active_move_line_ids': [
                            (0, 0, {
                                'product_id': item.product_id.id,
                                'lot_id': item.id,
                                'qty_done': sum(self.potential_serial_planned_ids.filtered(
                                    lambda a: a.stock_production_lot_id.id == item.id).mapped('display_weight')),
                                'lot_produced_id': self.production_finished_move_line_ids.filtered(
                                    lambda a: a.product_id.id == self.product_id.id and a.lot_id)[0].lot_id,
                                'workorder_id': self.id,
                                'production_id': self.production_id.id,
                                'product_uom_id': stock_move.product_uom.id,
                                'location_id': item.stock_production_lot_serial_ids.mapped(
                                    'production_id').location_src_id.id if not item.location_id else item.location_id.id,
                                'location_dest_id': virtual_location_production_id.id
                            })
                        ]
                    })
                else:
                    stock_move.update({
                        'active_move_line_ids': [
                            (0, 0, {
                                'product_id': item.product_id.id,
                                'lot_id': item.id,
                                'qty_done': sum(self.potential_serial_planned_ids.filtered(
                                    lambda a: a.stock_production_lot_id.id == item.id).mapped('display_weight')),
                                'lot_produced_id': self.lot_produced_id,
                                'workorder_id': self.id,
                                'production_id': self.production_id.id,
                                'product_uom_id': stock_move.product_uom.id,
                                'location_id': item.stock_production_lot_serial_ids.mapped(
                                    'production_id').location_src_id.id if not item.location_id else item.location_id.id,
                                'location_dest_id': virtual_location_production_id.id
                            })
                        ]
                    })

    @api.multi
    def organize_move_line(self):
        for move in self.production_id.move_raw_ids.filtered(lambda a: a.needs_lots):
            for active in move.active_move_line_ids:
                active.unlink()
        for item in self.potential_serial_planned_ids.mapped('stock_production_lot_id'):
            stock_move = self.production_id.move_raw_ids.filtered(lambda a: a.product_id.id == item.product_id.id)
            virtual_location_production_id = self.env['stock.location'].search([
                ('usage', '=', 'production'),
                ('location_id.name', 'like', 'Virtual Locations')
            ])
            if item not in stock_move.active_move_line_ids.mapped('lot_id'):
                if not self.lot_produced_id:
                    stock_move.update({
                        'active_move_line_ids': [
                            (0, 0, {
                                'product_id': item.product_id.id,
                                'lot_id': item.id,
                                'qty_done': sum(self.potential_serial_planned_ids.filtered(
                                    lambda a: a.stock_production_lot_id.id == item.id).mapped('display_weight')),
                                'lot_produced_id': self.production_finished_move_line_ids.filtered(
                                    lambda a: a.product_id.id == self.product_id.id and a.lot_id)[0].lot_id,
                                'workorder_id': self.id,
                                'production_id': self.production_id.id,
                                'product_uom_id': stock_move.product_uom.id,
                                'location_id': item.stock_production_lot_serial_ids.mapped(
                                    'production_id').location_src_id.id if not item.location_id else item.location_id.id,
                                'location_dest_id': virtual_location_production_id.id
                            })
                        ]
                    })
                else:
                    stock_move.update({
                        'active_move_line_ids': [
                            (0, 0, {
                                'product_id': item.product_id.id,
                                'lot_id': item.id,
                                'qty_done': sum(self.potential_serial_planned_ids.filtered(
                                    lambda a: a.stock_production_lot_id.id == item.id).mapped('display_weight')),
                                'lot_produced_id': self.lot_produced_id,
                                'workorder_id': self.id,
                                'production_id': self.production_id.id,
                                'product_uom_id': stock_move.product_uom.id,
                                'location_id': item.stock_production_lot_serial_ids.mapped(
                                    'production_id').location_src_id.id if not item.location_id else item.location_id.id,
                                'location_dest_id': virtual_location_production_id.id
                            })
                        ]
                    })

    @api.multi
    def fix_env(self):
        workorder_ids = self.env['mrp.workorder'].search([])
        for work in workorder_ids:
            first_state = work.state
            if first_state == 'done':
                query = "UPDATE mrp_workorder set state = 'ready' where id = {}".format(work.id)
                cr = self._cr
                cr.execute(query)
            producer_ids = self.env['stock.production.lot.serial'].search(
                [('used_in_workorder_id.id', '=', work.id)]).mapped('producer_id')
            for prod in producer_ids:
                work.write({
                    'producer_ids': [(4, prod.id)]
                })
            if first_state == 'done':
                query = "UPDATE mrp_workorder set state = 'done' where id = {}".format(work.id)
                cr = self._cr
                cr.execute(query)

    @api.multi
    def _compute_pallet_content(self):
        for item in self:
            if item.manufacturing_pallet_ids:
                item.pallet_content = sum(item.manufacturing_pallet_ids.mapped('total_content_weight'))

    @api.multi
    def _compute_pallet_serial(self):
        for item in self:
            if item.manufacturing_pallet_ids:
                item.pallet_serial = len(item.manufacturing_pallet_ids.mapped('lot_serial_ids'))

    @api.multi
    def _compute_pallet_qty(self):
        for item in self:
            if item.manufacturing_pallet_ids:
                item.pallet_qty = len(item.manufacturing_pallet_ids)

    @api.multi
    def show_in_serials(self):
        self.ensure_one()
        return {
            'name': "Series de Entrada",
            'view_type': 'form',
            'view_mode': 'tree,graph,form,pivot',
            'res_model': 'stock.production.lot.serial',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'views': [
                [self.env.ref('dimabe_manufacturing.stock_production_lot_serial_process_in_form_view').id, 'tree']],
            'context': self.env.context,
            'domain': [('id', 'in', self.potential_serial_planned_ids.mapped("id"))]
        }

    @api.multi
    def show_out_serials(self):
        self.ensure_one()
        return {
            'name': "Series de Salida",
            'view_type': 'form',
            'view_mode': 'tree,graph,form,pivot',
            'res_model': 'stock.production.lot.serial',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'views': [
                [self.env.ref('dimabe_manufacturing.stock_production_lot_serial_process_out_form_view').id, 'tree']],
            'context': self.env.context,
            'domain': [('id', 'in', self.summary_out_serial_ids.mapped("id"))]
        }

    @api.multi
    def _compute_lot_produced(self):
        for item in self:
            if len(item.production_finished_move_line_ids) > 1:
                item.lot_produced_id = item.production_finished_move_line_ids.filtered(
                    lambda a: a.product_id.id == item.product_id.id).lot_id.id
            item.lot_produced_id = item.final_lot_id.id

    @api.multi
    def compute_is_match(self):
        for item in self:
            item.is_match = item.production_id.routing_id.code == 'RO/00006'

    @api.multi
    def _compute_there_is_serial_without_pallet(self):
        for item in self:
            if item.summary_out_serial_ids:
                item.there_is_serial_without_pallet = len(item.summary_out_serial_ids.filtered(
                    lambda a: not a.pallet_id)) > 0

    @api.multi
    def _compute_manufacturing_pallet_ids(self):
        for item in self:
            if item.summary_out_serial_ids:
                pallet_ids = []
                for pallet_id in item.summary_out_serial_ids.mapped('pallet_id'):
                    if pallet_id.id not in pallet_ids:
                        pallet_ids.append(pallet_id.id)
                if pallet_ids:
                    item.manufacturing_pallet_ids = [(4, pallet_id) for pallet_id in pallet_ids]

    @api.onchange('qty_producing')
    def _onchange_qty_producing(self):
        print('se inhabilita este método')

    @api.multi
    def _compute_summary_out_serial_ids(self):
        for item in self:
            if item.final_lot_id:
                item.summary_out_serial_ids = item.final_lot_id.stock_production_lot_serial_ids
                if item.byproduct_move_line_ids:
                    item.summary_out_serial_ids += item.byproduct_move_line_ids.filtered(
                        lambda a: a.lot_id not in item.potential_serial_planned_ids.mapped(
                            'stock_production_lot_id')).mapped(
                        'lot_id'
                    ).mapped(
                        'stock_production_lot_serial_ids'
                    )
            else:
                item.summary_out_serial_ids = item.production_finished_move_line_ids.filtered(
                    lambda a: a.lot_id not in item.potential_serial_planned_ids.mapped(
                        'stock_production_lot_id')).mapped(
                    'lot_id'
                ).mapped(
                    'stock_production_lot_serial_ids'
                )

    @api.multi
    def _compute_byproduct_move_line_ids(self):
        for item in self:
            if not item.byproduct_move_line_ids:
                item.byproduct_move_line_ids = item.active_move_line_ids.filtered(lambda a: not a.is_raw and a.lot_id)

    @api.multi
    def _compute_material_product_ids(self):
        for item in self:
            if not item.material_product_ids:
                item.material_product_ids = item.production_id.move_raw_ids.mapped('product_id')

    @api.model
    def create(self, values_list):
        res = super(MrpWorkorder, self).create(values_list)

        name = self.env['ir.sequence'].next_by_code('mrp.workorder')

        final_lot = self.env['stock.production.lot'].create({
            'name': name,
            'product_id': res.product_id.id,
            'is_prd_lot': True,
            'can_add_serial': True,
            'label_durability_id': res.production_id.label_durability_id.id
        })
        res.final_lot_id = final_lot.id
        return res


    def open_tablet_view(self):
        for check in self.check_ids:
            if not check.component_is_byproduct:
                check.qty_done = 0
                self.action_skip()
            else:
                if not check.lot_id:
                    lot_tmp = self.env['stock.production.lot'].create({
                        'name': self.env['ir.sequence'].next_by_code('mrp.workorder'),
                        'product_id': check.component_id.id,
                        'is_prd_lot': True
                    })
                    check.lot_id = lot_tmp.id
                    check.qty_done = self.component_remaining_qty
                    self.active_move_line_ids.filtered(lambda a: a.lot_id.id == lot_tmp.id).write({
                        'is_raw': False
                    })
                    if check.quality_state == 'none' and check.qty_done > 0:
                        self.action_next()
        self.action_first_skipped_step()
        return super(MrpWorkorder, self).open_tablet_view()

    def new_screen_in(self):
        for check in self.check_ids:
            if not check.component_is_byproduct:
                check.qty_done = 0
                self.action_skip()
            else:
                if not check.lot_id:
                    lot_tmp = self.env['stock.production.lot'].create({
                        'name': self.env['ir.sequence'].next_by_code('mrp.workorder'),
                        'product_id': check.component_id.id,
                        'is_prd_lot': True
                    })
                    check.lot_id = lot_tmp.id
                    check.qty_done = self.component_remaining_qty
                    self.active_move_line_ids.filtered(lambda a: a.lot_id.id == lot_tmp.id).write({
                        'is_raw': False
                    })
                    if check.quality_state == 'none' and check.qty_done > 0:
                        self.action_next()
                else:
                    self.active_move_line_ids.filtered(lambda a: a.lot_id.id == check.lot_id.id).write({
                        'is_raw': False
                    })
        self.action_first_skipped_step()
        self.sudo().write({
            'in_weight': sum(self.potential_serial_planned_ids.mapped('display_weight'))
        })
        return {
            'name': "Procesar Entrada",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mrp.workorder',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {'form_view_initial_mode': 'edit', 'force_detailed_view': 'true'},
            'views': [
                [self.env.ref('dimabe_manufacturing.mrp_workorder_process_view').id, 'form']],
            'res_id': self.id,
        }

    def do_finish(self):
        self.write({
            'lot_produced_id': self.final_lot_id.id
        })
        if self.production_id.move_raw_ids.filtered(lambda a: not a.product_uom):
            raise models.ValidationError(
                '{}'.format(self.production_id.move_raw_ids.filtered(lambda a: not a.product_uom)))
        self.organize_move_line()
        return super(MrpWorkorder, self).do_finish()

    def action_skip(self):
        self.write({
            'in_weight': sum(self.potential_serial_planned_ids.mapped('real_weight'))
        })
        super(MrpWorkorder, self).action_skip()

    def action_ignore(self):
        for move in self.active_move_line_ids:
            if not move.lot_id:
                move.unlink()
        self.action_skip()
        for skip in self.skipped_check_ids:
            skip.unlink()

    def confirmed_keyboard(self):
        self.process_serial(serial_number=self.confirmed_serial)

    def process_serial(self, serial_number):
        serial_number = serial_number.strip()
        dict_write = {}
        serial = self.env['stock.production.lot.serial'].sudo().search(
            [('serial_number', '=', serial_number), ('stock_production_lot_id', '!=', False)])
        if not serial:
            raise models.ValidationError("La serie ingresada no existe")
        if serial.product_id not in self.material_product_ids:
            raise models.ValidationError(
                "La serie ingresada no es compatible con la lista de material de la produccion")
        if serial.consumed:
            raise models.ValidationError(
                "La serie ya fue consumida en el proceso {}".format(serial.reserved_to_production_id.name))
        dict_write['lot_id'] = serial.stock_production_lot_id.id
        serial.write({
            'reserved_to_production_id': self.production_id.id,
            'consumed': True,
            'used_in_workorder_id': self.id,
        })
        if serial.producer_id not in self.producers_id:
            dict_write['producers_id'] = [(4, serial.producer_id.id)]
        line_new = self.env['stock.move.line']
        line = self.env['stock.move.line']
        move = self.production_id.move_raw_ids.filtered(lambda x: x.product_id.id == serial.product_id.id)
        if move.active_move_line_ids:
            line = move.active_move_line_ids.filtered(lambda a: a.lot_id == serial.stock_production_lot_id)
            if not line.lot_produced_id:
                line.write({
                    'lot_produced_id': self.final_lot_id.id
                })
            line.write({
                'qty_done': sum(serial.display_weight for serial in self.potential_serial_planned_ids.filtered(
                    lambda x: x.stock_production_lot_id.id == serial.stock_production_lot_id.id))
            })
        else:
            line_new = self.env['stock.move.line'].sudo().create({
                'lot_id': serial.stock_production_lot_id.id,
                'lot_produced_id': self.final_lot_id.id,
                'product_id': move.product_id.id,
                'location_dest_id': self.env['stock.location'].search([('usage', '=', 'production')]).id,
                'location_id': self.production_id.location_src_id.id,
                'move_id': move.id,
                'product_uom_id': serial.product_id.uom_id.id,
                'date': date.today(),
                'qty_done': sum(self.potential_serial_planned_ids.filtered(
                    lambda a: a.stock_production_lot_id.id == serial.stock_production_lot_id.id).mapped(
                    'display_weight')),
                'production_id': self.production_id.id,
                'workorder_id': self.id,
                'is_raw': True
            })
        check = self.check_ids.filtered(
            lambda a: a.component_id.id == serial.product_id.id and not a.component_is_byproduct)
        check.write({
            'lot_id': serial.stock_production_lot_id.id,
            'move_line_id': line_new.id if line_new.id else line.id,
            'qty_done': sum(
                self.potential_serial_planned_ids.filtered(lambda a: a.product_id.id == serial.product_id.id).mapped(
                    'display_weight'))
        })
        if check.quality_state != 'pass':
            check.do_pass()
        dict_write['confirmed_serial'] = None
        dict_write['current_quality_check_id'] = check.id
        dict_write['in_weight'] = sum(serial.display_weight for serial in self.potential_serial_planned_ids)
        if self.start_date:
            dict_write['start_date'] = fields.Datetime.now()
        self.write(dict_write)

    @api.multi
    def validate_to_done(self):
        for check in self.check_ids.filtered(
                lambda a: a.quality_state != 'pass' or not a.lot_id):
            check.unlink()
        for move in self.active_move_line_ids.filtered(lambda a: not a.lot_id):
            move.unlink()
        self.write({
            'to_done': True
        })

    @api.model
    def lot_is_byproduct(self):
        return self.finished_product_check_ids.filtered(
            lambda a: a.lot_id == self.lot_id and a.component_is_byproduct
        )

    def validate_serial_code(self, barcode):
        custom_serial = self.env['stock.production.lot.serial'].search(
            [('serial_number', '=', barcode)])
        if custom_serial:
            if custom_serial.product_id != self.component_id:
                raise models.ValidationError('El producto ingresado no corresponde al producto solicitado')
            if custom_serial.consumed:
                raise models.ValidationError('este código ya ha sido consumido en la produccion {}'.format(
                    custom_serial.reserved_to_production_id.name))
            return custom_serial
        return custom_serial

    def open_out_form_view(self):
        for item in self:
            item.write({
                'out_weight': sum(item.summary_out_serial_ids.mapped('real_weight')),
                'pt_out_weight': sum(
                    item.summary_out_serial_ids.filtered(lambda a: a.product_id.id == self.product_id.id).mapped(
                        'real_weight'))
            })
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'mrp.workorder',
                'views': [[self.env.ref('dimabe_manufacturing.mrp_workorder_out_form_view').id, 'form']],
                'res_id': self.id,
                'target': 'fullscreen',
                'context': {'default_producers_id': item.producers_id}
            }

    def create_pallet(self):
        default_product_id = None
        if 'default_product_id' in self.env.context:
            default_product_id = self.env.context['default_product_id']
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'manufacturing.pallet',
            'views': [[self.env.ref('dimabe_manufacturing.manufacturing_pallet_form_view').id, 'form']],
            'target': 'fullscreen',
            'context': {'_default_product_id': default_product_id}
        }

    def update_inventory(self, lot_name):
        lot = self.env['stock.production.lot'].search([('name', '=', lot_name)])
        lot.write({
            'available_kg': sum(lot.stock_production_lot_serial_ids.mapped('real_weight'))
        })
        self.write({
            'in_weight': sum(self.potential_serial_planned_ids.mapped('real_weight'))
        })
        quant = self.env['stock.quant'].search([('lot_id', '=', lot.id)])
        quant.write({
            'quantity': sum(lot.stock_production_lot_serial_ids.mapped('real_weight'))
        })

