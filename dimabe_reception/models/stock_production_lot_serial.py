from odoo import fields, models, api
from odoo.addons import decimal_precision as dp


class StockProductionLotSerial(models.Model):
    _name = 'stock.production.lot.serial'
    _description = "Numero de Serie"

    name = fields.Char(
        'Serie',
        compute='_compute_name'
    )

    calculated_weight = fields.Float(
        'Peso Estimado',
        digits=dp.get_precision('Product Unit of Measure')
    )

    real_weight = fields.Float(
        'Peso Real',
        nulable=True,
        default=None,
        digits=dp.get_precision('Product Unit of Measure')
    )

    display_weight = fields.Float(
        'Peso',
        compute='_compute_display_weight',
        inverse='_inverse_real_weight',
        digits=dp.get_precision('Product Unit of Measure')
    )

    stock_production_lot_id = fields.Many2one(
        'stock.production.lot',
        'Lote'
    )

    serial_number = fields.Char(
        'Numero Serie'
    )


    @api.multi
    def _compute_display_weight(self):
        for item in self:
            if item.real_weight:
                item.display_weight = item.real_weight
            else:
                item.display_weight = item.calculated_weight

    @api.multi
    def _inverse_real_weight(self):
        for item in self:
            item.real_weight = item.display_weight

    @api.multi
    def _compute_name(self):
        for item in self:
            item.name = item.serial_number
