from odoo import fields, models, api
from dateutil.relativedelta import relativedelta


class WizardGenerateTemporarySerial(models.TransientModel):
    _name = 'wizard.generate.temporary.serial'
    _description = "Generador de Series Temporales"

    lot_id = fields.Many2one('stock.production.lot', 'Lote')

    production_id = fields.Many2one('mrp.production','Produccion')

    qty_to_generate = fields.Integer('Cantidad a generar')

    @api.multi
    def generate(self):
        counter = 1
        for serial in range(self.qty_to_generate):
            zeros = '00' if counter < 1000 else '0'
            self.env['custom.temporary.serial'].create({
                'product_id': self.lot_id.product_id.id,
                'producer_id': self.lot_id.producer_id.id,
                'lot_id': self.lot_id.id,
                'name': f'{self.lot_id.name}{zeros}{counter}',
                'best_before_date': fields.Date.today() + relativedelta(
                    months=self.lot_id.label_durability_id.month_qty),
                'harvest': fields.Date.today().year,
                'label_durability_id': self.lot_id.label_durability_id.id,
                'net_weight': self.lot_id.standard_weight,
            })
            counter += 1
