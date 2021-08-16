# -*- coding: utf-8 -*-
# © 2015 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api, fields, tools
import odoo.addons.decimal_precision as dp
from odoo.tools.translate import _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _prepare_analytic_account(self, line):
        return line.order_id.session_id.config_id.account_analytic_id.id