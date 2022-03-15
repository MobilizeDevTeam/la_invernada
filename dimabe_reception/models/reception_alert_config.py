from odoo import fields, models, api
from odoo.addons import decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)


class ReceptionAlertConfig(models.Model):
    _name = 'reception.alert.config'
    _description = "Alerta de Recepcion"

    hr_alert = fields.Float(
        'hr para alerta',
        digits=dp.get_precision('Product Unit of Measure')
    )

    notify_elapsed_time_to = fields.Many2many(
        'res.partner',
        string='Notificar Retraso de Camión a'
    )

    kg_diff_alert = fields.Float(
        'diferencia de kg para alerta',
        digits=dp.get_precision('Product Unit of Measure')
    )

    notify_diff_kg = fields.Many2many(
        'res.partner',
        string='Notificar Diferencia de kg a'
    )

    def get_notify_elapsed_mails(self):
        return ','.join(self.notify_elapsed_time_to.mapped('email'))

    def get_notify_diff_emails(self):
        return ','.join(self.notify_diff_kg.mapped('email'))




