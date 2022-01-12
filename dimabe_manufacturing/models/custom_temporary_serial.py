from odoo import models, fields, api
from odoo.addons import decimal_precision as dp


class CustomTemporarySerial(models.Model):
    _name = 'custom.temporary.serial'

    name = fields.Char('N° Serie')

    product_id = fields.Many2one('product.product', 'Producto')

    lot_id = fields.Many2one('stock.production.lot', 'Lote')

    producer_id = fields.Many2one('res.partner')

    packaging_date = fields.Date('Fecha Produccion', default=fields.Date.today())

    best_before_date = fields.Date('Consumir antes de')

    harvest = fields.Integer('Año de Cosecha')

    canning_id = fields.Many2one('product.product', 'Envase')

    net_weight = fields.Float('Peso Neto', digits=dp.get_precision('Product Unit of Measure'))

    gross_weight = fields.Float('Peso Bruto', digits=dp.get_precision('Product Unit of Measure'))

    label_durability_id = fields.Many2one('label.durability', 'Durabilidad Etiqueta')

    production_id = fields.Many2one('mrp.production')

