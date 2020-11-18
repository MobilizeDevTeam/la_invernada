from odoo import models, api, fields
from dateutil.relativedelta import *
import pandas as pd
from odoo.addons import decimal_precision as dp
import xlsxwriter
import xlwt
from xlsxwriter.workbook import Workbook
import base64

import io
import re


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    salary_id = fields.Many2one('hr.salary.rule', 'Agregar Entrada')

    have_absence = fields.Boolean('¿Tiene Ausencias?', default=False)

    absence_days = fields.Float('Dias Ausencias', default=0)

    vacations_days = fields.Float('Dias Vacaciones', default=0)

    vacation_paid = fields.Boolean('Vacaciones Pagadas')

    @api.onchange('struct_id')
    def onchange_domain(self):
        res = {
            'domain': {
                'salary_id': [('name', 'not in', self.input_line_ids.mapped('name'))],
            }
        }
        return res

    @api.multi
    def add(self):
        for item in self:
            if item.salary_id:
                self.env['hr.payslip.input'].create({
                    'name': item.salary_id.name,
                    'code': item.salary_id.code,
                    'contract_id': item.contract_id.id,
                    'payslip_id': item.id
                })
            item.salary_id = None

    @api.multi
    def get_leave(self):
        for item in self:
            employee_id = item.contract_id.employee_id
            leaves = self.env['hr.leave'].search(
                [('employee_id', '=', employee_id.id), ('state', '=', 'validate'),
                 ('date_from', '>', item.date_from), ('date_to', '<', item.date_to)])
            for leave in leaves:
                if item.worked_days_line_ids.filtered(
                        lambda a: a.name == leave.holiday_status_id.name).number_of_days != sum(
                    leaves.mapped('number_of_days')):
                    models._logger.error('Aqui')
                    if leave.holiday_status_id.name in item.worked_days_line_ids.mapped('name'):

                        days = item.worked_days_line_ids.filtered(lambda a: a.name == leave.holiday_status_id.name)
                        days.write({
                            'number_of_days': days.number_of_days + leave.number_of_days
                        })
                    else:
                        models._logger.error('No Aqui')
                        code = self.generate_code(leave.holiday_status_id.name, leave.holiday_status_id.id)
                        self.env['hr.payslip.worked_days'].create({
                            'name': leave.holiday_status_id.name,
                            'number_of_days': leave.number_of_days,
                            'code': code,
                            'contract_id': item.contract_id.id,
                            'payslip_id': item.id,
                            'unpaid': leave.holiday_status_id.unpaid
                        })
                if leave.holiday_status_id.name == 'Vacaciones' and leaves:
                    models._logger.error('Esta Aqui')
                    if leave.holiday_status_id.unpaid:
                        item.write({
                            'vacations_days': sum(
                                item.worked_days_line_ids.filtered(lambda a: 'Vacaciones' in a.name).mapped(
                                    'number_of_days')),
                            'vacation_paid': False
                        })
                    else:
                        models._logger.error('Aqui Esta')
                        item.write({
                            'vacations_days': sum(
                                item.worked_days_line_ids.filtered(lambda a: 'Vacaciones' in a.name).mapped(
                                    'number_of_days')),
                            'vacation_paid': True
                        })
            if sum(leaves.mapped('number_of_days')) > 0 and not leaves:
                models._logger.error('No')
                item.write({
                    'absence_days': 0,
                    'have_absence': False
                })
            else:
                item.write({
                    'absence_days': sum(leaves.filtered(lambda a: 'Vacaciones' not in a.holiday_status_id.name).mapped(
                        'number_of_days')),
                    'have_absence': True
                })

    def generate_code(self, name, id):
        res = re.sub(r'[AEIOUÜÁÉÍÓÚ]', '', name, flags=re.IGNORECASE)
        identy = ''
        if id > 10:
            identy = '{}0'.format(id)
        else:
            identy = '{}00'.format(id)
        res = res[0:3].upper() + identy
        return res

    @api.multi
    def compute_sheet(self):
        super(HrPayslip,self).compute_sheet()
        if self.worked_days_line_ids.filtered(lambda a : a.code == 'SBS220'):
            hr_payrule = str(self.env['hr.salary.rule'].search([('code','=','SIS')]).amount_python_compute)
            hr_payrule_2 = hr_payrule.replace('payslip','self')
            hr = hr_payrule_2.replace('inputs.HEX50', 'self.input_line_ids.filtered(lambda a: a.code == "HEX50")')
            hr_final = hr.replace('contract','self.contract_id')
            result = 0
            exec(hr_final)
            raise models.ValidationError(result)


    def get_sis_values(self,afp,payslip_id):
        payslip = self.env['hr.payslip'].search([('id','=',payslip_id)])
        if afp == 'CAPITAL':
            return payslip.indicadores_id.tasa_sis_capital
        elif afp == 'CUPRUM':
            return payslip.indicadores_id.tasa_sis_cuprum
        elif afp == 'HABITAT':
            return payslip.indicadores_id.tasa_sis_habitat
        elif afp == 'MODELO':
            return payslip.indicadores_id.tasa_sis_modelo
        elif afp == 'PLANVITAL':
            return payslip.indicadores_id.tasa_sis_planvital
        elif afp == 'PROVIDA':
            return payslip.indicadores_id.tasa_sis_provida
        elif afp == 'UNO':
            return payslip.indicadores_id.tasa_sis_uno
        else:
            return 0