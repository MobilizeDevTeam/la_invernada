from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger('TEST ========================')


class DiaryAccountMoveLineReport(models.AbstractModel):
    _name = 'report.mblz_la_invernada.report_diary_account_move_pdf'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(_("El contenido del reporte esta vacio, El reporte no puede imprimirse."))

        report = self.env['ir.actions.report']._get_report_from_name('mblz_la_invernada.report_diary_account_move_pdf')
        report_data = {            
            'doc_ids': report.id,
            'doc_model': report.model,
            'docs': report.id,
            'date': data['form']['date'],
            'company_get_id': data['form']['company_get_id'],
            'get_move_lines': self.get_move_lines(data['form']['date'], data['form']['company_get_id'][0]),
        }
        _logger.info('LOG:.    test data report {}'.format(report_data))
        return report_data

    def get_move_lines(self, date, company_id):
        domain = [
            ('date', '=', date),
            ('company_id.id', '=', company_id)
            ]

        res = self.env['account.move.line'].sudo().search(domain, order='date asc')
        
        return res