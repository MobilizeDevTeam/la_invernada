from odoo import models, fields

class CustomContainerType(models.Model):

    _name = 'custom.container.type'
    _description = "Tipo de Contenedor"

    name = fields.Char(string='Tipo de Contenedor', required=True)