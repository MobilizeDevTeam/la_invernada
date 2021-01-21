from odoo import http
from odoo.http import request
import json
import datetime
import logging
from odoo.tools import date_utils
from odoo.addons.web.controllers.main import serialize_exception,content_disposition
import base64

class Binary(http.Controller):
    @http.route('/web/binary/download_document', type='http', auth="public")
    @serialize_exception
    def download_document(self, model, field, id, filename=None, **kw):
        """ Download link for files stored as binary fields.
        :param str model: name of the model to fetch the binary from
        :param str field: binary field
        :param str id: id of the record from which to fetch the binary
        :param str filename: field holding the file's name, if any
        :returns: :class:`werkzeug.wrappers.Response`
        """
        Model = request.registry[model]
        cr, uid, context = request.cr, request.uid, request.context
        fields = [field]
        res = Model.read(cr, uid, [int(id)], fields, context)[0]
        filecontent = base64.b64decode(res.get(field) or '')
        if not filecontent:
            return request.not_found()
        else:
            if not filename:
                filename = '%s_%s' % (model.replace('.', '_'), id)
                return request.make_response(filecontent,
                                             [('Content-Type', 'application/octet-stream'),
                                              ('Content-Disposition', content_disposition(filename))])

    @http.route('/api/indicators',method=['GET'], type='json', auth='token', cors='*')
    @serialize_exception
    def get_indicators(self):
        response = request.env['hr.indicadores'].sudo().search([])
        result = []
        for item in response:
            raw_data = item.read()
            json_data = json.dumps(raw_data, default=date_utils.json_default)
            json_dict = json.loads(json_data)
            result.append(json_dict)

        return result

    @http.route('/api/payslips', type='json', auth='token', cors='*')
    @serialize_exception
    def get_payslip(self, indicator_id):
        response = request.env['hr.payslip'].sudo().search([('indicadores_id', '=', indicator_id)])
        result = []
        for item in response:
            raw_data = item.read()
            json_data = json.loads(raw_data, default=date_utils.json_default)
            json_dict = json.loads(json_data)
            result.append(json_dict)

        return result

    @http.route('/api/line', type='json', auth='token', cors='*')
    @serialize_exception
    def get_lines(self, slip_id):
        response = request.env['hr.payslip.line'].sudo().search([('slip_id', '=', slip_id)])
        result = []
        for item in response:
            raw_data = item.read()
            json_data = json.loads(raw_data, default=date_utils.json_default)
            json_dict = json.loads(json_data)
            result.append(json_dict)

        return result

