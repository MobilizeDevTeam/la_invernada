from odoo import fields, models, api


class ConfirmRePrintSerial(models.TransientModel):
    _name = 'confirm.re_print.serial'

    serial_id = fields.Many2one('stock.production.lot.serial','Serie')

    @api.multi
    def print(self):
        return self.env.ref(
            'dimabe_manufacturing.action_stock_production_lot_serial_label_report'
        ).report_action(self.serial_id)

    @api.multi
    def get_full_url(self):
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        return base_url