from odoo import fields, models


class CustomPort(models.Model):
    _name = 'custom.port'
    _description = "Puerto"

    name = fields.Char(string= 'Nombre', required=True)

    code = fields.Char(string='Código', required=True)

    country_id = fields.Many2one(comodel_name='res.country', string='País')

