from odoo import models, fields, api

class AccountInvoiceLine(models.Model):

    _inherit = 'account.invoice.line'

    exempt = fields.Selection([
            ("1", 'No afecto o exento de IVA'),
            ("2", 'Producto o servicio no es facturable'),
            ("3", 'Garantía de depósito por envases, autorizados por Resolución especial'),
            ("4", 'Item No Venta'),
            ("5", 'Item a rebajar'),
            ("6", 'Producto/Servicio no facturable negativo'),
            ])