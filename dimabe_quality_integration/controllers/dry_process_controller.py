from odoo import http, exceptions, models
from odoo.http import request
from datetime import date, timedelta
import werkzeug


class DryProcessController(http.Controller):

    @http.route('/api/dry_process', type='json', methods=['GET'], auth='token', cors='*')
    def get_dry_process(self, sinceDate=None):
        search_date = sinceDate or (date.today() - timedelta(days=7))
        result = request.env['dried.unpelled.history'].sudo().search([('write_date', '>', search_date)])
        processResult = []
        for res in result:
            if res.finish_date:
                processResult.append({
                    'name': res.name,
                    'inLotIds': res.mapped('in_lot_ids.name'),
                    'initDate': res.init_date or res.create_date,
                    'guideNumbers': res.lot_guide_numbers,
                    'finishDate': res.finish_date or res.write_date,
                    'productName': res.in_product_id.name,
                    'productId': res.in_product_id.id,
                    'productVariety': res.in_product_variety,
                    'outLot': res.out_lot_id.name,
                    'producerName': res.producer_id.name,
                    'producerId': res.producer_id.id,
                    'totalInWeight': res.total_in_weight,
                    'totalOutWeight': res.total_out_weight,
                    'performance': res.performance,
                    'OdooUpdatedAt': res.write_date
                })


        result_receptions = request.env['stock.picking'].search([('state','=','done'), ('picking_type_id.require_dried', '=', True),('write_date', '>', search_date)]).filtered(lambda x: x.name not in result.mapped('in_lot_ids.name'))

        for reception in result_receptions:
            product_id =  reception.move_line_ids_without_package.filtered(lambda x: x.lot_id)[0]
            processResult.append({
                    'name': '{} {}'.format(reception.partner_id.name,product_id.display_name),
                    'inLotIds': [reception.name],
                    'initDate': reception.date_done,
                    'guideNumbers': reception.guide_number,
                    'finishDate': reception.write_date,
                    'productName': reception.product_id.name,
                    'productId': reception.product_id.id,
                    'productVariety': reception.product_id.get_variety(),
                    'outLot': '',
                    'producerName': reception.partner_id.name,
                    'producerId': reception.partner_id.id,
                    'totalInWeight': reception.net_weight,
                    'totalOutWeight': 0,
                    'performance': 0,
                    'OdooUpdatedAt': reception.write_date
                })



        return processResult

    def get_guide_number(self,res):
        tmp = ''
        for guide_number in res.in_lot_ids.mapped('reception_guide_number'):
            tmp += '{} '.format(guide_number)
        return tmp