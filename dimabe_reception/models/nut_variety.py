from odoo import models, fields, api


def upper(name):
    return str.upper(name)


class NutVariety(models.Model):
    _name = 'nut.variety'
    _description = "Variedad de Nuez"

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'la variedad ya se encuentra en el sistema.')
    ]

    name = fields.Char('Variedad', required=True)

    @api.model
    def create(self, vals_list):
        if 'name' in vals_list:
            vals_list['name'] = upper(vals_list['name'])
        return super(NutVariety, self).create(vals_list)

    @api.multi
    def write(self, vals):
        if 'name' in vals:
            vals['name'] = upper(vals['name'])
        return super(NutVariety, self).write(vals)
