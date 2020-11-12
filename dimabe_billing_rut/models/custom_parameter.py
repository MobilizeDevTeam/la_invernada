from odoo import models, fields


class CustomParameter(models.Models):
    _name = 'custom.parameter'

    name = fields.Char('Nombre')

    value = fields.Char('Valor')

    comment = fields.Char('Comentario')
