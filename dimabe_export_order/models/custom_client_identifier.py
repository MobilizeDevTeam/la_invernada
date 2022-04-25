from odoo import fields, models, api


class CustomClientIdentifier(models.Model):
    _name = 'custom.client.identifier'
    _description = "Identificador de Cliente"

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'el tipo de identificador ya se encuentra en el listado')
    ]

    name = fields.Char(
        'Identificador',
        required=True
    )

    @api.model
    def create(self, values_list):
        if values_list['name']:
            values_list['name'] = str.upper(values_list['name'])
        return super(CustomClientIdentifier, self).create(values_list)

    @api.multi
    def write(self, values):
        if values['name']:
            values['name'] = str.upper(values['name'])
        return super(CustomClientIdentifier, self).write(values)
