
from odoo import models, fields, api
import requests
import json


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    #To Intructuives

    temperature = fields.Char('Temperatura')

    ventilation = fields.Char('Ventilación')

    humidity = fields.Char('Humedad')

    withdrawal_deposit = fields.Many2one('custom.withdrawal.deposits',string="Depósito Retiro")

    freight_payment_term = fields.Many2one('custom.freight.payment.term',string="Termino de Pago Flete")

    safe_type = fields.Many2one('custom.safe.type',string="Tipo de Seguro")

    stacking = fields.Char(string="Stacking")

    cut_off = fields.Char(string="Cut Off")

    dus_second_send = fields.Char(string="D.U.S 2DO.ENVÍO")

    bill_of_lading = fields.Char(string="Conocimiento de Embarque")

    phytosanitary_certificate = fields.Char(string="Certificado Fitosanitario")

    origin_certificate = fields.Char(string="Certificado Origen")

    plant = fields.Many2one('res.partner', string="Planta")

    quality_type = fields.Many2one('custom.quality.type',string="Calidad")

    consolidation = fields.Char(string="Consolidación")

    total_container = fields.Integer(string="Total de Contenedores")

    notify_ids = fields.Many2many(
            'res.partner',
            domain=[('customer', '=', True)]
        )
    custom_notify_ids = fields.Many2many('custom.notify', string="Notify (Custom)")
    
    consignee_id = fields.Many2one(
        'res.partner',
        'Consignatario',
        domain=[('customer', '=', True)]
    )

    order_names = fields.Char(string="Pedidos", compute="_compute_order_ids")

    canning_types = fields.Char(string="Envases", compute="_compute_canning_types")

    #To order report 

    quality_status = fields.Selection([
                    ('Pendiente','Pendiente'),
                    ('Recibido','Recibido'),
                    ('Enviado','Enviado'),
                    ('Cancelado','Cancelado')
            ], string="Estado Calidad")

    quality_remarks = fields.Text(string="Obs. Calidad")

    shipping_date_to_customer = fields.Date(string="Fecha Envío al Cliente")

    port_terminal_origin = fields.Char(string="Terminal Portuario Origen")

    def _compute_order_ids(self):
        for item in self:
            orders = []
            for line in item.invoice_line_ids:
                if line.order_name and line.order_name not in orders:
                    orders.append(line.order_name)
            str_orders = ''
            for o in orders:
                str_orders += o + ' '
            item.order_names = str_orders
    
    
    def _compute_canning_types(self):
        for item in self:
            cannings = []
            for line in item.invoice_line_ids:
                for attr in line.mapped('product_id').mapped('attribute_value_ids'):
                    if attr.attribute_id.name == 'Tipo de envase':
                        if attr.name and attr.name not in cannings:
                            cannings.append(attr.name)
            str_cannings = ''
            for c in cannings:
                str_cannings += c + ' '
            item.canning_types = str_cannings


