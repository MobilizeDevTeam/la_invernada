from odoo import models, fields


class CustomShip(models.Model):
    _name = 'custom.ship'
    _description = "Nave"

    name = fields.Char(string='Nave', required=True)