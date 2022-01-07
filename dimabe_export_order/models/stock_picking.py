from odoo import models, fields, api, tools
from datetime import datetime, timedelta
from PIL import Image
import io
import base64
import codecs
import math

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    delivery_date = fields.Datetime('Fecha de entrega')

    #shipping_number = fields.Integer('Número Embarque')
    shipping_number = fields.Char('Número Embarque')

    #Ya no se ocupa
    #shipping_id = fields.Many2one(
    #    'custom.shipment',
    #    'Embarque'
    #)

    #required_loading_date = fields.Datetime(
    #    related='shipping_id.required_loading_date')

    variety = fields.Many2many(related="product_id.attribute_value_ids")

    country = fields.Char(related='partner_id.country_id.name')

    quantity_done = fields.Float(
        related='move_ids_without_package.product_uom_qty')

    product = fields.Many2one(related="move_ids_without_package.product_id")

    contract_correlative = fields.Integer('corr')

    contract_correlative_view = fields.Char(
        'N° Orden',
        compute='_get_correlative_text'
    )

    commission = fields.Float('Comisión %')

    #   elapsed_time_dispatch = fields.Float(string="Hora de Camión en Planta")

    consignee_id = fields.Many2one(
        'res.partner',
        'Consignatario',
        domain=[('customer', '=', True)]
    )

    notify_ids = fields.Many2many(
        'res.partner',
        domain=[('customer', '=', True)]
    )

    custom_notify_ids = fields.Many2many('custom.notify', string="Notify")
 
    agent_id = fields.Many2one(
        'res.partner',
        'Agente',
        domain=[('is_agent', '=', True)]
    )

    total_commission = fields.Float(
        'Valor Comisión',
        compute='_compute_total_commission'
    )

    charging_mode = fields.Selection(
        [
            ('piso', 'A Piso'),
            ('slip_sheet', 'Slip Sheet'),
            ('palet', 'Paletizado')
        ],
        'Modo de Carga'
    )

    booking_number = fields.Char('N° Booking')

    bl_number = fields.Char('N° BL')

    client_label = fields.Boolean('Etiqueta Cliente', default=False)

    client_label_file = fields.Binary(string='Archivo Etiqueta Cliente')

    container_number = fields.Char('N° Contenedor')

    freight_value = fields.Float('Valor Flete')

    safe_value = fields.Float('Valor Seguro')

    total_value = fields.Float(
        'Valor Total',
        compute='_compute_total_value',
        store=True
    )

    value_per_kilogram = fields.Float(
        'Valor por kilo',
        compute='_compute_value_per_kilogram',
        store=True
    )

    remarks = fields.Text('Comentarios')

    container_type = fields.Many2one(
        'custom.container.type',
        'Tipo de contenedor'
    )

    net_weight_dispatch = fields.Float(
        string="Kilos Netos Despacho",
        copy=False
    )

    gross_weight_dispatch = fields.Float(
        string="Kilos Brutos",
        copy=False
    )

    tare_container_weight_dispatch = fields.Float(
        string="Tara Contenedor",
        copy=False
    )

    container_weight = fields.Float(
        string="Peso Contenedor",
        copy=False
    )

    vgm_weight_dispatch = fields.Float(
        string="Peso VGM",
        compute="compute_vgm_weight",
        store=True,
        copy=False
    )

    note_dispatched = fields.Many2one(
        'custom.note',
        copy=False
    )

    sell_truck = fields.Char(
        string="Sello Invernada",
        copy=False
    )

    dispatch_guide_number = fields.Char(
        string="Numero de Guia",
        copy=False
    )

    sell_sag = fields.Char(
        string="Sello SAG",
        copy=False
    )

    gps_lock = fields.Char(
        string="Candado GPS",
        copy=False
    )

    gps_button = fields.Char(
        string="Botón GPS",
        copy=False
    )

    dus_number = fields.Char(
        string="Numero DUS",
        copy=False
    )

    picture = fields.Many2many(
        "ir.attachment",
        string="Fotos Camión",
        copy=False
    )

    pictures = fields.Many2many(
        "ir.attachment",
        compute="get_pictures",
        readonly=False,
        store=True,
        string="Datos Fotos",
        copy=False
    )

    file = fields.Char(
        related="picture.datas_fname",
        copy=False
    )

    type_of_transfer_list = fields.Selection(
        [('1', 'Operacion constituye venta'),
         ('2', 'Ventas por efectuar'),
         ('3', 'Consignaciones'),
         ('4', 'Entrega gratuita'),
         ('5', 'Traslado internos'),
         ('6', 'Otros traslados no venta'),
         ('7', 'Guia de devolucion'),
         ('8', 'Traslado para exportación no venta'),
         ('9', 'Venta para exportacion')],
        string="Tipo de Traslado"
    )

    type_of_transfer = fields.Char(
        compute="get_type_of_transfer"
    )

    transport = fields.Char(
        string="Transporte"
    )

    type_of_dispatch = fields.Selection(
        [('exp', 'Exportación'),
         ('nac', 'Nacional')],
        string="Tipo de Despacho",
        copy=False)

    sell_shipping = fields.Char(
        string="Sello Naviera",
        copy=False
    )

    is_dispatcher = fields.Integer(
        compute="get_permision"
    )

    hour_arrival = fields.Float(
        string="Hora Llegada",
        copy=False
    )

    hour_departure = fields.Float(
        string="Hora Salida",
        copy=False
    )

    truck_in_date = fields.Datetime(
        string="Entrada Camión",
        readonly=False,
        copy=False
    )

    elapsed_time = fields.Char(
        'Horas Camión en planta',
        compute='_compute_elapsed_time',
        copy=False
    )

    have_picture_report = fields.Boolean('Tiene reporte de fotos', default=True)

    arrival_weight = fields.Float('Peso de Entrada',
        copy=False)

    departure_weight = fields.Float('Peso de Salida',
        copy=False)

    customs_department = fields.Many2one('res.partner', 'Oficina Aduanera',
        copy=False)

    canning_data = fields.Char('Agregar Envases',
        copy=False)

    @api.onchange('picture')
    def get_pictures(self):
        self.pictures = self.picture

    @api.multi
    def generate_packing_list(self):
        if not self.consignee_id:
            raise models.ValidationError('No tiene definido el consignatario')
        if not self.notify_ids:
            raise models.ValidationError('No tiene ninguna persona para notificar')
        if not self.dispatch_line_ids and not self.packing_list_file:
            return self.env.ref('dimabe_export_order.action_packing_list') \
                .report_action(self)
        else:
            file_name = 'Packing List.pdf'
            attachment_id = self.env['ir.attachment'].sudo().create({
                'name': file_name,
                'datas_fname': file_name,
                'datas': self.packing_list_file
            })

            action = {
                'type': 'ir.actions.act_url',
                'url': '/web/content/{}?download=true'.format(attachment_id.id, ),
                'target': 'current',
            }
            return action

    @api.multi
    def generate_inform(self):
        return self.env.ref('dimabe_export_order.action_inform') \
            .report_action(self)

    @api.multi
    def generate_report(self):
        self.pictures.set_pages()
        for page in self.pictures:
            print(f'Counter {page.counter} Page {page.page}')




    @api.multi
    def get_permision(self):
        for i in self.env.user.groups_id:
            if i.name == "Despachos":
                self.is_dispatcher = 1

    @api.multi
    def get_type_of_transfer(self):
        self.type_of_transfer = \
            dict(self._fields['type_of_transfer_list'].selection).get(self.type_of_transfer_list)
        return self.type_of_transfer

    @api.one
    @api.depends('tare_container_weight_dispatch', 'container_weight')
    def compute_vgm_weight(self):
        self.vgm_weight_dispatch = \
            self.tare_container_weight_dispatch + self.container_weight

    @api.one
    def compute_elapsed_time(self):
        if self.truck_in_date:
            if self.date_done:
                self.elapsed_time = self._get_hours(self.truck_in_date, self.date_done)
            else:
                self.elapsed_time = self._get_hours(self.truck_in_date, datetime.now())
        else:
            self.elapsed_time = '00:00:00'

    def _get_hours(self, init_date, finish_date):
        diff = str((finish_date - init_date))
        return diff.split('.')[0]

    @api.multi
    @api.depends('freight_value', 'safe_value')
    def _compute_total_value(self):   
        for item in self:
            list_price = []
            list_qty = []
            prices = 0
            qantas = 0
            for i in item.sale_id.order_line:
                if len(item.sale_id.order_line) != 0:
                    list_price.append(i.price_unit)

            #move_line = []
            #if item.is_multiple_dispatch:
            #    for line in item.dispatch_line_ids:
            #        if line.sale_id.id == item.sale_id.id:
            #            
            #            move_line.append(line)
            #    if len(move_line) != 0:
            #        for m in move_line:
             #           list_qty.append(m.real_dispatch_qty)
            #            prices = sum(list_price)
            #            qantas = sum(list_qty)
            #else:
                #move_line = item.move_ids_without_package

            if len(item.move_ids_without_package) != 0:
                for a in item.move_ids_without_package:    
                    list_qty.append(a.quantity_done)
                    prices = sum(list_price)
                    qantas = sum(list_qty)

            item.total_value = (prices * qantas) + item.freight_value + item.safe_value

    @api.multi
    @api.depends('total_value')
    def _compute_value_per_kilogram(self):
        for item in self:
            qty_total = 0
            #move_line = []
            #if item.is_multiple_dispatch:
            #    for line in item.dispatch_line_ids:
            #        if line.sale_id == item.sale_id:
            #            move_line.append(line)
            #    for line in move_line:
            #        qty_total = qty_total + line.real_dispatch_qty
            #    if qty_total > 0:
            #        item.value_per_kilogram = item.total_value / qty_total
            #else:
            for line in item.move_ids_without_package:
                qty_total = qty_total + line.quantity_done
            if qty_total > 0:
                item.value_per_kilogram = item.total_value / qty_total

    @api.onchange('commission')
    @api.multi
    def _compute_total_commission(self):
        for item in self:
            if item.agent_id and item.commission > 3:
                raise models.ValidationError('la comisión debe ser mayor que 0 y menor o igual que 3')
            else:
                sum_required_qty = 0
                #if item.is_multiple_dispatch:
                #    for line in item.dispatch_line_ids:
                #        if line.sale_id == item.sale_id:
                #            sum_required_qty += line.required_sale_qty
                #    item.total_commission = (item.commission / 100) \
                #                        * (sum(item.sale_id.order_line.mapped('price_unit'))
                #                           * sum_required_qty)
                #else:
                item.total_commission = (item.commission / 100) \
                                        * (sum(item.sale_id.order_line.mapped('price_unit'))
                                           * sum(item.move_ids_without_package.mapped('product_uom_qty')))

    @api.multi
    # @api.depends('contract_id')
    def _get_correlative_text(self):
        print('')
        # if self.contract_id:
        # if self.contract_correlative == 0:
        # existing = self.contract_id.sale_order_ids.search([('name', '=', self.name)])
        # if existing:
        # self.contract_correlative = existing.contract_correlative
        # if self.contract_correlative == 0:
        # self.contract_correlative = len(self.contract_id.sale_order_ids)
        # else:
        # self.contract_correlative = 0
        # if self.contract_id.name and self.contract_correlative and self.contract_id.container_number:
        # self.contract_correlative_view = '{}-{}/{}'.format(
        # self.contract_id.name,
        # self.contract_correlative,
        # self.contract_id.container_number
        # )
        # else:
        # self.contract_correlative_view = ''

    @api.constrains('commission')
    def _check_data_typed(self):
        for item in self:
            if item.agent_id and item.commission > 3:
                raise models.ValidationError('la comisión debe ser mayor que 0 y menor o igual que 3')

 
        