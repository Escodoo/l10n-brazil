# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PartnerLC(models.Model):

    _name = "partner.lc"
    _description = "Fiscal Partner LC"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
    )

    service_type_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.service.type",
        string="Fiscal Service Type",
        domain="[('can_be_selected_on_partner', '=', True)]",
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
    )
