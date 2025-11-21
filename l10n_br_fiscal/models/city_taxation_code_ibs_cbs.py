# Copyright 2025 - TODAY, Cristiano Mafra Junior <cristiano.mafra@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

class CityTaxationIbsCbs(models.Model):
    _name = "l10n_br_fiscal.city.taxation.ibs_cbs"
    _description = "City Taxation IBS/CBS Mapping"

    company_id = fields.Many2one(
        "res.company",
        required=True,
    )

    city_taxation_code_id = fields.Many2one(
        "l10n_br_fiscal.city.taxation.code",
        required=True,
    )

    cst_id = fields.Many2one(
        "l10n_br_fiscal.ibs_cbs.cst",
        string="CST",
    )

    cclass_id = fields.Many2one(
        "l10n_br_fiscal.ibs_cbs.cclass",
        string="cClassTrib",
        domain="[('cst_id', '=', cst_id)]",
    )
