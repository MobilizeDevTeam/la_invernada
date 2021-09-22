from odoo import fields, models, api
import xlsxwriter
import base64
from datetime import datetime


class ProcessReport(models.TransientModel):
    _name = 'process.report.xlsx'

    process_id = fields.Many2one('mrp.workcenter', string="Centro de Produccion")

    year = fields.Integer('Año', default=datetime.now().year)

    @api.multi
    def generate_xlsx(self):
        dict_data = self.generate_xlsx_process(process_id=self.process_id)
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

    def generate_xlsx_process(self,process_id):
        file_name = 'temp_report.xlsx'
        workbook = xlsxwriter.Workbook(file_name)
        text_format = workbook.add_format({
            'text_wrap': True
        })
        number_format = workbook.add_format({'num_format': '#,##0.00'})
        date_format = workbook.add_format({'num_format': 'dd/mmmm/yyyy'})
        sheet = workbook.add_worksheet(process_id.name)
        processes = self.env['mrp.workorder'].search([('workcenter_id.id','=',self.process_id.id)])
        processes = processes.filtered(lambda a: a.create_date.year == self.year)
        row = 0
        col = 0

        titles = ['Proceso Entrada', 'Pedido', 'Fecha Produccion', 'Lote', 'Serie', 'Productor', 'Producto', 'Variedad',
                  'Peso', 'Proceso Salida', 'Pedido', 'Fecha Produccion', 'Productor', 'Producto', 'Variedad', 'Pallet',
                  'Lote', 'Serie', 'Peso Real']
        for title in titles:
            sheet.write(row, col, title, text_format)
            col += 1
        col = 0
        row += 1
        col_out = 0
        row_in = 0
        row_out = 0
        for process in processes:
            serial_in = self.env['stock.production.lot.serial'].search(
                [('reserved_to_production_id', '=', process.production_id.id)])
            for serial in serial_in:
                sheet.write(row, col, process.production_id.name, text_format)
                col += 1
                sheet.write(row, col, process.production_id.sale_order_id.name, text_format)
                col += 1
                sheet.write(row, col, serial.packaging_date, date_format)
                col += 1
                sheet.write(row, col, serial.stock_production_lot_id.name, text_format)
                col += 1
                sheet.write(row, col, serial.serial_number, text_format)
                col += 1
                sheet.write(row, col, serial.producer_id.display_name, text_format)
                col += 1
                sheet.write(row, col, serial.product_id.display_name, text_format)
                col += 1
                sheet.write(row, col, serial.product_id.get_variety())
                col += 1
                sheet.write(row, col, serial.display_weight, number_format)
                row += 1
                col = 0
        col_out = 9
        row = 1
        for process in processes:
            serial_in = self.env['stock.production.lot.serial'].search(
                [('reserved_to_production_id', '=', process.production_id.id)])
            serial_out = self.env['stock.production.lot.serial'].search(
                [('production_id.id', '=', process.production_id.id)]
            )
            row_final = 0
            for serial in serial_out:
                sheet.write(row, col_out, process.production_id.name, text_format)
                col_out += 1
                sheet.write(row, col_out, process.production_id.sale_order_id.name, text_format)
                col_out += 1
                sheet.write(row, col_out, serial.packaging_date.strftime('%d-%m-%Y'), text_format)
                col_out += 1
                sheet.write(row, col_out, serial.producer_id.name, text_format)
                col_out += 1
                sheet.write(row, col_out, serial.product_id.display_name, text_format)
                col_out += 1
                sheet.write(row, col_out, serial.product_id.get_variety(), text_format)
                col_out += 1
                sheet.write(row, col_out, serial.pallet_id.name, text_format)
                col_out += 1
                sheet.write(row, col_out, serial.stock_production_lot_id.name, text_format)
                col_out += 1
                sheet.write(row, col_out, serial.serial_number, text_format)
                col_out += 1
                sheet.write(row, col_out, serial.display_weight, number_format)
                row += 1
                col_out = 9

        workbook.close()
        with open(file_name, "rb") as file:
            file_base64 = base64.b64encode(file.read())
        report_name = f'Informe de Proceso {self.process_id.name}'
        return {'file_name': report_name, 'base64': file_base64}
