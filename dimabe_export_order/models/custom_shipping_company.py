from odoo import models, fields


class CustomShippingCompany(models.Model):

    _name = 'custom.shipping.company'
    _description = "Naviera"

    name = fields.Char(string='Naviera', required=True)