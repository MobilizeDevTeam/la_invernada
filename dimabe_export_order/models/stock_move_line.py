from odoo import fields, models, api


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'