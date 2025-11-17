# Copyright 2025 - TODAY, Cristiano Mafra Junior <cristiano.mafra@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CityTaxationIbsCbs(models.Model):
    _name = "l10n_br_fiscal.city.taxation.ibs_cbs"
    _description = "City Taxation IBS/CBS Mapping"

    # TODO: HOT-FIX
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
    )

    city_taxation_code_id = fields.Many2one(
        "l10n_br_fiscal.city.taxation.code",
        string="City Taxation Code",
        required=True,
    )

    cClassTribIBSCBS = fields.Char(
        string="IBS/CBS",
        required=False,
    )

    cstIBSCBS = fields.Char(
        string="CST IBS/CBS",
        required=False,
    )
