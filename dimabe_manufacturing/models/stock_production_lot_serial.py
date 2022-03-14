from odoo import fields, models, api
from dateutil.relativedelta import relativedelta
from odoo.addons import decimal_precision as dp
import math


class StockProductionLotSerial(models.Model):
    _inherit = 'stock.production.lot.serial'

   # _sql_constraints = [
   #     ('serial_uniq', 'UNIQUE(serial_number)', 'la serie ya se encuentra en el sistema.')
   # ]

    production_id = fields.Many2one(
        'mrp.production',
        'Salida'
    )

    producer_id = fields.Many2one(
        'res.partner',
        'Productor'
    )

    product_variety = fields.Char(
        'Variedad',
        related='stock_production_lot_id.product_variety'
        , store=True
    )

    product_id = fields.Many2one(
        'product.product',
        string='Producto'
    )

    belongs_to_prd_lot = fields.Boolean(
        'pertenece a lote productivo',
        related='stock_production_lot_id.is_prd_lot'
    )

    reserved_to_production_id = fields.Many2one(
        'mrp.production',
        'Entrada',
        nullable=True
    )

    consumed_in_production_id = fields.Many2one(
        'mrp.production',
        'Consumida en la produccion',
        nullable=True
    )

    stock_product_id = fields.Many2one(
        'product.product',
        related='stock_production_lot_id.product_id',
        string='Producto del Lote'
    )

    reserved_to_stock_picking_id = fields.Many2one(
        'stock.picking',
        'Para Picking',
        nullable=True
    )

    validate_to_stock_picking_id = fields.Many2one(
        'stock.picking',
        'Validado',
        nullable=True
    )

    is_dried_serial = fields.Boolean(
        'Es Serie Secada',
        related='stock_production_lot_id.is_dried_lot'
    )

    consumed = fields.Boolean('Consumido')

    confirmed_serial = fields.Char('Confimación de Serie')

    pallet_id = fields.Many2one(
        'manufacturing.pallet',
        'Pallet'
    )

    packaging_date = fields.Date(
        'Fecha Producción',
        default=fields.Date.today()
    )

    best_before_date = fields.Date(
        'Consumir antes de',
        compute='_compute_best_before_date'
    )

    harvest = fields.Integer(
        'Año de Cosecha',
        compute='_compute_harvest'
    )

    harvest_filter = fields.Integer(
        'Año de Cosecha Serie',
        compute='_compute_harvest_filter',
        store=True
    )

    canning_id = fields.Many2one(
        'product.product',
        'Envase',
        inverse='_inverse_gross_weight'
    )

    gross_weight = fields.Float(
        'Peso Bruto',
        digits=dp.get_precision('Product Unit of Measure'),
        inverse='_inverse_gross_weight'
    )

    label_durability_id = fields.Many2one(
        'label.durability',
        'Durabilidad Etiqueta'
    )

    label_percent = fields.Float(
        '% Peso Etiqueta',
        digits=dp.get_precision('Product Unit of Measure'),
        compute='_compute_label_percent'
    )

    bom_id = fields.Many2one(
        'mrp.bom',
        'Lista de Materiales',
        related='production_id.bom_id'
    )

    to_add = fields.Boolean('Agregar')

    to_delete = fields.Boolean('Desreservar')

    movement = fields.Char('Movimiento', compute='_compute_movement')

    in_weight = fields.Float('Kilos Ingresado', compute='_compute_in_weight')

    produce_weight = fields.Float('Kilos Producidos', compute='_compute_produce_weight')

    pallet_name = fields.Char('Folio Pallet', compute='_compute_pallet_name')

    sale_order_id = fields.Many2one('sale.order', 'N° Pedido', compute='_compute_sale_order_id', store=True)

    work_order_id = fields.Many2one('mrp.workorder', 'Order Fabricacion', compute='_compute_workorder_id')

    used_in_workorder_id = fields.Many2one('mrp.workorder', 'Usado en Orden de Trabajo')

    production_id_to_view = fields.Many2one('mrp.production', 'Order de Fabricacion',
                                            compute='_compute_production_id_to_view', store=True)
    workcenter_id = fields.Many2one('mrp.workcenter', related="work_order_id.workcenter_id")

    workcenter_send_id = fields.Many2one('mrp.workcenter', string='Enviado a proceso:')

    client_or_quality = fields.Text('Cliente o Calidad')

    physical_location = fields.Text('Ubicacion Fisica')

    observations = fields.Text('Observaciones')

    product_caliber = fields.Char('Calibre', compute='compute_product_caliber')

    location_id = fields.Many2one('stock.location', related='stock_production_lot_id.location_id')

    delivered_date = fields.Date('Fecha de envio a:')

    available_weight = fields.Float('Kilos disponibles', compute="compute_available_weight")

    to_unlink = fields.Boolean('Para Eliminar')

    best_before_date_new = fields.Date(string='Consumir antes de (Nueva)')

    to_print = fields.Boolean(string='Imprimir')

    printed = fields.Boolean(string='Impresa')

    @api.multi
    def compute_available_weight(self):
        for item in self:
            if item.consumed:
                item.available_weight = 0
            else:
                item.available_weight = item.display_weight

    @api.multi
    def compute_product_caliber(self):
        for item in self:
            item.product_caliber = item.product_id.get_calibers()

    @api.depends('production_id', 'reserved_to_production_id')
    @api.multi
    def _compute_production_id_to_view(self):
        for item in self:
            if item.reserved_to_production_id:
                item.production_id_to_view = item.reserved_to_production_id
            elif item.production_id:
                item.production_id_to_view = item.production_id
            else:
                item.production_id_to_view = None

    @api.multi
    def _compute_workorder_id(self):
        for item in self:
            if item.reserved_to_production_id:
                item.work_order_id = self.env['mrp.workorder'].search(
                    [('production_id', '=', item.reserved_to_production_id.id)])
            elif item.production_id:
                item.work_order_id = self.env['mrp.workorder'].search(
                    [('production_id', '=', item.production_id.id)])
            else:
                item.work_order_id = None

    @api.depends('production_id', 'reserved_to_production_id')
    @api.multi
    def _compute_sale_order_id(self):
        for item in self:
            if item.reserved_to_production_id:
                item.sale_order_id = item.reserved_to_production_id.sale_order_id
            elif item.production_id:
                item.sale_order_id = item.production_id.sale_order_id
            else:
                item.sale_order_id = None

    @api.multi
    def _compute_pallet_name(self):
        for item in self:
            if item.stock_production_lot_id.product_id.is_standard_weight:
                if item.pallet_id:
                    item.pallet_name = item.pallet_id.name
                else:
                    item.pallet_name = 'Sin Pallet'

    @api.multi
    def _compute_produce_weight(self):
        for item in self:
            if item.production_id:
                item.produce_weight = item.real_weight
                item.in_weight = 0.0
            else:
                item.produce_weight = 0.0

    @api.multi
    def _compute_in_weight(self):
        for item in self:
            if item.reserved_to_production_id:
                item.in_weight = item.real_weight
                item.produce_weight = 0.0
            else:
                item.in_weight = 0.0

    @api.multi
    def undo_consumed(self):
        for item in self:
            item.write({
                'reserved_to_production_id': None,
                'consumed': False
            })
            item.stock_production_lot_id.write({
                'available_kg': sum(
                    item.stock_production_lot_id.filtered(lambda a: not a.consumed).mapped('real_weight'))
            })

    @api.depends('reserved_to_production_id', 'production_id')
    @api.multi
    def _compute_process_id(self):
        for item in self:
            if item.reserved_to_production_id:
                item.process_id = item.reserved_to_production_id.routing_id.name
            elif item.production_id:
                item.process_id = item.production_id.routing_id.name
            else:
                item.process_id = None

    @api.depends('reserved_to_production_id', 'production_id')
    @api.multi
    def _compute_movement(self):
        for item in self:
            if item.reserved_to_production_id and not item.production_id:
                item.movement = 'ENTRADA'
            elif item.production_id and not item.reserved_to_production_id:
                item.movement = 'SALIDA'
            else:
                item.movement = 'NO DEFINIDO'

    @api.multi
    def _inverse_real_weight(self):
        for item in self:
            item.real_weight = item.display_weight
            if not item.is_dried_serial:
                canning_weight = item.canning_id.weight
                if not canning_weight:
                    canning_weight = sum(item.get_possible_canning_id().mapped('weight'))
                item.gross_weight = item.display_weight + canning_weight

    def _inverse_gross_weight(self):
        if self.is_dried_serial:
            gross_weight_without_canning = self.gross_weight - self.canning_id.weight
            self.display_weight = gross_weight_without_canning - (gross_weight_without_canning * self.label_percent)

    @api.multi
    def _compute_label_percent(self):
        for item in self:
            settings_percent = float(self.env['ir.config_parameter'].sudo().get_param(
                'dimabe_manufacturing.label_percent_subtract'
            ))

            if settings_percent:
                item.label_percent = settings_percent / 100

    @api.multi
    def _compute_harvest(self):
        for item in self:
            item.harvest = item.packaging_date.year

    @api.multi
    @api.depends('packaging_date')
    def _compute_harvest_filter(self):
        for item in self:
            item.harvest_filter = item.packaging_date.year

    @api.multi
    def _compute_best_before_date(self):
        for item in self:
            months = item.label_durability_id.month_qty
            item.best_before_date = item.packaging_date + relativedelta(months=months)


    @api.model
    def create(self, values_list):
        if 'is_pallet' not in self.env.context.keys():
            if 'stock_production_lot_id' in values_list.keys():
                lot = self.env['stock.production.lot'].search([('id', '=', values_list['stock_production_lot_id'])])
                values_list['product_id'] = lot.product_id.id
            if ('stock_production_lot_id', 'producer_id') in values_list.keys():
                lot = self.env['stock.production.lot'].search([('id', '=', values_list['stock_production_lot_id'])])
                if not lot.producer_id:
                    lot.write({
                        'producer_id': values_list['producer_id']
                    })
                workorder = self.env['mrp.workorder'].search([('production_id.id', '=', values_list['production_id'])])
                if not lot.label_durability_id:
                    lot.write({
                        'label_durability_id': workorder.label_durability_id.id
                    })
                    values_list['label_durability_id'] = workorder.production_id.label_durability_id.id
                workorder.write({
                    'out_weight': sum(lot.stock_production_lot_serial_ids.mapped('display_weight'))
                })
            res = super(StockProductionLotSerial, self).create(values_list)
            if res.display_weight == 0 and res.gross_weight == 0:
                raise models.ValidationError('debe agregar un peso a la serie')
    
            stock_move_line = self.env['stock.move.line'].search([
                ('lot_id', '=', res.stock_production_lot_id.id),
                ('lot_id.is_prd_lot', '=', True)
            ])
            if res.stock_production_lot_id.best_before_date:
                res.best_before_date_new = res.stock_production_lot_id.best_before_date
            if res.stock_production_lot_id.packaging_date:
                res.packaging_date = res.stock_production_lot_id.packaging_date
            production = None
            if stock_move_line.mapped('move_id.production_id'):
                production = stock_move_line.mapped('move_id.production_id')[0]
                res.producer_id = res.stock_production_lot_id.producer_id.id
            else:
                work_order = self.env['mrp.workorder'].search([
                    ('final_lot_id', '!=', False),
                    ('final_lot_id', '=', res.stock_production_lot_id.id)
                ])
                work_order.sudo().write({
                    'out_weight': sum(
                            work_order.summary_out_serial_ids.mapped('display_weight')),
                        'pt_out_weight': sum(work_order.summary_out_serial_ids.filtered(
                            lambda a: a.product_id.categ_id.parent_id.name == 'Producto Terminado').mapped(
                            'display_weight'))
                })
                res.producer_id = res.stock_production_lot_id.producer_id.id
    
                if work_order.production_id:
                    production = work_order.production_id[0]
    
            if production:
                res.production_id = production.id
                res.reserve_to_stock_picking_id = production.stock_picking_id.id
                res.stock_production_lot_id.update_kg(res.stock_production_lot_id.id)
                res.stock_production_lot_id.write({
                    'label_durability_id': production.label_durability_id.id
                })
                res.stock_production_lot_id.get_and_update(res.product_id.id)
                res.stock_production_lot_id.update_kg(res.stock_production_lot_id.product_id.id)
            res.label_durability_id = res.stock_production_lot_id.label_durability_id
    
            if res.bom_id:
                if res.bom_id.product_id != res.product_id:
                    res.gross_weight = res.display_weight
                    return res
                res.set_bom_canning()
                if res.canning_id:
                    res.gross_weight = res.display_weight + res.canning_id.weight
                else:
                    res.gross_weight = res.display_weight + sum(res.get_possible_canning_id().mapped('weight'))
                res.stock_production_lot_id.get_and_update(res.product_id.id)
                res.stock_production_lot_id.update_kg(res.stock_production_lot_id.product_id.id)
        else:
            res = super(StockProductionLotSerial, self).create(values_list)
        return res

    @api.model
    def set_bom_canning(self):
        canning_id = self.get_possible_canning_id()
        if len(canning_id) == 1:
            self.canning_id = canning_id[0]

    @api.model
    def get_possible_canning_id(self):
        return self.bom_id.bom_line_ids.filtered(
            lambda a: 'envases' in str.lower(a.product_id.categ_id.name) or
                      'embalaje' in str.lower(a.product_id.categ_id.name)
                      or (
                              a.product_id.categ_id.parent_id and (
                              'envases' in str.lower(a.product_id.categ_id.parent_id.name) or
                              'embalaje' in str.lower(a.product_id.categ_id.parent_id.name))
                      )
        ).mapped('product_id')

    @api.multi
    def write(self, vals):
        res = super(StockProductionLotSerial, self).write(vals)
        for item in self:
            if item.display_weight == 0 and item.gross_weight == 0:
                raise models.ValidationError('debe agregar un peso a la serie')
            if not item.canning_id and item.bom_id:
                item.set_bom_canning()
            if 'consumed' in vals.keys():
                if vals['consumed']:
                    item.stock_production_lot_id.verify_without_lot()
                    item.stock_production_lot_id.update_kg(item.stock_production_lot_id.id)
        return res

    @api.model
    def unlink(self):
        for item in self:
            if item.consumed:
                raise models.ValidationError(
                    'este código {} ya fue consumido, no puede ser eliminado'.format(
                        self.serial_number
                    )

                )
            lot = self.env['stock.production.lot'].search([('id', '=', item.stock_production_lot_id.id)])
            lot.update_kg(lot.id)
            lot.get_and_update(lot.product_id.id)
            if item.production_id and item.production_id.state != 'done':
                production = self.env['mrp.production'].search([('id', '=', item.production_id.id)])
                workorder = self.env['mrp.workorder'].search([('production_id','=',item.production_id.id)])
                workorder.sudo().write({
                    'out_weight': sum(
                        workorder.summary_out_serial_ids.mapped('display_weight')),
                    'pt_out_weight': sum(workorder.summary_out_serial_ids.filtered(
                        lambda a: a.product_id.categ_id.parent_id.name == 'Producto Terminado').mapped(
                        'display_weight'))
                })
            res = super(StockProductionLotSerial, item).unlink()
            lot.update_kg(lot.id)
            lot.get_and_update(lot.product_id.id)
            return res

    @api.multi
    def delete(self):
        if self.stock_production_lot_id.serial_without_pallet_ids:
            for item in self.stock_production_lot_id.serial_without_pallet_ids:
                if item.id == self.id:
                    item.unlink()

    @api.multi
    def print_serial_label(self):
        if 'producer_id' in self.env.context:
            for item in self:
                item.producer_id = self.env.context['producer_id']
        if not self.printed:
            self.write({
                'printed': True
            })
            return self.env.ref(
                'dimabe_manufacturing.action_stock_production_lot_serial_label_report'
            ).report_action(self)
        else:
            wiz_id = self.env['confirm.re_print.serial'].create({
                'serial_id': self.id,
            })
            view_id = self.env.ref('dimabe_manufacturing.confirm_re_print_serial')
            return {
                'name': "Reimpresion de Etiqueta",
                'type': "ir.actions.act_window",
                'view_type': 'form',
                'view_model': 'form',
                'res_model': 'confirm.re_print.serial',
                'views': [(view_id.id, 'form')],
                'target': 'new',
                'res_id': wiz_id.id,
                'context': self.env.context
            }


    @api.multi
    def get_full_url(self):
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        return base_url

    @api.multi
    def reserve_picking(self):
        if 'dispatch_id' in self.env.context:
            stock_picking_id = self.env.context['dispatch_id']
            stock_picking = self.env['stock.picking'].search([('id', '=', stock_picking_id)])
            if not stock_picking:
                raise models.ValidationError('No se encontró el picking al que reservar el stock')

            for item in self:
                if item.consumed:
                    raise models.ValidationError('Esta serie fue consumida')
                item.update({
                    'reserved_to_stock_picking_id': stock_picking.id
                })
                stock_move = item.reserved_to_stock_picking_id.move_lines.filtered(
                    lambda a: a.product_id == item.stock_production_lot_id.product_id
                )
                stock_quant = item.stock_production_lot_id.get_stock_quant()
                if not stock_quant:
                    raise models.ValidationError('El lote {} aún se encuentra en proceso.'.format(
                        item.stock_production_lot_id.name
                    ))

                if not stock_move:
                    move_line = self.env['stock.move.line'].create({
                        'product_id': item.stock_production_lot_id.product_id.id,
                        'lot_id': item.stock_production_lot_id.id,
                        'qty_done': item.display_weight,
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

                    item.reserved_to_stock_picking_id.update({
                        'move_line_ids': [
                            (4, move_line.id)
                        ]
                    })

                    if stock_quant.total_reserved:
                        stock_quant.sudo().update({
                            'reserved_quantity': stock_quant.total_reserved
                        })
                    else:
                        stock_quant.sudo().update({
                            'reserved_quantity': sum(item.lot_id.stock_production_lot_serial_ids.filtered(
                                lambda a: (a.reserved_to_production_id and a.reserved_to_production_id.state not in [
                                    'done', 'cancel'])
                                          or (a.reserved_to_stock_picking_id and
                                              a.reserved_to_stock_picking_id.state not in ['done', 'cancel']
                                              )
                            ).mapped('display_weight'))
                        })


                else:
                    move_line = stock_move.move_line_ids.filtered(
                        lambda
                            a: a.product_id.id == item.stock_production_lot_id.product_id.id
                    )
                    if not move_line:
                        move_line = self.env['stock.move.line'].create({
                            'product_id': item.stock_production_lot_id.product_id.id,
                            'lot_id': item.stock_production_lot_id.id,
                            'qty_done': item.display_weight,
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

                        item.reserved_to_stock_picking_id.update({
                            'move_line_ids': [
                                (4, move_line.id)
                            ]
                        })
                    else:
                        picking_move_line = item.reserved_to_stock_picking_id.move_line_ids.filtered(
                            lambda a: a.id == move_line.id
                        )
                        stock_quant = item.stock_production_lot_id.get_stock_quant()
                        item.update({
                            'reserved_to_stock_picking_id': stock_picking_id
                        })

                        for ml in move_line:
                            product_uom_qty = ml.product_uom_qty
                            if ml.state == 'done':
                                raise models.ValidationError('este producto ya ha sido validado')

                            ml.update({'product_uom_qty': product_uom_qty + item.display_weight})
                            picking_move_line.filtered(lambda a: a.id == ml.id).update({
                                'product_uom_qty': ml.product_uom_qty
                            })
                    stock_quant.sudo().update({
                        'reserved_quantity': item.display_weight
                    })
        else:
            raise models.ValidationError('no se pudo identificar picking')

    @api.multi
    def unreserved_picking(self):
        for item in self:
            stock_move = item.reserved_to_stock_picking_id.move_lines.filtered(
                lambda a: a.product_id == item.stock_production_lot_id.product_id
            )

            move_line = stock_move.move_line_ids.filtered(
                lambda
                    a: a.lot_id.id == item.stock_production_lot_id.id
            )

            if len(move_line) > 1:
                for move in move_line:
                    picking_move_line = item.reserved_to_stock_picking_id.move_line_ids.filtered(
                        lambda a: a.id == move.id
                    )
                    stock_quant = item.stock_production_lot_id.get_stock_quant()

                    stock_quant.sudo().update({
                        'reserved_quantity': stock_quant.total_reserved
                    })

                    item.update({
                        'reserved_to_stock_picking_id': None
                    })

                    for ml in move:
                        if ml.qty_done > 0:
                            raise models.ValidationError('este producto ya ha sido validado')
                        ml.write({'move_id': None, 'product_uom_qty': 0})
                        picking_move_line.filtered(lambda a: a.id == ml.id).write({
                            'move_id': None,
                            'picking_id': None,
                            'product_uom_qty': 0
                        })
            else:
                picking_move_line = item.reserved_to_stock_picking_id.move_line_ids.filtered(
                    lambda a: a.id == move_line.id
                )

                stock_quant = item.stock_production_lot_id.get_stock_quant()
                item.update({
                    'reserved_to_stock_picking_id': None
                })

                for ml in move_line:
                    product_uom_qty = ml.product_uom_qty

                    if ml.qty_done > 0:
                        raise models.ValidationError('este producto ya ha sido validado')

                    ml.update({'product_uom_qty': product_uom_qty - item.display_weight})
                    picking_move_line.filtered(lambda a: a.id == ml.id).update({
                        'product_uom_qty': ml.product_uom_qty
                    })
                item.stock_production_lot_id.update({
                    'available_total_serial': item.stock_production_lot_id.available_total_serial - item.display_weight
                })

    @api.multi
    def remove_serial(self):
        if 'workorder_id' in self.env.context.keys():
            workorder_id = self.env.context['workorder_id']
            workorder = self.env['mrp.workorder'].search([('id', '=', workorder_id)])
            production = workorder.production_id
            self.sudo().write({
                'reserved_to_production_id': None,
                'consumed': False,
                'used_in_workorder_id': None
            })
            workorder.sudo().write({
                'in_weight': sum(workorder.potential_serial_planned_ids.mapped('display_weight'))
            })
            self.stock_production_lot_id.update_stock_quant(production.location_src_id.id)
            self.stock_production_lot_id.update_kg(self.stock_production_lot_id.id)
            move_line = self.env['stock.move.line'].search(
                [('workorder_id', '=', workorder_id), ('lot_id', '=', self.stock_production_lot_id.id),
                 ('location_dest_id.usage', '=', 'production')])
            for line in move_line:
                if (line.qty_done - self.display_weight) != 0:
                    line.write({
                        'qty_done': sum(workorder.potential_serial_planned_ids.mapped('display_weight'))
                    })
                else:
                    line.write({
                        'qty_done': 0
                    })
                    line.unlink()
