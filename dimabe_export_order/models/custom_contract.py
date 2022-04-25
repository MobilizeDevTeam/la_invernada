from odoo import models, fields, api


class CustomContract(models.Model):
    _name = 'custom.contract'
    _description = "Tipo de Contracto (Custom)"

    name = fields.Char(
        'Número de Contrato',
        required=True
    )

    container_number = fields.Integer('Cantidad de Contenedores')

    sale_order_ids = fields.One2many(
        'sale.order',
        'contract_id',
        'Ventas'
    )

    is_complete = fields.Boolean(
        'Completo',
        compute='_check_is_complete',
        store=True
    )

    @api.one
    @api.depends('sale_order_ids', 'container_number')
    def _check_is_complete(self):
        for item in self:
            total = len(self.sale_order_ids)
            item.is_complete = total == item.container_number ## If
