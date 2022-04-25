import base64
import xlsxwriter
from datetime import date
from py_linq import Enumerable
from odoo import fields, models, api


class CustomCustomerOrdersXls(models.TransientModel):
    _name = 'custom.customer.orders.xls'
    _description = "Generador de Archivo de Pedidos"

    orders_file = fields.Binary('Archivo de Pedidos')

    for_year = fields.Integer(string="Año")

    @api.multi
    def generate_orders_file(self):
        file_name = 'temp.xlsx'
        workbook = xlsxwriter.Workbook(file_name)
        # if not self.for_year or self.for_year == 0:
        #    self.for_year = int(date.now.strftime('%Y'))
        sheet = workbook.add_worksheet('Pedidos Clientes')
        formats = self.set_formats(workbook)
        row = 0
        col = 0
        titles = [(1, 'N° EMB'), (2, 'F. Zarpe'), (3, 'Sem ETD'), (4, 'Cargar Hasta'), (5, 'Sem Carga'),
                  (6, 'Cliente'), (7, 'País'), (8, 'Contrato Interno'), (9, 'Contrato Cliente'), (10, 'N° Pedido Odoo'),
                  (11, 'N° Despacho Odoo'), (12, 'Estatus Producción'), (13, 'Estatus Despacho'),
                  (14, 'Estado A. Calidad'),
                  (15, 'F. Envío al cliente'), (16, 'Especie'), (17, 'Variedad'), (18, 'Color'), (19, 'Producto'),
                  (20, 'Calibre'),
                  (21, 'Kilos'), (22, 'Precio'), (23, 'Monto'), (24, 'N° Factura'), (25, 'Cláusula'), (26, 'Envase'),
                  (27, 'Modo de Carga'),
                  (28, 'Etiqueta Cliente'), (29, 'Marca'), (30, 'Agente'), (31, 'Comisión'), (32, 'Valor Comisión'),
                  (33, 'Puerto de Carga'),
                  (34, 'Puerto de Destino'), (35, 'Destino Final'), (36, 'Vía de Transporte'), (37, 'Planta de Carga'),
                  (38, 'Fecha y Hora Carga'), (39, 'N° de Guía'), (40, 'Nave / Viaje'), (41, 'Naviera'),
                  (42, 'N° Booking'),
                  (43, 'N° BL'), (44, 'Stacking'), (45, 'Cut Off Documental'), (46, 'F. Real Zarpe'),
                  (47, 'F. Real Arribo'),
                  (48, 'N° Container'), (49, 'Tipo Container'), (50, 'Terminal Portuario Origen'),
                  (51, 'Depósito Retiro'),
                  (52, 'Valor Flete'), (53, 'Valor Seguro'), (54, 'FOB Total'), (55, 'FOB /Kg'), (56, 'Obs. Calidad'),
                  (57, 'Comentarios'), (58, 'N° DUS')]

        sheet.set_row(0, cell_format=formats['title'])
        for title in titles:
            sheet.write(row, col, title[1])
            col += 1
        row += 1
        col = 0

        from_date = '{}/01/01'.format(str(self.for_year))
        to_date = '{}/12/31'.format(str(self.for_year))

        # orders = self.env['sale.order'].sudo().search([('confirmation_date','>=',from_date),('confirmation_date','<=',to_date)])
        orders = self.env['sale.order'].sudo().search(
            [('create_date', '>=', from_date), ('create_date', '<=', to_date)])
        total_kilogram = 0
        total_amount = 0
        total_commission = 0
        total_bl = 0  # counter
        total_container = 0  # counter
        total_freight = 0
        total_safe = 0
        total_fob = 0
        total_fob_per_kilo = 0

        amount_total_invoice_ids = []
        other_fields_invoice_ids = []
        commission_invoice_ids = []

        if len(orders) > 0:
            for order in orders:
                # productions = self.env['mrp.production'].search([('sale_order_id',order.id)])
                stock_picking_ids = self.env['stock.picking'].sudo().search([('sale_id', '=', order.id),('state','!=','cancel')])
                # if len(stock_picking_ids) > 0:
                for stock in stock_picking_ids:
                    invoice_line = self.env['account.invoice.line'].sudo().search([('stock_picking_id', '=', stock.id)])
                    production = self.env['mrp.production'].sudo().search([('stock_picking_id', '=', stock.id)])
                    exist_account_invoice = False
                    if invoice_line:
                        exist_account_invoice = True
                        account_invoice = self.env['account.invoice'].sudo().search(
                            [('id', '=', invoice_line[0].invoice_id.id)])
                    # N° Embarque
                    sheet.write(row, col, stock.shipping_number if stock.shipping_number else '')
                    col += 1
                    # Fecha de Zarpe
                    sheet.write(row, col, stock.departure_date.strftime("%d-%m-%Y") if stock.departure_date else '')
                    col += 1
                    # Semana ETD
                    sheet.write(row, col, stock.etd_week)
                    col += 1
                    # Cargar Hasta
                    sheet.write(row, col,
                                stock.required_loading_date.strftime("%d-%m-%Y") if stock.required_loading_date else '')
                    col += 1
                    # Semana Carga
                    sheet.write(row, col, stock.required_loading_week)
                    col += 1
                    # Cliente
                    sheet.write(row, col, stock.partner_id.name if stock.partner_id.name else '')
                    col += 1
                    # Pais
                    sheet.write(row, col, stock.partner_id.country_id.name if stock.partner_id.country_id.name else '')
                    col += 1
                    # Contrato Interno
                    sheet.write(row, col, order.contract_number if order.contract_number else '')
                    col += 1
                    # Contrato Cliente
                    sheet.write(row, col, '')  # order.client_contract)
                    col += 1
                    # N° Pedido Odoo
                    sheet.write(row, col, order.name)
                    # sheet.write_url(row, col, f'https://dimabe-odoo-la-invernada-test-2148713.dev.odoo.com/web?#id={order.id}&action=259', order.name)
                    col += 1
                    # N° Stock Picking Odoo
                    sheet.write(row, col, stock.name)
                    col += 1
                    # Estatus Produccion
                    if production:
                        if len(production) == 1:
                            if production.state == 'planned':
                                sheet.write(row, col, 'Planeado', formats['pink_status'])
                            elif production.state == 'done':
                                sheet.write(row, col, 'Realizado', formats['green_status'])
                            elif production.state == 'progress':
                                sheet.write(row, col, 'En Progreso', formats['light_green_status'])
                            elif production.state == 'confirmed':
                                sheet.write(row, col, 'Confirmado', formats['yellow_status'])
                            elif production.state == 'cancel':
                                sheet.write(row, col, 'Cancelado', formats['red_status'])
                        else:
                            status_set = ''
                            status_type = []
                            for p in production:
                                if p.state not in status_type:
                                    status_type.append(p.state)

                            for state in status_type:
                                currency_state = ''
                                if state == 'planned':
                                    currency_state = 'Planeado'
                                elif state == 'done':
                                    currency_state = 'Realizado'
                                elif state == 'progress':
                                    currency_state = 'En Progreso'
                                elif state == 'confirmed':
                                    currency_state = 'Confirmado'
                                elif state == 'cancel':
                                    currency_state = 'Cancelado'
                                status_set += currency_state + ' '
                            sheet.write(row, col, status_set)
                    else:
                        sheet.write(row, col, 'Sin Órden de Producción')
                    col += 1
                    # Estatus Despacho
                    if exist_account_invoice:
                        if account_invoice.arrival_date:
                            sheet.write(row, col, 'Arrivado', formats['green_status'])
                        else:
                            if stock.state == 'draft':
                                sheet.write(row, col, 'Borrador')
                            elif stock.state == 'assigned':
                                sheet.write(row, col, 'Asignado', formats['pink_status'])
                            elif stock.state == 'confirmed':
                                sheet.write(row, col, 'Confirmado', formats['yellow_status'])
                            elif stock.state == 'done':
                                sheet.write(row, col, 'Realizado', formats['light_green_status'])
                            elif stock.state == 'cancel':
                                sheet.write(row, col, 'Cancelado', formats['red_status'])
                    else:
                        if stock.state == 'draft':
                            sheet.write(row, col, 'Borrador')
                        elif stock.state == 'assigned':
                            sheet.write(row, col, 'Asignado', formats['pink_status'])
                        elif stock.state == 'confirmed':
                            sheet.write(row, col, 'Confirmado', formats['yellow_status'])
                        elif stock.state == 'done':
                            sheet.write(row, col, 'Realizado', formats['light_green_status'])
                        elif stock.state == 'cancel':
                            sheet.write(row, col, 'Cancelado', formats['red_status'])
                    col += 1
                    # Estatus Calidad
                    if exist_account_invoice:
                        if account_invoice.quality_status == 'Pendiente':
                            sheet.write(row, col, account_invoice.quality_status, formats['pink_status'])
                        elif account_invoice.quality_status == 'Recibido':
                            sheet.write(row, col, account_invoice.quality_status, formats['yellow_status'])
                        elif account_invoice.quality_status == 'Enviado':
                            sheet.write(row, col, account_invoice.quality_status, formats['light_green_status'])
                        elif account_invoice.quality_status == 'Cancelado':
                            sheet.write(row, col, account_invoice.quality_status, formats['red_status'])

                    else:
                        sheet.write(row, col, '')
                    col += 1
                    # Fecha Envio al Cliente
                    if exist_account_invoice:
                        sheet.write(row, col, account_invoice.shipping_date_to_customer.strftime(
                            "%d-%m-%Y") if account_invoice.shipping_date_to_customer else '')
                    else:
                        sheet.write(row, col, '')
                    col += 1

                    product_set = ''
                    price_set = ''
                    species = []
                    varieties = []
                    colors = []
                    calibers = []
                    brands = []
                    cannings = []

                    for line in order.order_line:
                        for item in invoice_line:
                            if line.product_id.id == item.product_id.id:
                                price_set += str(item.price_unit) + ' '
                        product_set += line.product_id.name + ' '
                        for attribute in line.product_id.attribute_value_ids:
                            if attribute.attribute_id.name == 'Variedad':
                                if attribute.name not in varieties:
                                    varieties.append(attribute.name)
                            if attribute.attribute_id.name == 'Marca':
                                if attribute.name not in brands:
                                    brands.append(attribute.name)
                            if attribute.attribute_id.name == 'Tipo de envase':
                                if attribute.name not in cannings:
                                    cannings.append(attribute.name)
                            if attribute.attribute_id.name == 'Calibre':
                                if attribute.name not in calibers:
                                    calibers.append(attribute.name)
                            if attribute.attribute_id.name == 'Especie':
                                if attribute.name not in species:
                                    species.append(attribute.name)
                            if attribute.attribute_id.name == 'Color':
                                if attribute.name not in colors:
                                    colors.append(attribute.name)

                    # Especie
                    sheet.write(row, col, ' '.join([s for s in species]))
                    col += 1
                    # Variedad
                    sheet.write(row, col, ' '.join([v for v in varieties]))
                    col += 1
                    # Color
                    sheet.write(row, col, ' '.join([c for c in colors]))
                    col += 1
                    # Producto
                    sheet.write(row, col, product_set)
                    col += 1
                    # Calibre
                    sheet.write(row, col, ' '.join([ca for ca in calibers]))
                    col += 1
                    # Kilos
                    if len(stock.move_ids_without_package.filtered(lambda x: x.product_id.id in order.order_line.mapped(
                            'product_id').ids)) > 0 and stock.state == 'done':
                        quantity_done = sum(line.quantity_done for line in stock.move_ids_without_package.filtered(
                            lambda x: x.product_id.id in order.order_line.mapped('product_id').ids))
                        total_kilogram += quantity_done
                        sheet.write(row, col, quantity_done)
                    elif stock.backorder_id and stock.state != 'cancel':
                        if stock.state != 'done':
                            order_kgs = Enumerable(stock.move_ids_without_package).where(
                                lambda x: x.product_id.id in order.order_line.mapped('product_id').ids).sum(
                                lambda x: x.product_uom_qty)
                        else:
                            order_kgs = Enumerable(stock.move_ids_without_package).where(
                                lambda x: x.product_id.id in order.order_line.mapped('product_id').ids).sum(
                                lambda x: x.quantity_done)
                        sheet.write(row, col, order_kgs)
                    else:
                        order_kgs = Enumerable(order.order_line).sum(lambda x: x.product_uom_qty)
                        sheet.write(row, col, order_kgs)
                    col += 1
                    # Precio
                    sheet.write(row, col, price_set)
                    col += 1

                    if exist_account_invoice:
                        if account_invoice.id not in amount_total_invoice_ids:
                            amount_total_invoice_ids.append(account_invoice.id)  # para mostrar solo una vez el FOB
                            if account_invoice.total_value > 0:
                                total_fob += account_invoice.total_value
                            if account_invoice.value_per_kilogram > 0:
                                total_fob_per_kilo += account_invoice.value_per_kilogram
                            total_freight += account_invoice.freight_amount
                            total_safe += account_invoice.safe_amount
                            total_amount += account_invoice.amount_total
                            total_commission += account_invoice.total_commission
                            # Monto
                            sheet.write(row, col, account_invoice.amount_total)

                    col += 1
                    # N° Factura
                    if exist_account_invoice:
                        sheet.write(row, col, account_invoice.dte_folio if account_invoice.dte_folio else '')
                    else:
                        sheet.write(row, col, "")
                    col += 1
                    # Cláusula
                    if exist_account_invoice:
                        sheet.write(row, col,
                                    account_invoice.export_clause.name if account_invoice.export_clause else '')
                    else:
                        sheet.write(row, col, "")
                    col += 1
                    # Envase
                    sheet.write(row, col, ' '.join([e for e in cannings]))
                    col += 1
                    # Modo de carga
                    if exist_account_invoice:
                        sheet.write(row, col, account_invoice.charging_mode if account_invoice.charging_mode else '')
                    else:
                        sheet.write(row, col, "")
                    col += 1
                    # Etiqueta Cliente
                    if exist_account_invoice:
                        if account_invoice.client_label:
                            sheet.write(row, col, 'Si')
                        else:
                            sheet.write(row, col, 'No')
                    else:
                        sheet.write(row, col, '')
                    col += 1
                    # Marca
                    sheet.write(row, col, ' '.join([b for b in brands]))
                    col += 1
                    # Agente
                    sheet.write(row, col, stock.agent_id.name if stock.agent_id else '')
                    col += 1
                    if exist_account_invoice:
                        # Comisión
                        sheet.write(row, col, f'{stock.commission}%' if account_invoice.commission else '')
                        col += 1
                        # Valor Comisión
                        if exist_account_invoice not in commission_invoice_ids:
                            commission_invoice_ids.append(account_invoice.id)
                            sheet.write(row, col, account_invoice.total_commission)
                        else:
                            sheet.write(row, col, '0')
                    else:
                        col += 1
                    col += 1
                    # Puerto de Carga
                    sheet.write(row, col, stock.departure_port.name if stock.departure_port else '')
                    col += 1
                    # Puerto de Destino
                    sheet.write(row, col, stock.arrival_port.name if stock.arrival_port else '')
                    col += 1
                    # Destino Final
                    if exist_account_invoice:
                        sheet.write(row, col,
                                    account_invoice.city_final_destiny_id.city_country if account_invoice.city_final_destiny_id.city_country else '')
                    else:
                        sheet.write(row, col, "")
                    col += 1
                    # Vía de Transporte
                    sheet.write(row, col, stock.type_transport.name if stock.type_transport else '')
                    col += 1
                    # Planta de Carga
                    if exist_account_invoice:
                        sheet.write(row, col, account_invoice.plant.name if account_invoice.plant else '')
                    else:
                        sheet.write(row, col, "")
                    col += 1
                    # Fecha y Hora de Carga
                    sheet.write(row, col, stock.required_loading_date.strftime(
                        "%d-%m-%Y") if stock.required_loading_date else '', )
                    col += 1
                    # N° de Guía
                    sheet.write(row, col, stock.dte_folio if stock.dte_folio else '')
                    col += 1
                    # Nave / Viaje
                    sheet.write(row, col, stock.ship.name if stock.ship else '')
                    col += 1
                    # Naviera
                    sheet.write(row, col, stock.shipping_company.name if stock.shipping_company else '')
                    col += 1
                    # N° Booking
                    sheet.write(row, col, stock.booking_number if stock.booking_number else '')
                    col += 1
                    # N° BL
                    if stock.bl_number:
                        sheet.write(row, col, stock.bl_number)
                        total_bl += 1
                    else:
                        sheet.write(row, col, "")
                    col += 1
                    # Stacking
                    if exist_account_invoice:
                        sheet.write(row, col, account_invoice.stacking if account_invoice.stacking else '')
                    else:
                        sheet.write(row, col, "")
                    col += 1
                    # Cut Off Document
                    if exist_account_invoice:
                        sheet.write(row, col, account_invoice.cut_off if account_invoice.cut_off else '')
                    else:
                        sheet.write(row, col, "")
                    col += 1
                    # Fecha Real de Zarpe
                    sheet.write(row, col, stock.departure_date.strftime("%d-%m-%Y") if stock.departure_date else '')
                    col += 1
                    # Fecha Real Arribo
                    sheet.write(row, col, stock.arrival_date.strftime("%d-%m-%Y") if stock.arrival_date else '')
                    col += 1
                    # N° Container
                    if stock.container_number:
                        sheet.write(row, col, stock.container_number)
                        total_container += 1
                    else:
                        sheet.write(row, col, '')
                    col += 1
                    # Tipo Container
                    sheet.write(row, col, stock.container_type.name if stock.container_type else '')
                    col += 1
                    # Terminal Portuario Origen
                    if exist_account_invoice:
                        sheet.write(row, col,
                                    account_invoice.port_terminal_origin if account_invoice.port_terminal_origin else '')
                    else:
                        sheet.write(row, col, '')
                    col += 1
                    # Depósito Retiro
                    if exist_account_invoice:
                        sheet.write(row, col,
                                    account_invoice.withdrawal_deposit.name if account_invoice.withdrawal_deposit else '')
                    else:
                        sheet.write(row, col, "")
                    col += 1

                    if exist_account_invoice:
                        if account_invoice.id not in other_fields_invoice_ids:
                            other_fields_invoice_ids.append(account_invoice.id)
                            # Valor Flete
                            sheet.write(row, col, account_invoice.freight_amount)
                            col += 1
                            # Valor Seguro
                            sheet.write(row, col, account_invoice.safe_amount)
                            col += 1
                            # FOB TOTAL
                            sheet.write(row, col, account_invoice.total_value if account_invoice.total_value > 0 else 0)
                            col += 1
                            # FOB POR KILO
                            sheet.write(row, col,
                                        account_invoice.value_per_kilogram if account_invoice.value_per_kilogram > 0 else 0)
                        else:
                            sheet.write(row, col, '0')
                            col += 1
                            sheet.write(row, col, '0')
                            col += 1
                            sheet.write(row, col, '0')
                            col += 1
                            sheet.write(row, col, '0')
                    else:
                        col += 3
                    col += 1
                    # Obs. Calidad
                    if exist_account_invoice:
                        sheet.write(row, col,
                                    account_invoice.quality_remarks if account_invoice.quality_remarks else '')
                    else:
                        sheet.write(row, col, '')
                    col += 1
                    # Comentarios
                    sheet.write(row, col, stock.remarks if stock.remarks else '')
                    col += 1
                    # N° DUS
                    sheet.write(row, col, stock.dus_number if stock.dus_number else '')
                    col += 1

                    row += 1
                    col = 0

        # Header Format
        sheet.set_column('F:F', 35)
        sheet.set_column('G:G', 24)
        sheet.set_column('H:H', 16)
        sheet.set_column('J:J', 12)
        sheet.set_column('L:L', 12)
        sheet.set_column('M:M', 12)
        sheet.set_column('N:N', 12)
        sheet.set_column('O:O', 12)
        sheet.set_column('P:P', 18)
        sheet.set_column('Q:Q', 12)
        sheet.set_column('S:S', 50)
        sheet.set_column('T:T', 20)
        sheet.set_column('Y:Y', 24)
        sheet.set_column('Z:Z', 20)
        sheet.set_column('AA:AA', 12)
        sheet.set_column('AC:AC', 12)
        sheet.set_column('AD:AD', 25)
        sheet.set_column('AG:AG', 15)
        sheet.set_column('AH:AH', 15)
        sheet.set_column('AJ:AJ', 20)
        sheet.set_column('AJ:AJ', 28)
        sheet.set_column('AK:AK', 28)
        sheet.set_column('AL:AL', 12)
        sheet.set_column('AN:AN', 20)
        sheet.set_column('AO:AO', 12)
        sheet.set_column('AP:AP', 14)
        sheet.set_column('AQ:AQ', 14)
        sheet.set_column('AR:AR', 20)
        sheet.set_column('AS:AS', 20)
        sheet.set_column('AT:AT', 10)
        sheet.set_column('AU:AU', 10)
        sheet.set_column('AV:AV', 15)
        sheet.set_column('AW:AW', 15)
        sheet.set_column('AY:AY', 18)
        sheet.set_column('AO:AO', 12)
        sheet.set_column('AP:AP', 14)
        sheet.set_column('BD:BD', 40)
        sheet.set_column('BE:BE', 40)
        sheet.set_column('BF:BF', 30)
        # Total
        row += 1
        sheet.set_row(row, cell_format=formats['title'])
        sheet.write(row, 0, "Total", formats['title'])
        sheet.write(row, 20, f'{total_kilogram}', formats['title'])
        sheet.write(row, 22, f'{total_amount}', formats['title'])
        sheet.write(row, 31, f'{total_commission}', formats['title'])
        sheet.write(row, 42, f'{total_bl}', formats['title'])
        sheet.write(row, 47, f'{total_container}', formats['title'])
        sheet.write(row, 51, f'{total_freight}', formats['title'])
        sheet.write(row, 52, f'{total_safe}', formats['title'])
        sheet.write(row, 53, f'{total_fob}', formats['title'])
        sheet.write(row, 54, f'{total_fob_per_kilo}', formats['title'])

        workbook.close()
        with open(file_name, "rb") as file:
            file_base64 = base64.b64encode(file.read())

        file_name = 'Archivo de Pedidos - {}'.format(self.for_year)
        attachment_id = self.env['ir.attachment'].sudo().create({
            'name': file_name,
            'datas_fname': file_name,
            'datas': file_base64
        })
        action = {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment_id.id, ),
            'target': 'current',
        }
        return action

    def set_formats(self, workbook):
        merge_format_string = workbook.add_format({
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
        })
        merge_format_number = workbook.add_format({
            'bold': 0,
            'align': 'center',
            'valign': 'vcenter',
            'num_format': '#,##0'
        })
        merge_format_title = workbook.add_format({
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#8064a2',
            'font_color': 'white',
            'text_wrap': True
        })
        merge_format_red_status = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#c30f0f',
            'font_color': 'white',
        })
        merge_format_yellow_status = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#ffeb9c',
            'font_color': 'black',
        })
        merge_format_light_green_status = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#c6efce',
            'font_color': '#50612e',
        })
        merge_format_green_status = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#87c842',
            'font_color': 'black',
        })
        merge_format_pink_status = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#ffc7ce',
            'font_color': '#9c0031',
        })
        return {
            'string': merge_format_string,
            'number': merge_format_number,
            'title': merge_format_title,
            'red_status': merge_format_red_status,
            'yellow_status': merge_format_yellow_status,
            'green_status': merge_format_green_status,
            'light_green_status': merge_format_light_green_status,
            'pink_status': merge_format_pink_status
        }
