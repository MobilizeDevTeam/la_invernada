from odoo import models, fields, api

class CustomOrdersToInvoice(models.Model):
    _name = 'custom.orders.to.invoice'

    stock_picking_id = fields.Integer(string="Despacho Id", required=True)

    stock_picking_name = fields.Char(string="Despacho", required=True)

    order_id = fields.Integer(string="Pedido Id", required=True)

    order_name = fields.Char(string="Pedido", required=True)

    product_id = fields.Integer(string="Producto Id", required=True)

    product_name = fields.Char(string="Producto", required=True)

    quantity_remains_to_invoice = fields.Float(string="Cantidada por Facturar")

    quantity_to_invoice = fields.Char(string="Cantidad a Facturar", required=True)

    container_number = fields.Char(string="N° Contenedor", compute="_compute_container_number")

    invoice_id = fields.Many2one(
        'account.invoice',
        index=True,
        copy=False,
        string="Pedido"
    )

    total_value = fields.Float(string="Valor Total")

    value_per_kilo = fields.Float(string="Valor por Kilo")

    required_loading_date = fields.Datetime('Fecha Requerida de Carga')

    def _compute_container_number(self):
        for item in self:
            self.container_number = self.env['stock.picking'].search([('id','=',self.stock_picking_id)]).container_number
            raise models.ValidationError(self.env['stock.picking'].search([('id','=',self.stock_picking_id)]).container_number)


  
    
