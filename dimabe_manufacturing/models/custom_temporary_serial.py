from odoo import models, fields, api
from odoo.addons import decimal_precision as dp


class CustomTemporarySerial(models.Model):
    _name = 'custom.temporary.serial'
    _description = "Series Temporales"

    name = fields.Char('N° Serie')

    product_id = fields.Many2one('product.product', 'Producto')

    lot_id = fields.Many2one('stock.production.lot', 'Lote')

    producer_id = fields.Many2one('res.partner', string='Productor')

    packaging_date = fields.Date('Fecha Produccion', default=fields.Date.today())

    best_before_date = fields.Date('Consumir antes de')

    harvest = fields.Integer('Año de Cosecha')

    canning_id = fields.Many2one('product.product', 'Envase')

    net_weight = fields.Float('Peso Neto', digits=dp.get_precision('Product Unit of Measure'))

    gross_weight = fields.Float('Peso Bruto', digits=dp.get_precision('Product Unit of Measure'))

    label_durability_id = fields.Many2one('label.durability', 'Durabilidad Etiqueta')

    production_id = fields.Many2one('mrp.production', string='Produccion')

    to_print = fields.Boolean('A Imprimir')

    printed = fields.Boolean('Impresa')

    @api.multi
    def do_print(self):
        if self.printed:
            wiz_id = self.env['confirm.re_print.temporary.serial'].create({
                'serial_id': self.id,
            })
            view_id = self.env.ref('dimabe_manufacturing.confirm_re_print_temporary_serial')
            return {
                'name': "Reimpresion de Etiqueta",
                'type': "ir.actions.act_window",
                'view_type': 'form',
                'view_model': 'form',
                'res_model': 'confirm.re_print.temporary.serial',
                'views': [(view_id.id, 'form')],
                'target': 'new',
                'res_id': wiz_id.id,
                'context': self.env.context
            }
        self.write({
            'printed': True
        })
        return self.env.ref(
            'dimabe_manufacturing.action_print_temporary_serial'
        ).report_action(self)

    @api.multi
    def get_full_url(self):
        for item in self:
            return self.env["ir.config_parameter"].sudo().get_param("web.base.url")

    def get_possible_canning_id(self, production_id):
        production_id = self.env['mrp.production'].search([('id', '=', production_id)])
        return production_id.bom_id.bom_line_ids.filtered(
            lambda a: 'envases' in str.lower(a.product_id.categ_id.name) or
                      'embalaje' in str.lower(a.product_id.categ_id.name)
                      or (
                              a.product_id.categ_id.parent_id and (
                              'envases' in str.lower(a.product_id.categ_id.parent_id.name) or
                              'embalaje' in str.lower(a.product_id.categ_id.parent_id.name))
                      )
        ).mapped('product_id')

    def create_serial(self, pallet_id):
        serials = []
        for item in self:
            serials.append({
                'serial_number': item.name,
                'product_id': item.product_id.id,
                'display_weight': item.net_weight,
                'belongs_to_prd_lot': True,
                'pallet_id': pallet_id,
                'producer_id': item.producer_id.id,
                'best_before_date_new': item.best_before_date,
                'packaging_date': item.packaging_date,
                'stock_production_lot_id': item.lot_id.id,
                'label_durability_id': item.label_durability_id.id,
                'production_id': item.production_id.id,
                'bom_id': item.production_id.bom_id.id,
            })
            item.unlink()
        self.env['stock.production.lot.serial'].create(serials)

