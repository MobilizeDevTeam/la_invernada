from odoo import fields, models, api, _
from odoo.addons import decimal_precision as dp
from datetime import datetime
from ..helpers import date_helper


class OvenUse(models.Model):
    _name = 'oven.use'
    _description = 'datos de uso de los hornos'

    ready_to_close = fields.Boolean('Listo para Cerrar')

    name = fields.Char(
        'Horno en uso',
        compute='_compute_name'
    )

    done = fields.Boolean('Listo')

    init_date = fields.Datetime('Inicio de Proceso')

    finish_date = fields.Datetime('Termino de Proceso')

    active_seconds = fields.Integer('Tiempo Transcurrido')

    active_time = fields.Char(
        'Tiempo Transcurrido',
        compute='_compute_active_time',
        store=True
    )

    used_lot_id = fields.Many2one(
        'stock.production.lot',
        'Lote a Secar',
        required=True
    )

    lot_producer_id = fields.Many2one(
        'res.partner',
        related='used_lot_id.producer_id'
    )

    lot_guide_number = fields.Integer(
        'N° Guía',
        related='used_lot_id.reception_guide_number'
    )

    lot_variety = fields.Char(
        'Variedad',
        related='used_lot_id.product_variety'
    )

    lot_picking_type_id = fields.Many2one(
        'stock.picking.type',
        related='used_lot_id.picking_type_id'
    )

    init_active_time = fields.Integer('Inicio de tiempo activo')

    finish_active_time = fields.Integer('Fin de tiempo activo')

    dried_oven_id = fields.Many2one(
        'dried.oven',
        string='Horno',
        domain=[('state', '=', 'free')],
        required=True
    )

    dried_oven_ids = fields.Many2many(
        'dried.oven',
        string='Hornos',
        required=True
    )

    unpelled_dried_id = fields.Many2one('unpelled.dried', 'Proceso de secado')

    history_id = fields.Many2one('dried.unpelled.history', 'Historial')

    out_lot_id = fields.Many2one(
        'stock.production.lot',
        related='history_id.out_lot_id'
    )

    out_lot_serial_count = fields.Integer(
        'Cantidad Envases',
        related='history_id.out_serial_count'
    )

    reception_net_weight = fields.Float(
        'Kg Entrada',
        related='used_lot_id.reception_net_weight',
        digits=dp.get_precision('Product Unit of Measure')

    )

    total_out_weight = fields.Float(
        'Kg Salida',
        related='history_id.total_out_weight',
        digits=dp.get_precision('Product Unit of Measure')
    )

    performance = fields.Float(
        'Rendimiento',
        related='history_id.performance',
        digits=dp.get_precision('Product Unit of Measure')
    )

    stock_picking_id = fields.Many2one(
        'stock.picking',
        related='used_lot_id.stock_picking_id',
        string='Lote'
    )

    state = fields.Selection(
        string='Estado',
        selection=[('draft', 'Borrador'), ('pause', 'en Pausa'),
                   ('in_process', 'En Proceso'), ('cancel', 'Cancelado'), ('done', 'Finalizado')],
        default=lambda self: 'draft' if not self.finish_date else 'done')

    lot_locked = fields.Boolean(string='Lote Bloqueado', related='used_lot_id.is_unpelled_locked')

    used_lot_ids = fields.Many2many('stock.production.lot', compute='compute_used_lot_ids')

    @api.multi
    def compute_used_lot_ids(self):
        for item in self:
            item.used_lot_ids = item.unpelled_dried_id.in_lot_ids

    @api.multi
    def do_lot_locked(self):
        for item in self:
            item.used_lot_id.write({
                'is_unpelled_locked': True
            })

    @api.multi
    @api.onchange('dried_oven_id')
    def onchange_oven(self):
        res = {
            "domain": {
                "dried_oven_id": [
                    ('id', 'not in', self.unpelled_dried_id.oven_use_ids.mapped('dried_oven_id').ids),
                    ('state', '=', 'free'),
                    ('is_in_use', '=', False)],
                'used_lot_id': [
                    ('id', 'not in', self.env['oven.use'].search(
                        [('unpelled_dried_id', '!=', self.unpelled_dried_id.id)]).mapped(
                        'used_lot_id').ids),
                    ('producer_id', '=', self.unpelled_dried_id.producer_id.id),
                    ('product_id', '=', self.unpelled_dried_id.product_in_id.id),
                    ('balance', '>', 0),
                ]
            }
        }
        return res

    @api.multi
    def _compute_name(self):
        for item in self:
            if len(item.dried_oven_ids) > 0:
                tmp = ''
                for name in item.dried_oven_ids.mapped('name'):
                    tmp += '{} '.format(name)
                item.name = tmp
            else:
                item.name = item.dried_oven_id.name

    @api.multi
    @api.depends('active_seconds')
    def _compute_active_time(self):
        for item in self:
            item.active_time = date_helper.int_to_time(item.active_seconds)

    @api.multi
    def unlink(self):
        if self.env.user in self.env.ref('dimabe_manufacturing.oven_manger').users:
            self.mapped('dried_oven_ids').write({
                'is_in_use': False
            })
            unpelled_dried = self.env['unpelled.dried'].search([('id', '=', self.unpelled_dried_id.id)])
            res = super(OvenUse, self).unlink()
            print(unpelled_dried)
            return res
        else:
            raise models.ValidationError(
                'Su usuario no cuenta con los permisos para eliminar horno de este proceso , ponerse en contacto con la persona a cargo')

    @api.multi
    def init_process(self):
        for item in self:
            item.write({
                'state': 'in_process'
            })
            if item.init_date:
                raise models.ValidationError('este proceso ya ha sido iniciado')
            if not item.dried_oven_id:
                raise models.ValidationError('Debe seleccionar el horno a iniciar')
            if not item.used_lot_id:
                raise models.ValidationError('Debe Seleccionar un lote a secar')
            item.init_date = datetime.utcnow()
            item.init_active_time = item.init_date.timestamp()
            item.unpelled_dried_id.state = 'progress'
            item.dried_oven_id.write({
                'state': 'in_use',
                'is_in_use': True
            })
            item.used_lot_id.unpelled_state = 'drying'

    @api.multi
    def cancel_process(self):
        for item in self:
            if item.state == 'done':
                raise models.ValidationError('Este proceso ya ha finalizado')
            item.write({
                'state': 'cancel',
            })
            item.dried_oven_id.write({
                'is_in_use': True
            })
            item.used_lot_id.write({
                'unpelled_state': 'waiting'
            })

    @api.multi
    def pause_process(self):
        for item in self:
            item.write({
                'state': 'pause'
            })
            item.finish_active_time = datetime.utcnow().timestamp()
            item.active_seconds += item.finish_active_time - item.init_active_time

    @api.multi
    def resume_process(self):
        for item in self:
            item.write({
                'state': 'in_process'
            })
            item.init_active_time = datetime.utcnow().timestamp()
            item.finish_active_time = 0

    @api.multi
    def finish_process(self):
        for item in self:
            item.write({
                'state': 'done'
            })
            if item.used_lot_id and item.used_lot_id.reception_state != 'done':
                raise models.ValidationError(
                    'la recepción del lote {} no se encuentra en estado realizado. '
                    'Primero termine el proceso de recepción'.format(item.used_lot_id.name))
            item.finish_date = datetime.utcnow()
            if item.finish_active_time == 0:
                item.finish_active_time = item.finish_date.timestamp()
                item.active_seconds += item.finish_active_time - item.init_active_time
            item.used_lot_id.write({
                'unpelled_state': 'done'
            })
            item.dried_oven_id.write({
                'is_in_use': False
            })
            item.unpelled_dried_id.write({
                'can_close': True
            })

    @api.multi
    def print_oven_label(self):
        for item in self:
            return self.env.ref('dimabe_manufacturing.action_oven_use_label_report') \
                .report_action(item)

    @api.multi
    def get_full_url(self):
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        return base_url

    @api.multi
    def unlink(self):
        for item in self:
            if item.state == 'done':
                raise models.UserError('No se puede eliminar un registro si el horno esta finalizado')
            item.dried_oven_id.write({
                'is_in_use': False
            })
            item.used_lot_id.write({
                'unpelled_state': 'draft'
            })
            res = super(OvenUse, self).unlink()
            print(self.unpelled_dried_id.oven_use_ids)
            return res

    @api.multi
    def create(self, values):
        res = super(OvenUse, self).create(values)
        for r in res:
            r.dried_oven_id.write({
                'state': 'waiting'
            })
            r.used_lot_id.write({
                'unpelled_state': 'waiting'
            })
        return res
