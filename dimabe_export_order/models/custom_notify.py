from odoo import models, fields


class CustomNotify(models.Model):
    _name = 'custom.notify'
    _description = "Notificacion (Custom)"

    partner_id = fields.Many2one('res.partner', domain=[('customer', '=', True)], string='Cliente', required=True)

    partner_name = fields.Char(string="Nombre de Cliente", related='partner_id.name')

    partner_identifier_type = fields.Char(string="Tipo de Identificador", related='partner_id.client_identifier_id.name')

    partner_identifier_value = fields.Char(string="Valor Identificador", related='partner_id.client_identifier_value')

    position = fields.Integer("Posición",nullable=True)