from odoo import models, api, fields
from dateutil.relativedelta import *
import pandas as pd
from odoo.addons import decimal_precision as dp
import re


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    input_id = fields.Many2one('hr.payslip.input', 'Agregar Entrada')

    @api.onchange('employee_id')
    def onchange_employee(self):
        for item in self:
            res = {
                'domain': {
                    'input_id': [('id', 'not in', item.input_line_ids), ('contract_id', '=', item.contract_id)],
                }
            }
        return res

    @api.multi
    def add(self):
        for item in self:
            if item.input_id:
                item.write({
                    'input_line_ids': [(4, item.input_id.id)]
                })

    @api.multi
    def get_leave(self):
        for item in self:
            employee_id = item.contract_id.employee_id
            leaves = self.env['hr.leave'].search(
                [('employee_id', '=', employee_id.id), ('state', '=', 'validate')])
            for leave in leaves:
                if item.worked_days_line_ids.filtered(
                        lambda a: a.name == leave.holiday_status_id.name).number_of_days != sum(
                    leaves.mapped('number_of_days')):
                    if leave.holiday_status_id.name in item.worked_days_line_ids.mapped('name'):
                        days = item.worked_days_line_ids.filtered(lambda a: a.name == leave.holiday_status_id.name)
                        days.write({
                            'number_of_days': days.number_of_days + leave.number_of_days
                        })
                    else:
                        self.env['hr.payslip.worked_days'].create({
                            'name': leave.holiday_status_id.name,
                            'number_of_days': leave.number_of_days,
                            'code': '',
                            'contract_id': item.contract_id.id,
                            'payslip_id': item.id
                        })
