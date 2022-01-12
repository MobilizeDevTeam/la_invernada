from odoo import fields, models, api
import xlsxwriter
from datetime import date, datetime
import base64


class StockReportXlsx(models.TransientModel):
    _name = 'stock.report.xlsx'

    year = fields.Integer('Cosecha')

    stock_selection = fields.Selection(
        [('raw', 'Informe existencia materia prima'), ('calibrate', 'Informe existencia producto calibrado'),
         ('split', 'Informe existencia producto partido'), ('vain', 'Informe existencia producto vana'),
         ('discard', 'Informe existencia descarte'), ('pt', 'Informe existencia producto terminado'),
         ('washed', 'Informe existencia producto lavado'), ('raw_service', 'Informe existencia materia prima servicio'),
         ('washed_service', 'Informe existencia producto lavado servicio'),
         ('split_service', 'Informe existencia producto partido servicio'),
         ('calibrate_service', 'Informe existencia Producto Calibrado Servicio'),
         ('discart_service', 'Informe existencia Producto Descarte Servicio'),
         ('vain_service', 'Informe existencia Producto Vana Servicio')
         ])

    @api.multi
    def generate_report(self):
        dict_data = {}
        if self.stock_selection == 'raw':
            dict_data = self.generate_excel_raw_report(
                [('product_id.categ_id.name', 'in', ('Seca', 'Desp. y Secado')), ('harvest', '=', self.year)],
                'Materia Prima')
        elif self.stock_selection == 'calibrate':
            dict_data = self.generate_excel_serial_report(
                [('product_id.default_code', 'like', 'PSE006'), ('product_id.name', 'not like', 'Vana'),
                 ('product_id.name', 'not like', 'Descarte'), ('harvest_filter', '=', self.year)], "Producto Calibrado")
        elif self.stock_selection == 'split':
            dict_data = self.generate_excel_serial_report(
                [('product_id.categ_id.name', 'in',
                  ('Envasado NSC', 'Partido Manual Calidad', 'Partido Mecánico/Láser')),
                 ('harvest_filter', '=', self.year),
                 ('product_id.name', 'not like', 'Vana'), ('product_id.default_code', 'not like', 'PT')],
                'Producto Partido')
        elif self.stock_selection == 'vain':
            dict_data = self.generate_excel_serial_report(
                [('product_id.name', 'ilike', 'Vana'), ('harvest_filter', '=', self.year)], "Vana")
        elif self.stock_selection == 'discard':
            dict_data = self.generate_excel_serial_report(
                [('product_id.name', 'ilike', 'Descarte'), ('product_id.default_code', 'ilike', 'PSE006'),
                 ('harvest_filter', '=', self.year)], 'Descarte')
        elif self.stock_selection == 'washed':
            dict_data = self.generate_excel_serial_report(
                [('product_id.default_code', 'like', 'PSE016'), (
                'product_id.categ_id.name', 'in', ('Envasado NSC', 'Partido Manual Calidad', 'Partido Mecánico/Láser')),
                 ('product_id.name', 'not like', 'Vana'),
                 ('product_id.name', 'not like', '(S)'), ('harvest_filter', '=', self.year)], 'Producto Lavado')
        elif self.stock_selection == 'raw_service':
            dict_data = self.generate_excel_raw_report(
                [('product_id.default_code', 'like', 'MPS'), ('product_id.name', 'not like', 'Verde'),
                 ('harvest', '=', self.year)], 'Materia Prima Servicio')
        elif self.stock_selection == 'washed_service':
            dict_data = self.generate_excel_serial_report(
                [('product_id.default_code', 'like', 'PSES016'), ('harvest_filter', '=', self.year)],
                'Producto Lavado Servicio')
        elif self.stock_selection == 'split_service':
            dict_data = self.generate_excel_serial_report(
                ["&", "|", ("product_id.categ_id.name", "=", "Producto Semi-elaborado / Envasado NSC Servicio"),
                 ("product_id.categ_id.name", "=", "Partido Mecánico/Láser Servicio"),
                 ("harvest_filter", "=", self.year)],
                'Producto Partido Servicio')
        elif self.stock_selection == 'calibrate_service':
            dict_data = self.generate_excel_serial_report(
                [('product_id.default_code', 'like', 'PSES006'), ('harvest_filter', '=', self.year),
                 ('product_id.name', 'not like', 'Vana'),
                 ('product_id.name', 'not like', 'Descarte')], 'Producto Calibrado Servicio'
            )
        elif self.stock_selection == 'vain_service':
            dict_data = self.generate_excel_serial_report(
                [('product_id.name', 'like', 'Vana'), ('product_id.categ_id.name', 'like', 'Servicio')],
                'Producto Vana Servicio'
            )
        elif self.stock_selection == 'discart_service':
            dict_data = self.generate_excel_serial_report(
                [('product_id.name', 'like', 'Descarte'), ('product_id.categ_id.name', 'like', 'Servicio')],
                'Producto Descarte Servicio'
            )
        elif self.stock_selection == 'pt':
            dict_data = self.generate_pt_report()
        attachment_id = self.env['ir.attachment'].sudo().create({
            'name': dict_data['file_name'],
            'datas_fname': dict_data['file_name'],
            'datas': dict_data['base64']
        })

        action = {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment_id.id, ),
            'target': 'new',
        }
        return action

    def generate_excel_raw_report(self, list_condition, type_product):
        file_name = 'C:\\Users\\fabia\\Documents\\test.xlsx'
        workbook = xlsxwriter.Workbook(file_name)
        text_format = workbook.add_format({
            'text_wrap': True
        })
        number_format = workbook.add_format({'num_format': '#,##0.00'})
        date_format = workbook.add_format({'num_format': 'dd/mmmm/yyyy'})
        sheet = workbook.add_worksheet('Informe de Materia Prima')
        row = 0
        col = 0
        titles = [(1, 'Productor:'), (2, 'Lote:'), (3, 'Kilos Disponible:'), (4, 'Variedad:'), (5, 'Calibre:'),
                  (6, 'Ubicacion Sistema:'), (7, 'Producto:'), (8, 'N° Guia:'), (9, 'Año Cosecha:'),
                  (10, 'Kilos Recepcionados:'), (11, 'Fecha Creacion:'), (12, 'Series Disponible:'),
                  (13, 'Enviado a Proceso de:'), (14, 'Fecha de Envio:'), (15, 'Ubicacion Fisica:'),
                  (16, 'Observaciones:')]
        for title in titles:
            sheet.write(row, col, title[1], text_format)
            col += 1
        row += 1
        col = 0

        lots = self.env['stock.production.lot'].sudo().search(list_condition)
        for lot in lots:
            if lot.producer_id:
                sheet.write(row, col, lot.producer_id.display_name)
            else:
                sheet.write(row, col, "Sin Definir")
            col += 1
            sheet.write(row, col, lot.name)
            col += 1
            sheet.write_number(row, col, float(
                sum(lot.stock_production_lot_serial_ids.filtered(lambda a: not a.consumed).mapped('display_weight'))),
                               number_format)
            col += 1
            sheet.write(row, col, lot.product_id.get_variety())
            col += 1
            sheet.write(row, col, lot.product_id.get_calibers())
            col += 1
            if lot.location_id:
                sheet.write(row, col, lot.location_id.display_name)
            col += 1
            sheet.write(row, col, lot.product_id.display_name)
            col += 1
            sheet.write(row, col, lot.show_guide_number)
            col += 1
            sheet.write(row, col, lot.harvest)
            col += 1
            sheet.write(row, col, lot.reception_weight, number_format)
            col += 1
            sheet.write_datetime(row, col, lot.create_date, date_format)
            col += 1
            sheet.write(row, col, len(lot.stock_production_lot_serial_ids.filtered(lambda a: not a.consumed)))
            col += 1
            if lot.workcenter_id:
                sheet.write(row, col, lot.workcenter_id.display_name)
            col += 1
            if lot.delivered_date:
                sheet.write(row, col, lot.delivered_date.strftime("%d-%m-%Y"))
            col += 1
            if lot.physical_location:
                sheet.write(row, col, lot.physical_location, text_format)
            col += 1
            if lot.observations:
                sheet.write(row, col, lot.observations)
            row += 1
            col = 0
        workbook.close()
        with open(file_name, "rb") as file:
            file_base64 = base64.b64encode(file.read())
        report_name = f'Informe de Existencia {type_product} {date.today().strftime("%d/%m/%Y")}.xlsx'

        return {'file_name': report_name, 'base64': file_base64}

    def generate_excel_serial_report(self, list_condition, type_product):
        file_name = 'C:\\Users\\fabia\\Documents\\test.xlsx'
        workbook = xlsxwriter.Workbook(file_name)
        sheet = workbook.add_worksheet(f"Informe de {type_product}")
        text_format = workbook.add_format({
            'text_wrap': True
        })
        number_format = workbook.add_format({'num_format': '#,##0.00'})
        date_format = workbook.add_format({'num_format': 'dd/mmmm/yyyy'})
        row = 0
        col = 0
        titles = [(50.56, 'Productor'), (15.33, 'Serie'), (13.22, 'Kilos Producidos'), (13.22, 'Kilos Disponible'),
                  (8, 'Variedad'),
                  (12.22, 'Calibre'),
                  (11, 'Ubicacion Sistema'), (54.22, 'Producto'), (9.22, 'Serie Disponible'),
                  (9.56, 'Fecha de Produccion'),
                  (10, 'Cliente o Calidad'), (22.89, 'Enviado a proceso'), (9.56, 'Fecha de Envio'),
                  (13.78, 'Ubicacion Fisica'), (10.89, 'Observacion')]
        for title in titles:
            sheet.set_column(col, col, title[0])
            sheet.write(row, col, title[1], text_format)
            col += 1
        col = 0
        row += 1
        serials = self.env['stock.production.lot.serial'].sudo().search(list_condition)
        for serial in serials:
            if serial.producer_id:
                sheet.write(row, col, serial.producer_id.display_name)
            else:
                sheet.write(row, col, 'No Definido')
            col += 1
            sheet.write(row, col, serial.serial_number)
            col += 1
            sheet.write_number(row, col, serial.display_weight, number_format)
            col += 1
            sheet.write(row, col, serial.available_weight, number_format)
            col += 1
            sheet.write(row, col, serial.product_id.get_variety())
            col += 1
            sheet.write(row, col, serial.product_id.get_calibers())
            col += 1
            if serial.stock_production_lot_id.location_id:
                sheet.write(row, col, serial.stock_production_lot_id.location_id.display_name)
            col += 1
            sheet.write(row, col, serial.product_id.display_name)
            col += 1
            if serial.consumed:
                sheet.write(row, col, 'Consumida')
            else:
                sheet.write(row, col, 'Disponible')
            col += 1
            sheet.write_datetime(row, col, serial.packaging_date, date_format)
            col += 1
            if serial.client_or_quality:
                sheet.write(row, col, serial.client_or_quality)
            col += 1
            if serial.workcenter_send_id:
                sheet.write(row, col, serial.workcenter_send_id.display_name)
            col += 1
            if serial.delivered_date:
                sheet.write(row, col, serial.delivered_date, date_format)
            col += 1
            if serial.physical_location:
                sheet.write(row, col, serial.physical_location, text_format)
            col += 1
            if serial.observations:
                sheet.write(row, col, serial.observations)
            row += 1
            col = 0
        workbook.close()
        with open(file_name, "rb") as file:
            file_base64 = base64.b64encode(file.read())
        report_name = f'Informe de Existencia {type_product} {date.today().strftime("%d/%m/%Y")}.xlsx'
        return {'file_name': report_name, 'base64': file_base64}

    def generate_pt_report(self):
        file_name = 'pt_name.xlsx'
        workbook = xlsxwriter.Workbook(file_name)
        sheet = workbook.add_worksheet('Informe PT')
        text_format = workbook.add_format({
            'text_wrap': True
        })
        date_format = workbook.add_format({'num_format': 'dd/mmmm/yyyy'})
        row = 0
        col = 0
        titles = [(1, 'Pedido'), (13, 'Lote'), (14, 'Producto'), (15, 'Productor'), (2, 'Medida'),
                  (3, 'Cantidad Producida'), (4, 'Kilos Producido'),
                  (5, 'Fecha de Creacion'), (6, 'Estado de Produccion'), (7, 'Cantidad Disponible'),
                  (8, 'Kilos Disponible'), (16, 'Estado de Despacho'), (9, 'Cliente'), (10, 'Pais Destino'),
                  (10, 'Fecha Despacho'),
                  (11, 'Ubicacion Fisica'), (12, 'Observaciones')]
        for title in titles:
            sheet.write(row, col, title[1], text_format)
            col += 1
        col = 0
        row += 1
        lots = self.env['stock.production.lot'].search(
            [('product_id.default_code', 'like', 'PT'), ('sale_order_id', '!=', None), ('harvest', '=', self.year)])
        for lot in lots:
            sheet.write(row, col, lot.sale_order_id.name, text_format)
            col += 1
            sheet.write(row, col, lot.name)
            col += 1
            sheet.write(row, col, lot.product_id.display_name)
            col += 1
            sheet.write(row, col, lot.producer_id.display_name)
            col += 1
            sheet.write(row, col, lot.measure)
            col += 1
            sheet.write(row, col, lot.produced_qty)
            col += 1
            sheet.write(row, col, lot.produced_weight)
            col += 1
            sheet.write(row, col,
                        lot.start_date.strftime('%d-%m-%Y') if lot.start_date else lot.create_date.strftime('%d-%m-%Y'))
            col += 1
            if lot.production_state:
                sheet.write(row, col, lot.production_state)
            col += 1
            sheet.write(row, col, len(lot.mapped('stock_production_lot_serial_ids').filtered(
                lambda a: not a.reserved_to_stock_picking_id and not a.consumed)))
            col += 1
            sheet.write(row, col, sum(lot.mapped('stock_production_lot_serial_ids').filtered(
                lambda a: not a.reserved_to_stock_picking_id and not a.consumed).mapped('real_weight')))
            col += 1
            if lot.dispatch_state:
                sheet.write(row, col, lot.dispatch_state)
            col += 1
            if lot.client_id:
                sheet.write(row, col, lot.client_id.display_name)
            col += 1
            if lot.destiny_country_id:
                sheet.write(row, col, lot.destiny_country_id.name)
            if lot.dispatch_date:
                sheet.write(row, col, lot.dispatch_date.strftime('%d-%m-%Y'))
            col += 1
            if lot.physical_location:
                sheet.write(row, col, lot.physical_location, text_format)
            col += 1
            if lot.observations:
                sheet.write(row, col, lot.observations)
            col += 1
            col = 0
            row += 1
        workbook.close()
        with open(file_name, "rb") as file:
            file_base64 = base64.b64encode(file.read())
        report_name = f'Informe de Existencia de Producto Terminado {date.today().strftime("%d/%m/%Y")}.xlsx'
        return {'file_name': report_name, 'base64': file_base64}
