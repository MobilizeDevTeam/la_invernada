from odoo import models, fields, api
import datetime
from datetime import datetime, date, time
from dateutil.relativedelta import *
from dateutil import rrule


class CustomSettlement(models.Model):
    _name = 'custom.settlement'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', 'Empleado', required=True)

    contract_id = fields.Many2one('hr.contract', 'Contrato', related='employee_id.contract_id')

    fired_id = fields.Many2one('custom.fired', 'Causal de Despido')

    date_start_contract = fields.Date('Fecha de inicio', related='contract_id.date_start')

    date_of_notification = fields.Date('Fecha de Notificacion de despido')

    date_settlement = fields.Date('Fecha finiquito')

    period_of_service = fields.Char('Periodo de servicio', compute='compute_period', readonly=True)

    vacation_days = fields.Float('Dias de Vacaciones', compute='compute_vacation_day', readonly=True)

    day_takes = fields.Float('Dias Tomados')

    days_pending = fields.Float('Dias Pendiente')

    type_contract = fields.Selection([
        ('Fijo', 'Fijo'),
        ('Variable', 'Variable')
    ])

    currency_id = fields.Many2one('res.currency', string='Moneda')

    wage = fields.Monetary('Sueldo Base', related='contract_id.wage', currency_field='currency_id')

    reward_value = fields.Monetary('Gratificacion', compute='compute_reward')

    reward_selection = fields.Selection([
        ('Yes', 'Si'),
        ('No', 'No'),
        ('Edit', 'Editar')
    ])

    snack_bonus = fields.Float('Colacion')

    mobilization_bonus = fields.Float('Movilizacion')

    pending_remuneration_payment = fields.Monetary('Remuneraciones Pendientes')

    compensation_warning = fields.Monetary('indemnización Aviso Previo', compute='compute_warning')

    compensation_years = fields.Monetary('indemnización Años de Servicio', compute='compute_years')

    compensation_vacations = fields.Monetary('indemnización Vacaciones')#, compute='compute_vacations'#)

    settlement = fields.Monetary('Finiquito')

    @api.multi
    @api.onchange('date_settlement')
    def compute_period(self):
        for item in self:
            period = relativedelta(item.date_settlement, item.date_start_contract)
            item.period_of_service = '{} años , {} meses , {} dias'.format(period.years, period.months,
                                                                           (period.days + 1))

    @api.multi
    @api.onchange('date_settlement')
    def compute_vacation_day(self):
        for item in self:
            period = relativedelta(item.date_settlement, item.date_start_contract)
            item.vacation_days = (15 * period.years + (period.months * 1.25 + (period.days + 1) / 30 * 1.25))

    @api.multi
    def compute_reward(self):
        for item in self:
            item.reward_value = item.wage * 0.25

    @api.onchange('reward_selection')
    def onchange_reward_selection(self):
        for item in self:
            if item.reward_selection == 'Yes' or item.reward_selection == 'Edit':
                item.reward_value = item.wage * 0.25
            else:
                item.reward_value = 0

    # @api.multi
    # def compute_vacations(self):
    #     for item in self:
    #         if item.vacation_days > 0:
    #             item.compensation_vacations = item.wage * item.vacation_days

    @api.multi
    @api.onchange('date_settlement')
    def compute_warning(self):
        for item in self:
            period = relativedelta(item.date_settlement, item.date_start_contract)
            if period.days < 30:
                item.compensation_warning = (
                        (item.wage + item.snack_bonus + item.mobilization_bonus) + item.reward_value)

    @api.multi
    @api.onchange('date_settlement')
    def compute_years(self):
        for item in self:
            period = relativedelta(item.date_settlement, item.date_start_contract)
            item.compensation_years = ((item.wage + item.snack_bonus + item.mobilization_bonus)
                                       + item.reward_value) * period.years

    @api.multi
    @api.depends('date_settlement', 'pending_remuneration_payment', 'reward_selection')
    def compute_settlement(self):
        for item in self:
            period = relativedelta(item.date_settlement, item.date_start_contract)
            item.settlement = (item.wage + item.reward_value) + item.pending_remuneration_payment + \
                              (item.snack_bonus + item.mobilization_bonus) \
                              + (item.compensation_vacations + item.compensation_warning + item.compensation_years)

    @api.multi
    def test(self):
        salary = self.env['hr.payslip.line'].search(
            [('employee_id.id', '=', self.employee_id.id), ('name', 'like', 'LIQUIDO')])
        raise models.UserError(salary)
