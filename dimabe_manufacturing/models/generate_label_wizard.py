from odoo import fields, models, api
import base64


class GenerateLabelWizard(models.TransientModel):
    _name = 'generate.label.wizard'
    _description = "Generar Plantilla de Etiqueta"

    eco_id = fields.Many2one('mrp.eco')

    product_id = fields.Many2one('product.product', related='eco_id.product_id')

    producer_id = fields.Many2one('res.partner', string='Productor',
                                  domain=[('is_company', '=', True), ('supplier', '=', True), ('name', '!=', ''),
                                          ('type', '=', 'contact'), ('parent_id', '=', False)])

    type_of_best_before = fields.Selection(selection=[('mask', 'Escrita'), ('real', 'Real')], default='mask',
                                           string="Mostrar la fecha de Consumir Preferentemente antes de")

    best_before_date_mask = fields.Char(string="Consumir Preferentemente antes de (Plantilla)")

    best_before_date = fields.Date(string='Consumir Preferentemente antes de')

    type_of_packaging = fields.Selection(selection=[('mask', 'Escrita'), ('real', 'Real')], default='mask',
                                         string="Mostrar la fecha de envasado")

    packaging_date_mask = fields.Char(string='Fecha de Envasado (Plantilla)')

    packaging_date = fields.Date(string='Fecha de Envasado')

    type_of_trace_code = fields.Selection(selection=[('mask', 'Escrita'), ('real', 'Real')], default='mask',
                                          string="Mostrar codigo de trazabilidad")

    sale_order_id = fields.Many2one('sale.order', string='Codigo de Trazabilidad (Real)')

    trace_code = fields.Char(string='Codigo de Trazabilidad (Escrita)')

    serial_number = fields.Char(string='Serie')

    gross_weight = fields.Float(string="Kilos Brutos")

    net_weight = fields.Float(string="Kilos Netos")

    @api.multi
    def get_full_url(self):
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        return base_url

    @api.multi
    def generate_label(self):
        label = self
        report = self.env.ref('dimabe_manufacturing.action_stock_production_lot_serial_label_report_template')
        ctx = self.env.context.copy()
        ctx['flag'] = True
        pdf = report.with_context(ctx).render_qweb_pdf(label.id)
        file = base64.b64encode(pdf[0])
        ir_attachment_id = self.env['mrp.document'].sudo().create({
            'name': f'Etiqueta {self.id}',
            'data_fname': 'Etiqueta para Salida de Proceso.pdf',
            'res_name': 'ET: Etiqueta',
            'res_model': 'mrp.eco',
            'res_id': self.eco_id.id,
            'type': 'binary',
            'db_datas': file,
            'datas': file,
        })
        print(file)
