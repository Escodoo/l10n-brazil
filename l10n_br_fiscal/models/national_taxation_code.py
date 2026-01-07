# Copyright 2020 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class NationalTaxationCode(models.Model):
    _name = "l10n_br_fiscal.national.taxation.code"
    _inherit = "l10n_br_fiscal.data.abstract"
    _description = "National Taxation Code"

    tax_definition_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.tax.definition",
        relation="tax_definition_national_taxation_code_rel",
        readonly=True,
        string="Tax Definition",
    )
