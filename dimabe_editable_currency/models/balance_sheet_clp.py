from odoo import fields, models, api


class ModelName(models.Model):
    _name = 'balance.sheet.clp'
    _description = 'Balance de Situacion CLP'

    currency_id = fields.Many2one('res.currency', 'Moneda',
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'CLP')]))

    account_id = fields.Many2one('account.account', 'Cuenta')

    balance = fields.Monetary('Balance')

    @api.multi
    def get_data(self):
        for item in self:
            accounts = self.env['account.account'].search([])
            for ac in accounts:
                ac_move_line = self.env['account.move.line'].search([('account_id', '=', ac.id)])
                result = sum(ac_move_line.mapped('debit')) - sum(ac_move_line.mapped('credit'))
                raise models.ValidationError(result)
                self.env['balance.sheet.clp'].create({
                    'account_id': ac.id,
                    'balance': sum(ac_move_line.mapped('debit')) - sum(ac_move_line.mapped('credit'))
                })
