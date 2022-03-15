from odoo import fields, models, api


class ConfirmRePrintTemporarySerial(models.TransientModel):
    _name = 'confirm.re_print.temporary.serial'
    _description = "Re-Imprimir Temporales Series"

    serial_id = fields.Many2one('custom.temporary.serial','Serie')

    @api.multi
    def print(self):
        return self.env.ref(
            'dimabe_manufacturing.action_print_temporary_serial'
        ).report_action(self.serial_id)

    @api.multi
    def get_full_url(self):
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        return base_url