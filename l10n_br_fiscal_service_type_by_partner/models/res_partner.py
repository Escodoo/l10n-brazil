# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):

    _inherit = "res.partner"

    partner_lc_ids = fields.One2many(
        comodel_name="res.partner.lc",
        inverse_name="partner_id",
        string="Partner LC",
    )
