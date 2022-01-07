from odoo import models, fields, api
import os


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    counter = fields.Integer("Posicion",nullable=True)

    stock_picking_id = fields.Integer()

    @api.constrains('counter')
    def _validate_counter(self):
        if self.counter > 16:
            raise models.ValidationError("La posicion de la imagen {} no existe".format(self.datas_fname))

    @api.model_create_multi
    def create(self, vals_list):
        try:
            for values in vals_list:
                for field in ('file_size', 'checksum'):
                    values.pop(field, False)
                values = self._check_contents(values)
                values = self._make_thumbnail(values)
                self.browse().check('write', values=values)
            return super(IrAttachment, self).create(vals_list)
        except:
            pass
