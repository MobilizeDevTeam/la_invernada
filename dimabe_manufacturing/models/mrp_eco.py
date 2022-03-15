from odoo import fields, models, api, _


class MrpEco(models.Model):
    _inherit = 'mrp.eco'

    type = fields.Selection(
        selection=[('product', 'Producto'), ('bom', 'Lista de Materiales'), ('routing', 'Ruta de produccion'),
                   ('variant', 'Variante'), ('both', 'LdM y Rutas')])

    product_id = fields.Many2one('product.product',string="Variante de Producto")

    @api.multi
    def action_generate_label(self):
        for item in self:
            view_id = self.env.ref('dimabe_manufacturing.generate_label_form_view')
            wiz_id = self.env['generate.label.wizard'].create({
                'eco_id': self.id
            })
            return {
                'name': "Generar Etiqueta",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'generate.label.wizard',
                'views': [(view_id.id, 'form')],
                'view_id': view_id.id,
                'target': 'new',
                'res_id': wiz_id.id,
                'context': self.env.context
            }
