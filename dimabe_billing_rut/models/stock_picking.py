from odoo import models, fields, api
import json
import requests
from datetime import date
import re

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    dte_folio = fields.Text(string='Folio DTE')
    dte_type_id =  fields.Many2one(
        'dte.type', string = 'Tipo Documento'
    )
    dte_xml = fields.Text("XML")
    dte_pdf = fields.Text("PDF")
    ted = fields.Text("TED")
    pdf_url = fields.Text("URL PDF")

    partner_economic_activities = fields.Many2many('custom.economic.activity',related='partner_id.economic_activities')
    company_economic_activities = fields.Many2many('custom.economic.activity', related='company_id.economic_activities')
    partner_activity_id = fields.Many2one('custom.economic.activity', string='Actividad del Proveedor')
    company_activity_id = fields.Many2one('custom.economic.activity', string='Actividad de la Compañía')
    references = fields.One2many(
        'account.invoice.references',
        'invoice_id',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    method_of_payment = fields.Selection(
        [
            ('1', 'Contado'),
            ('2', 'Crédito'),
            ('3', 'Gratuito')
        ],
        string="Forma de pago",
        readonly=True,
        states={'draft': [('readonly', False)]},
        default='1',
    )

    observations_ids = fields.One2many('custom.invoice.observations','invoice_id',string='Observaciones')


    @api.onchange('partner_id')
    @api.multi
    def _compute_partner_activity(self):
        for item in self:
            activities = []
            for activity in item.partner_id.economic_activities:
                activities.append(activity.id)
            item.partner_activity_id = activities
    
    #eliminar
    @api.one
    def send_to_sii_old(self):
        #PARA COMPLETAR EL DOCUMENTO SE DEBE BASAR EN http://www.sii.cl/factura_electronica/formato_dte.pdf
        if not self.company_activity_id or not self.partner_activity_id:
            raise models.ValidationError('Por favor seleccione las actividades de la compañía y del proveedor')
        if not self.company_id.invoice_rut or not self.partner_id.invoice_rut:
            raise models.ValidationError('No se encuentra registrado el rut de facturación')

        if not self.dte_type_id:
            raise models.ValidationError('Por favor seleccione tipo de documento a emitir')
        if not self.company_activity_id or not self.partner_activity_id:
            raise models.ValidationError('Debe seleccionar el giro de la compañí y proveedor a utilizar')

        dte = {}
        dte["Encabezado"] = {}
        dte["Encabezado"]["IdDoc"] = {}
        # El Portal completa los datos del Emisor
        dte["Encabezado"]["IdDoc"] = {"TipoDTE": self.dte_type_id.code}
        #Si es Boleta de debe indicar el tipo de servicio, por defecto de venta de servicios
        if self.dte_type_id.code in ('39', 39):
            dte["Encabezado"]["IdDoc"]["IndServicio"] = 3

        if not self.dte_type_id.code in ('39', 39):
            #Se debe inicar SOLO SI los valores indicados en el documento son con iva incluido
            dte["Encabezado"]["IdDoc"]["MntBruto"] = 1

        #EL CAMPO RUT DE FACTURACIÓN, debe corresponder al RUT de la Empresa
        dte["Encabezado"]["Emisor"] = {"RUTEmisor": self.company_id.invoice_rut.replace(".","")}

        # EL CAMPO VAT o NIF Del Partner, debe corresponder al RUT , si es empresa extranjera debe ser 55555555-5
        dte["Encabezado"]["Receptor"] = {"RUTRecep": self.partner_id.invoice_rut.replace(".",""),
                                         "RznSocRecep": self.partner_id.name,
                                         "DirRecep": self.partner_id.street +  ' ' + self.partner_id.city,
                                         "CmnaRecep": self.partner_id.city,
                                         "GiroRecep": self.partner_activity_id.name}
        
        dte["Encabezado"]["IdDoc"]["TermPagoGlosa"] = self.note or ''
        dte["Encabezado"]["IdDoc"]["Folio"] = '0'
        dte["Encabezado"]["IdDoc"]["FchEmis"] = str(date.today())
        dte["Detalle"] = []
        for line in self.move_ids_without_package:
            #El Portal Calculos los Subtotales
            ld = {'NmbItem': line.product_id.name,
             'DscItem': line.product_id.display_name,
             'QtyItem': round(line.quantity_done, 6),
             'PrcItem': round(line.product_id.lst_price,4)
            }
            if line.product_id.default_code:
                ld['CdgItem'] = {"TpoCodigo": "INT1",
                              "VlrCodigo": line.product_id.default_code}

            dte["Detalle"].append(ld)
        referencias = []
        for reference in self.references:
            ref = {'TpoDocRef':reference.document_type_reference_id.code or 'SET',
                   'FolioRef':reference.folio_reference,
                   'FchRef':reference.document_date.__str__(),
                   'RazonRef':reference.reason}
            if reference.code_reference:
                ref['CodRef'] =reference.code_reference
            referencias.append(ref)
        if referencias:
            dte['Referencia'] = referencias

        self.send_dte(json.dumps(dte))
    #eliminar
    def send_dte(self, dte):
        url = self.company_id.dte_url
        rut_emisor = self.company_id.invoice_rut.replace(".", "").split("-")[0]
        hash = self.company_id.dte_hash
        auth = requests.auth.HTTPBasicAuth(hash, 'X')
        ssl_check = False
        # Api para Generar DTE
        apidte = '/dte/documentos/gendte?getXML=true&getPDF=true&getTED=png'
        emitir = requests.post(url + '/api' + apidte, dte, auth=auth, verify=ssl_check)
        if emitir.status_code != 200:
            raise Exception('Error al Temporal: ' + emitir.json())
        data = emitir.json()
        self.dte_folio = data.get('folio', None)
        self.dte_xml = data.get("xml", None)
        self.dte_pdf = data.get('pdf', None)
        self.ted = data.get("ted", None)
        fecha = data.get("fecha", None)
        total = data.get("total", None)
        self.pdf_url = "%s/dte/dte_emitidos/pdf/%s/%s/0/%s/%s/%s" % (url, self.dte_type_id.code, self.dte_folio, rut_emisor, fecha, total)


    @api.one
    def send_to_sii(self):
        url = self.env.user.company_id.dte_url
        headers = {
            "apiKey" : self.env.user.company_id.dte_hash,
            "CustomerCode": self.env.user.company_id.dte_customer_code
        }
        invoice = {}
        productLines = []
        lineNumber = 1
        typeOfExemptEnum = ""
        netAmount = 0
        countNotExempt = 0

        #Main Validations
        self.validation_fields()

        for item in self.move_line_ids_without_package:
            raise models.ValidationError(type(item))
            netAmount += int(item.price_subtotal)
            productLines.append(
                    {
                        "LineNumber": str(lineNumber),
                        "ProductTypeCode": "EAN",
                        "ProductCode": str(item.product_id.default_code),
                        "ProductName": item.name,
                        "ProductQuantity": str(item.quantity), #segun DTEmite no es requerido int
                        "UnitOfMeasure": str(item.uom_id.name),
                        "ProductPrice": str(item.price_unit), #segun DTEmite no es requerido int
                        "ProductDiscountPercent": "0",
                        "DiscountAmount": "0",
                        "Amount": str(int(item.price_subtotal)),
                    }
                )
            lineNumber += 1
        
        if self.partner_id.phone:
            recipientPhone = str(self.partner_id.phone)
        elif self.partner_id.mobile:
            recipientPhone = str(self.partner_id.mobile)
        else:
            recipientPhone = ''

        invoice= {
            "dteType": self.dte_type_id.code,
            "createdDate": self.date_invoice.strftime("%Y-%m-%d"),
            "expirationDate": self.date_due.strftime("%Y-%m-%d"),
            "paymentType": int(self.method_of_payment),
            "transmitter": {
                "EnterpriseRut": re.sub('[\.]','', "11.111.111-1"), #self.env.user.company_id.invoice_rut,
                "EnterpriseActeco": self.company_activity_id.code,
                "EnterpriseAddressOrigin": self.env.user.company_id.street,
                "EnterpriseCity": self.env.user.company_id.city,
                "EnterpriseCommune": str(self.env.user.company_id.state_id.name),
                "EnterpriseName": self.env.user.company_id.partner_id.name,
                "EnterpriseTurn": self.company_activity_id.name,
                "EnterprisePhone": self.env.user.company_id.phone if self.env.user.company_id.phone else ''
            },
            "recipient": {
                "EnterpriseRut": re.sub('[\.]','', self.partner_id.invoice_rut),
                "EnterpriseAddressOrigin": self.partner_id.street[0:60],
                "EnterpriseCity": self.partner_id.city,
                "EnterpriseCommune": self.partner_id.state_id.name,
                "EnterpriseName": self.partner_id.name,
                "EnterpriseTurn": self.partner_activity_id.name,
                "EnterprisePhone": recipientPhone
            },
            "total": {
                "netAmount": str(netAmount),
                "exemptAmount": "0",
                "taxRate": "19",
                "taxtRateAmount": str(int(self.amount_tax)),
                "totalAmount": str(int(netAmount + self.amount_tax))
            },
            "lines": productLines,
        }
        
        # Add Refeences
        if self.references and len(self.references) > 0:
            refrenecesList = []
            line_reference_number = 1
            for item in self.references:
                refrenecesList.append(
                    {
                        "LineNumber": str(line_reference_number),
                        "DocumentType": str(item.document_type_reference_id.id),
                        "Folio": str(item.folio_reference),
                        "Date": str(item.document_date),
                        "Code": str(item.code_reference),
                        "Reason": str(item.reason)
                    }
                )
                line_reference_number += 1
            invoice['references'] = refrenecesList
        #Add Additionals
        if len(self.observations_ids) > 0:
            additionals = []
            for item in self.observations_ids:
                additionals.append(item.observations)
            invoice['additional'] =  additionals    


        r = requests.post(url, json=invoice, headers=headers)

        #raise models.ValidationError(json.dumps(invoice))

        jr = json.loads(r.text)

        Jrkeys = jr.keys()
        if 'urlPdf' in Jrkeys  and 'filePdf' in Jrkeys and 'folio' in Jrkeys and 'fileXml' in Jrkeys:
            self.write({'pdf_url':jr['urlPdf']})
            self.write({'dte_pdf':jr['filePdf']})
            self.write({'dte_folio':jr['folio']})
            self.write({'dte_xml':jr['fileXml']})
      
        if 'status' in Jrkeys and 'title' in Jrkeys:
            raise models.ValidationError('Status: {} Title: {} Json: {}'.format(jr['status'],jr['title'],json.dumps(invoice)))
        elif 'message' in Jrkeys:
            raise models.ValidationError('Advertencia: {} Json: {}'.format(jr['message'],json.dumps(invoice)))


    def validation_fields(self):
        if not self.partner_id:
            raise models.ValidationError('Por favor selccione el Cliente')
        else:
            if not self.partner_id.invoice_rut:
                raise models.ValidationError('El Cliente {} no tiene Rut de Facturación'.format(self.partner_id.name))

        if not self.dte_type_id.code:
            raise models.ValidationError('Por favor seleccione el Tipo de Documento a emitir')

            if len(self.move_ids_without_package) == 0:
                raise models.ValidationError('Por favor agregar al menos un Producto')

        if not self.company_activity_id or not self.partner_activity_id:
            raise models.ValidationError('Por favor seleccione la Actividad de la Compañía y del Proveedor')

        if len(self.references) > 10:
            raise models.ValidationError('Solo puede generar 20 Referencias')

        if len(self.observations_ids) > 10: 
            raise models.ValidationError('Solo puede generar 10 Observaciones')