from odoo import models, fields, api


class CustomNote(models.Model):
    _name = "custom.note"
    _description = "Nota (Custom)"

    name = fields.Char(string="Nombre")

    body = fields.Text(string="Cuerpo nota")

    destiny = fields.Selection(
        selection=[('andes', 'Los Andes'), ('sanantonio', 'San Antonio'), ('valparaiso', 'Valparaiso')],
        string="Destino"
    )

    footer = fields.Text(string="Pie nota")

    @api.model
    def get_full_note(self):
        destiny = dict(self._fields['destiny'].selection).get(self.destiny)
        full_note = self.body.strip()
        full_note = full_note.replace('{destino}', destiny)
        full_note = full_note.upper()
        return full_note

    @api.model
    def get_footer_note(self):
        destiny = dict(self._fields['destiny'].selection).get(self.destiny)
        full_footer = self.footer
        full_footer = full_footer.replace('{destino}',destiny)
        full_footer = full_footer.upper()
        return full_footer
