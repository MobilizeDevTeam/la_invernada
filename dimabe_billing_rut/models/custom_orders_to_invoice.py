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

    invoice_id = fields.Many2one(
        'account.invoice',
        index=True,
        copy=False,
        string="Pedido"
    )

    #def change_invoice_line(self,invoice_line):
    #    for item in self:
    #        if item.product_id == invoice_line.product_id and item.order_id == invoice_line.order_id and item.stock_picking_id == invoice_line.stock_picking_id:
    #            self.env[self.model].search([('id','=',item.id)]).unlink()

    