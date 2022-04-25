from odoo import fields, models, api
from odoo.tools.float_utils import float_round
from datetime import datetime
from odoo.addons import decimal_precision as dp


class ProductProduct(models.Model):
    _inherit = 'product.product'

    variety = fields.Char(
        'Variedad',
        compute='_compute_variety',
        search='_search_variety'
    )

    type_product = fields.Char(
        'Tipo de Producto'
        , compute='_compute_type_product'
    )

    label_name = fields.Char(
        'Nombre de Etiqueta'
        , compute='_compute_label_product'
    )

    caliber = fields.Char(
        'Caliber',
        compute='_compute_caliber',
        store=True
    )

    package = fields.Char('Envase', compute='_compute_package')

    is_to_manufacturing = fields.Boolean('Es Fabricacion?', default=True, compute="compute_is_to_manufacturing")

    is_standard_weight = fields.Boolean('Es peso estandar', default=False)

    measure = fields.Char('Medida', compute='_compute_measure')

    total_weight = fields.Float('Total Kilos Disponibles', compute='_compute_total_weight',
                                digits=dp.get_precision('Product Unit of Measure'))

    dispatch_weight = fields.Float('Kilos Despachados', compute='_compute_dispatch_weight')

    supply_id = fields.Many2one('product.product', 'Producto')



    @api.multi
    def _compute_measure(self):
        for item in self:
            for value in item.attribute_value_ids.mapped('name'):
                if "Saco 10K" == value:
                    item.measure = '10 Kilos'
                if "Saco 25K" == value:
                    item.measure = '25 Kilos'

    @api.multi
    def _compute_caliber(self):
        for item in self:
            if item.get_calibers():
                item.caliber = item.get_calibers()
            else:
                item.caliber = "S/Calibre"

    @api.multi
    def _compute_package(self):
        for item in self:
            for value in item.attribute_value_ids.mapped('name'):
                if "Saco" in value:
                    item.package = 'Sacos de '

    @api.multi
    def _compute_type_product(self):
        for item in self:
            type = []
            for value in item.attribute_value_ids:
                if value.id != item.attribute_value_ids[0].id:
                    type.append(',' + value.name)
                else:
                    type.append(value.name)
            type_string = ''.join(type)
            item.type_product = type_string

    @api.multi
    def _compute_label_product(self):
        for item in self:
            specie = item.get_variant('Especie')
            if specie == 'Nuez Con Cáscara':
                item.label_name = item.name + ' (' + item.get_calibers() + ')'
            if specie == 'Nuez Sin Cáscara':
                item.label_name = item.name + ' (' + item.get_color() + ')'

    @api.multi
    def compute_is_to_manufacturing(self):
        for item in self:
            if "Fabricar" in item.route_ids.mapped('name'):
                item.update({
                    'is_to_manufacturing': True
                })

    @api.multi
    def _compute_variety(self):
        for item in self:
            item.variety = item.get_variety()

    @api.multi
    def _search_variety(self, operator, value):
        attribute_value_ids = self.env['product.attribute.value'].search([('name', operator, value)])
        product_ids = []
        if attribute_value_ids:
            product_ids = self.env['product.product'].search([
                ('attribute_value_ids', '=', attribute_value_ids.mapped('id'))
            ]).mapped('id')
        return [('id', 'in', product_ids)]

    @api.multi
    def _compute_total_weight(self):
        for item in self:
            if item.tracking == 'lot':
                lots = self.env['stock.production.lot'].search([('product_id', '=', item.id), ('available_kg', '>', 0)])
                item.total_weight = sum(lots.mapped('available_kg'))

    @api.multi
    def _compute_dispatch_weight(self):
        for item in self:
            serial = self.env['stock.production.lot.serial'].search(
                [('stock_production_lot_id.product_id', '=', item.id), ('reserved_to_stock_picking_id', '!=', None)])
            total = sum(serial.mapped('display_weight'))
            item.dispatch_weight = total

    def get_and_update(self, product_id, to_fix=False):
        lots = self.env['stock.production.lot'].search([('product_id', '=', product_id)])
        for lot in lots:
            quant = self.env['stock.quant'].search([('lot_id', '=', lot.id), ('location_id.usage', '=', 'internal')])
            if quant:
                try:
                    if quant.quantity != lot.available_kg or quant.quantity != sum(
                            lot.stock_production_lot_serial_ids.mapped('display_weight')):
                        quant.write({
                            'reserved_quantity': lot.available_kg,
                            'quantity': lot.available_kg
                        })
                except:
                    query = 'DELETE FROM stock_quant where id = {}'.format(quant[0].id)
                    cr = self._cr
                    cr.execute(query)
            else:
                self.env['stock.quant'].sudo().create({
                    'lot_id': lot.id,
                    'product_id': lot.product_id.id,
                    'reserved_quantity': sum(
                        lot.stock_production_lot_serial_ids.filtered(lambda x: not x.consumed).mapped(
                            'display_weight')),
                    'quantity': sum(lot.stock_production_lot_serial_ids.filtered(lambda x: not x.consumed).mapped(
                        'display_weight')),
                    'location_id': lot.stock_production_lot_serial_ids.mapped('production_id')[
                        0].location_dest_id.id if lot.stock_production_lot_serial_ids.mapped('production_id') else 12,
                    'in_date': datetime.now()
                })
        self.env['stock.quant'].sudo().search(
            [('product_id.id', '=', product_id), ('location_id.usage', '=', 'internal'),
             ('quantity', '<', 0)]).sudo().unlink()

    def update_kg(self, product_id):
        lots = self.env['stock.production.lot'].search([('product_id', '=', product_id)])
        for lot in lots:
            if 'Verde' in lot.product_id.name:
                oven_use = self.env['oven.use'].search([('used_lot_id', '=', lot.id)])
                for oven in oven_use:
                    if oven.finish_date and oven.finish_active_time:
                        lot.stock_production_lot_serial_ids.write({
                            'consumed': True
                        })
            total = sum(lot.stock_production_lot_serial_ids.filtered(lambda a: not a.consumed).mapped('display_weight'))
            if total != lot.available_kg:
                lot.sudo().write({
                    'available_kg': total,
                    'available_weight': total
                })
            else:
                continue

    def mass_fix_diference(self):
        products = self.env['product.product'].search([('tracking', '=', 'lot')])
        for product in products:
            if product.total_weight != product.qty_available:
                self.update_kg(product.id)
                self.get_and_update(product.id)
