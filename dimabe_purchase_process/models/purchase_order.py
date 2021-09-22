from odoo import fields, models, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Rechazado'),
        ('purchase sent', 'Orden de Compra Enviada')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')

    boss_approval_id = fields.Many2one(
        'res.users',
        'vb jefe de área',
        default=None,
        nullable=True
    )

    boss_approval_date = fields.Datetime(
        string='fecha de aprobación jefe',
        default=None,
        nullable=True
    )

    provider_po_document = fields.Binary('Documento entregado por proveedor')

    @api.model
    def get_analytic_accounts(self):
        res = self.env['account.analytic.account'].search([])
        account_list = []
        tmp = []
        for account in res:
            tmp.append(account)
            if len(tmp) == 2:
                account_list.append(tmp)
                tmp = []
        return account_list

    @api.multi
    def action_rfq_send(self):
        for item in self:
            if not item.boss_approval_id:
                item.update({
                    'boss_approval_id': self.env.user.id,
                    'boss_approval_date': fields.datetime.now()
                })
            if item.state == 'purchase':
                item.update({
                    'state':'purchase sent'
                })
        res = super(PurchaseOrder, self).action_rfq_send()
        return res

    @api.multi
    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        template_id = self.env.ref('dimabe_purchase_process.po_confirmed_mail_template')
        for order in self:
            order.message_post_with_template(template_id.id)
        return res

    @api.model
    def get_po_approve_data(self):
        approve_message = self.message_ids.filtered(lambda x: x.subtype_id.name == 'SdP aprobada')
        if approve_message:
            approve_message = approve_message[0]
            return '{} {}'.format(approve_message.author_id.name, approve_message.date)
        return ''

    @api.model
    def get_mail_sender(self):
        if self.boss_approval_id and self.boss_approval_date:
            return '{} {}'.format(self.boss_approval_id.name, self.boss_approval_date)
        return ''

    @api.model
    def get_email_to(self, ref_id):
        user_group = self.env.ref(ref_id)
        email_list = [
            usr.partner_id.email for usr in user_group.users if usr.partner_id.email
        ]
        return ','.join(email_list)

    @api.model
    def create(self, values_list):
        res = super(PurchaseOrder, self).create(values_list)
        if res.order_line and len(res.order_line) > 0:
            for line in res.order_line:
                if not line.price_unit or line.price_unit == 0:
                    raise models.ValidationError('debe agregar precio unitario')
        return res

    @api.multi
    def write(self, values):
        res = super(PurchaseOrder, self).write(values)
        for item in self:
            if item.order_line and len(item.order_line) > 0:
                for line in item.order_line:
                    if not line.price_unit or line.price_unit == 0:
                        raise models.ValidationError('debe agregar precio unitario')
        return res
