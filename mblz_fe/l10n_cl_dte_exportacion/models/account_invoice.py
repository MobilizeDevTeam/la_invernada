# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.addons.l10n_cl_fe.models.currency import float_round_custom as round
import logging
_logger = logging.getLogger(__name__)


class Exportacion(models.Model):
    _inherit = "account.invoice"

    exportacion = fields.Many2one(
        string="Detalles Exportación",
        comodel_name="account.invoice.exportacion",
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False,
    )
    pais_destino = fields.Many2one(
        'aduanas.paises',
        related="exportacion.pais_destino",
        string='País de Destino',
        readonly=False,
    )
    puerto_embarque = fields.Many2one(
        'aduanas.puertos',
        related="exportacion.puerto_embarque",
        string='Puerto Embarque',
        readonly=False,
    )
    puerto_desembarque = fields.Many2one(
        'aduanas.puertos',
        related="exportacion.puerto_desembarque",
        string='Puerto de Desembarque',
        readonly=False,
    )
    via = fields.Many2one(
        'aduanas.tipos_transporte',
        related="exportacion.via",
        string='Vía',
        readonly=False,
    )
    carrier_id = fields.Many2one(
        'delivery.carrier',
        related="exportacion.carrier_id",
        string="Transporte",
        readonly=False,
    )
    tara = fields.Integer(
        related="exportacion.tara",
        string="Tara",
        readonly=False,
    )
    uom_tara = fields.Many2one(
        'uom.uom',
        related="exportacion.uom_tara",
        string='Unidad Medida Tara',
        readonly=False,
    )
    peso_bruto = fields.Float(
        related="exportacion.peso_bruto",
        string="Peso Bruto",
        readonly=False,
    )
    uom_peso_bruto = fields.Many2one(
        'uom.uom',
        related="exportacion.uom_peso_bruto",
        string='Unidad Medida Peso Bruto',
        readonly=False,
    )
    peso_neto = fields.Float(
        related="exportacion.peso_neto",
        string="Peso Neto",
        readonly=False,
    )
    uom_peso_neto = fields.Many2one(
        'uom.uom',
        related="exportacion.uom_peso_neto",
        string='Unidad Medida Peso Neto',
        readonly=False,
    )
    total_items = fields.Integer(
        related="exportacion.total_items",
        string="Total Items",
        readonly=False,
    )
    total_bultos = fields.Integer(
        related="exportacion.total_bultos",
        string="Total Bultos",
        readonly=False,
    )
    monto_flete = fields.Monetary(
        related="exportacion.monto_flete",
        string="Monto Flete",
        readonly=False,
    )
    monto_seguro = fields.Monetary(
        related="exportacion.monto_seguro",
        string="Monto Seguro",
        readonly=False,
    )
    pais_recepcion = fields.Many2one(
        'aduanas.paises',
        related="exportacion.pais_recepcion",
        string='País de Recepción',
        readonly=False,
    )
    bultos = fields.One2many(
        string="Bultos",
        comodel_name="account.invoice.bultos",
        inverse_name="invoice_id",
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False,
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string="Movimiento Relacionado",
        readonly=False,
    )
    
    currency_rate_recitfied = fields.Float('Tasa de Cambio (Rectificativas)')

    @api.one
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        if self.exportacion:
            exp = self.exportacion.copy()
            default.setdefault('exportacion', exp.id)
        return super(Exportacion, self).copy(default)

    def format_vat(self, value, con_cero=False):
        if self.env.context.get('exportacion'):
            if self[0].company_id.vat != value:
                value = "CL555555555"
        return super(Exportacion, self).format_vat(value, con_cero)

    @api.multi
    def crear_exportacion(self):
        self.exportacion = self.env['account.invoice.exportacion'].create({
            'name': 'Exportación',
            'currency_id': self.currency_id.id,
        })

    @api.multi
    def eliminar_exportacion(self):
        if self.exportacion:
            self.exportacion.unlink()

    def _es_nc_exportacion(self):
        return self.document_class_id.es_nc_exportacion()

    def _es_exportacion(self):
        return self.document_class_id.es_exportacion()

    def _totales(self, MntExe=0, no_product=False, taxInclude=False):
        if not self._es_exportacion():
            return super(Exportacion, self)._totales(MntExe, no_product, taxInclude)
        gdr = 0
        if self.global_descuentos_recargos:
            gdr = self.global_descuentos_recargos.get_monto_aplicar()
        TasaIVA = False
        MntIVA = 0
        MntBase = 0
        MntNeto = round(gdr, 0) + sum(round(line.price_total, 0) for line in self.invoice_line_ids)
        MntExe = MntTotal = MntNeto
        return MntExe, MntNeto, MntIVA, TasaIVA, MntTotal, MntBase

    def currency_base(self):
        result = super(Exportacion, self).currency_base()
        if not self._es_exportacion():
            return result
        return self.currency_id

    def currency_target(self):
        if self._es_exportacion():
            clp = self.env.ref('base.CLP').with_context(date=self.date_invoice)
            if self.currency_id != clp:
                return self.env.ref('base.CLP').with_context(date=self.date_invoice)
            return clp
        return super(Exportacion, self).currency_target()

    def _totales_normal(self, currency_id, MntExe, MntNeto, IVA, TasaIVA,
                        MntTotal=0, MntBase=0):
        if not self._es_exportacion():
            return super(Exportacion, self)._totales_normal(currency_id, MntExe,
                                                            MntNeto, IVA, TasaIVA,
                                                            MntTotal, MntBase)
        if IVA > 0 or MntExe == 0:
            raise UserError("Deben ser todos los productos Exentos!")
        Totales = {}
        if currency_id:
            Totales['TpoMoneda'] = currency_id.abreviatura
        Totales['MntExe'] = MntExe
        Totales['MntTotal'] = MntTotal
        return Totales

    def _totales_otra_moneda(self, currency_id, MntExe, MntNeto, IVA, TasaIVA,
                             MntTotal=0, MntBase=0):
        if not self._es_exportacion():
            return super(Exportacion, self)._totales_otra_moneda(currency_id,
                                                                 MntExe, MntNeto,
                                                                 IVA, TasaIVA,
                                                                 MntTotal, MntBase)
        Totales = {}
        currency_target = self.currency_target()
        Totales['TpoMoneda'] = self._acortar_str(currency_target.abreviatura, 15)
        base = self.currency_base()
        if self.currency_rate_recitfied:
            base_rate = self.currency_rate_recitfied
        else:
            base_rate = round(1 / base.rate, 2)
            
        Totales['TpoCambio'] = base_rate
        _logger.info(f'LOGGG:.. base_rate {base_rate}')
        if MntExe:
            # if currency_id:
            #     MntExe = base._convert(MntExe, self.company_id.currency_id, self.company_id, self.date_invoice)
            Totales['MntExeOtrMnda'] = round(MntExe * base_rate, 0)
        # if currency_target:
        #     MntTotal = base._convert(MntTotal, self.company_id.currency_id, self.company_id, self.date_invoice)
        Totales['MntTotOtrMnda'] = round(MntTotal * base_rate, 0)
        _logger.info(f'LOGG ::>>__ totales {Totales}')
        return Totales

    def _id_doc(self, taxInclude=False, MntExe=0):
        res = super(Exportacion, self)._id_doc(taxInclude, MntExe)
        if self._es_exportacion() and self.payment_term_id.forma_pago_aduanas:
            res['FmaPagExp'] = self.payment_term_id.forma_pago_aduanas.code
        return res

    def _receptor(self):
        Receptor = {}
        commercial_partner_id = self.commercial_partner_id or self.partner_id.commercial_partner_id
        # if not commercial_partner_id.vat and not self._es_boleta() and not self._nc_boleta() and not self._es_exportacion():
        if not commercial_partner_id.vat and not self._es_boleta() and not self._es_exportacion():
            raise UserError("Debe Ingresar RUT Receptor")
        #if self._es_boleta():
        #    Receptor['CdgIntRecep']
        Receptor['RUTRecep'] = self.format_vat(commercial_partner_id.vat)
        Receptor['RznSocRecep'] = self._acortar_str( commercial_partner_id.name, 100)
        if not self.partner_id or (not self._es_exportacion() and Receptor['RUTRecep'] == '66666666-6'):
            return Receptor
        elif self._es_exportacion():
            Receptor['RUTRecep'] = '55.555.555-5'
        # if not self._es_boleta() and not self._nc_boleta():
        if not self._es_boleta():
            GiroRecep = self.acteco_id.name or commercial_partner_id.activity_description.name
            if not GiroRecep and not self._es_exportacion():
                raise UserError(_('Seleccione giro del partner'))
            if GiroRecep:
                Receptor['GiroRecep'] = self._acortar_str(GiroRecep, 40)
        if self.partner_id.phone or commercial_partner_id.phone:
            Receptor['Contacto'] = self._acortar_str(self.partner_id.phone or commercial_partner_id.phone or self.partner_id.email, 80)
        if (commercial_partner_id.email or commercial_partner_id.dte_email or self.partner_id.email or self.partner_id.dte_email) and not self._es_boleta():
            Receptor['CorreoRecep'] = commercial_partner_id.dte_email or self.partner_id.dte_email or commercial_partner_id.email or self.partner_id.email
        street_recep = (self.partner_id.street or commercial_partner_id.street or False)
        # if not street_recep and not self._es_boleta() and not self._nc_boleta():
        if not street_recep and not self._es_boleta():
        # or self.indicador_servicio in [1, 2]:
            raise UserError('Debe Ingresar dirección del cliente')
        street2_recep = (self.partner_id.street2 or commercial_partner_id.street2 or False)
        if street_recep or street2_recep:
            Receptor['DirRecep'] = self._acortar_str(street_recep + (' ' + street2_recep if street2_recep else ''), 70)
        cmna_recep = self.partner_id.city_id.name or commercial_partner_id.city_id.name
        # if not cmna_recep and not self._es_boleta() and not self._nc_boleta() and not self._es_exportacion():
        if not cmna_recep and not self._es_boleta() and not self._es_exportacion():
            raise UserError('Debe Ingresar Comuna del cliente')
        else:
            Receptor['CmnaRecep'] = cmna_recep
        ciudad_recep = self.partner_id.city or commercial_partner_id.city
        if ciudad_recep:
            Receptor['CiudadRecep'] = ciudad_recep
        Receptor['Nacionalidad'] = self.partner_id.commercial_partner_id.country_id.aduanas_id.code
        return Receptor

    def _validaciones_uso_dte(self):
        super(Exportacion,self)._validaciones_uso_dte()
        if self._es_exportacion():
            if self.incoterm_id and not self.payment_term_id:
                raise UserError("Debe Ingresar un Término de Pago")
            expo = self.exportacion
            if not self.payment_term_id.modalidad_venta and not self._es_nc_exportacion():
                raise UserError("Debe indicar Modalidad de venta")
            if self.ind_servicio in [3, 4, 5] and self.payment_term_id.modalidad_venta.code != '1':
                raise UserError("La modalidad de venta del plazo de pago debe ser 1.- A FIRME")

    def get_monto_clausula(self):
        mnt_clau = self.payment_term_id.with_context(currency_id=self.currency_id.id).compute(
            self.amount_total, date_ref=self.date_invoice)[0]
        return round(mnt_clau[0][1], 2)

    def _bultos(self, bultos):
        Bultos = []
        for b in bultos:
            Bulto = dict()
            # if b.tipo_bulto.code and b.tipo_bulto.code not in ['22']:
            #     _logger.info('LOG: -->> es del tipo 22')
            #     Bulto['CodTpoBultos'] = b.tipo_bulto.code
            Bulto['CodTpoBultos'] = b.tipo_bulto.code
            Bulto['CantBultos'] = b.cantidad_bultos
            if b.marcas:
                Bulto['Marcas'] = b.marcas
            if b.id_container:
                Bulto['IdContainer'] = b.id_container
                Bulto['Sello'] = b.sello
                Bulto['EmisorSello'] = b.emisor_sello
            Bultos.append(Bulto)
        _logger.info('LOG: -->>> bultos {}'.format(Bultos))
        return Bultos

    def _aduana(self):
        expo = self.exportacion.with_context(exportacion=True)
        Aduana = {}
        Aduana['CodModVenta'] = self.payment_term_id.modalidad_venta.code
        if self.incoterm_id:
            Aduana['CodClauVenta'] = self.incoterm_id.aduanas_code
        if self.payment_term_id:
            Aduana['TotClauVenta'] = self.get_monto_clausula()
        if expo.via:
            Aduana['CodViaTransp'] = expo.via.code
        if expo.chofer_id:
            Aduana['NombreTransp'] = expo.chofer_id.name
        if expo.carrier_id:
            Aduana['RUTCiaTransp'] = self.format_vat(expo.carrier_id.partner_id.vat)
        if expo.carrier_id:
            Aduana['NomCiaTransp'] = expo.carrier_id.name
        #Aduana['IdAdicTransp'] = self.indicador_adicional
        if expo.puerto_embarque:
            Aduana['CodPtoEmbarque'] = expo.puerto_embarque.code
        #Aduana['IdAdicPtoEmb'] = expo.ind_puerto_embarque
        if expo.puerto_desembarque:
            Aduana['CodPtoDesemb'] = expo.puerto_desembarque.code
        #Aduana['IdAdicPtoDesemb'] = expo.ind_puerto_desembarque
        if expo.tara:
            Aduana['Tara'] = expo.tara
        if expo.uom_tara.code:
            Aduana['CodUnidMedTara'] = expo.uom_tara.code
        if expo.peso_bruto:
            Aduana['PesoBruto'] = round(expo.peso_bruto, 2)
        if expo.uom_peso_bruto.code:
            Aduana['CodUnidPesoBruto'] = expo.uom_peso_bruto.code
        if expo.peso_neto:
            Aduana['PesoNeto'] = round(expo.peso_neto, 2)
        if expo.uom_peso_neto.code:
            Aduana['CodUnidPesoNeto'] = expo.uom_peso_neto.code
        if expo.total_items:
            Aduana['TotItems'] = expo.total_items
        if expo.total_bultos:
            Aduana['TotBultos'] = expo.total_bultos
            Aduana['Bultos'] = self._bultos(self.bultos)
        #Aduana['Marcas'] =
        #Solo si es contenedor
        #Aduana['IdContainer'] =
        #Aduana['Sello'] =
        #Aduana['EmisorSello'] =
        if expo.monto_flete:
            Aduana['MntFlete'] = expo.monto_flete
        if expo.monto_seguro:
            Aduana['MntSeguro'] = expo.monto_seguro
        if expo.pais_recepcion:
            Aduana['CodPaisRecep'] = expo.pais_recepcion.code
        if expo.pais_destino:
            Aduana['CodPaisDestin'] = expo.pais_destino.code
        return Aduana

    def _transporte(self):
        Transporte = {}
        expo = self.exportacion
        if expo.carrier_id:
            if self.patente:
                Transporte['Patente'] = self.patente[:8]
            elif self.vehicle:
                Transporte['Patente'] = self.vehicle.matricula or ''
            if self.transport_type in [2, 3] and self.chofer:
                if not self.chofer.vat:
                    raise UserError("Debe llenar los datos del chofer")
                if self.transport_type == 2:
                    Transporte['RUTTrans'] = self.format_vat(self.company_id.vat)
                else:
                    if not self.carrier_id.partner_id.vat:
                        raise UserError("Debe especificar el RUT del transportista, en su ficha de partner")
                    Transporte['RUTTrans'] = self.format_vat(self.carrier_id.partner_id.vat)
                if self.chofer:
                    Transporte['Chofer'] = {}
                    Transporte['Chofer']['RUTChofer'] = self.format_vat(self.chofer.vat)
                    Transporte['Chofer']['NombreChofer'] = self.chofer.name[:30]
        if not self._es_exportacion():
            partner_id = self.partner_id or self.company_id.partner_id
            Transporte['DirDest'] = (partner_id.street or '')+ ' '+ (partner_id.street2 or '')
            Transporte['CmnaDest'] = partner_id.state_id.name or ''
            Transporte['CiudadDest'] = partner_id.city or ''
        Transporte['Aduana'] = self._aduana()
        return Transporte

    def _encabezado(self, MntExe=0, no_product=False, taxInclude=False):
        res = super(Exportacion, self)._encabezado(MntExe, no_product, taxInclude)
        if not self._es_exportacion():
            return res
        if not res.get('OtraMoneda'):
            another_currency_id = self.env.ref('base.CLP').with_context(
                date=self.date_invoice)
            MntExe, MntNeto, IVA, TasaIVA, MntTotal, MntBase = self._totales(MntExe, no_product, taxInclude)
            res['OtraMoneda'] = self._totales_otra_moneda(
                        another_currency_id, MntExe, MntNeto, IVA, TasaIVA,
                        MntTotal, MntBase)
        if self._es_exportacion() and self.ind_servicio != 4:
            res['Transporte'] = self._transporte()
        elif self._es_exportacion() and not self.ind_servicio:
            raise UserError("Si es una factura de exportación, debe indicar el tipo de servicio")
        return res

    @api.onchange('monto_flete', 'monto_seguro')
    def _set_seguros(self):
        if self.exportacion:
            if self.monto_flete:
                flete = self.env['account.invoice.gdr'].search([
                    ('type', '=', 'R'),
                    ('invoice_id', '=', self.id),
                    ('aplicacion', '=', 'flete'),
                ])
                if not flete:
                    flete = self.env['account.invoice.gdr'].create({
                        'type': 'R',
                        'invoice_id': self.id,
                        'aplicacion': 'flete',
                        'impuesto': 'exentos',
                        'gdr_detail': 'Flete',
                        'gdr_type': 'amount',
                    })
                    flete.valor = self.monto_flete
            if self.monto_seguro:
                seguro = self.env['account.invoice.gdr'].search([
                    ('type', '=', 'R'),
                    ('invoice_id', '=', self.id),
                    ('aplicacion', '=', 'seguro'),
                ])
                if not seguro:
                    seguro = self.env['account.invoice.gdr'].create({
                        'type': 'R',
                        'invoice_id': self.id,
                        'aplicacion': 'seguro',
                        'impuesto': 'exentos',
                        'gdr_detail': 'Seguro',
                        'gdr_type': 'amount',
                    })
                seguro.valor = self.monto_seguro

    @api.onchange('bultos')
    def tot_bultos(self):
        tot_bultos = 0
        for b in self.bultos:
            tot_bultos += b.cantidad_bultos
        self.total_bultos = tot_bultos

    @api.onchange('currency_id')
    def update_exportacion(self):
        if self.exportacion:
            self.exportacion.currency_id = self.currency_id
