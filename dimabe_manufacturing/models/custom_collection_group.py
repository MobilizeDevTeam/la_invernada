from odoo import fields, models, api


class CustomCollectionGroup(models.Model):
    _name = 'custom.collection.group'

    name = fields.Char('Nombre Grupo')

    user_ids = fields.Many2many('res.users', string='Usuarios')

    group_id = fields.Many2one('res.groups', string='Grupo')

    @api.multi
    def write(self, values):
        res = super(CustomCollectionGroup, self).write(values)
        if 'user_ids' in values.keys():
            if 2 not in values['user_ids'][0][2]:
                values['user_ids'][0][2].append(2)
            self.group_id.write({
                'users': values['user_ids']
            })
        return res
