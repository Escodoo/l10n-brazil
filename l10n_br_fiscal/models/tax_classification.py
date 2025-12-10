# Copyright 2025 Marcel Savegnago <https://escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from ..constants.fiscal import TAX_RATE_TYPE, TAX_RATE_TYPE_DEFAULT


class TaxClassification(models.Model):
    _name = "l10n_br_fiscal.tax.classification"
    _inherit = "l10n_br_fiscal.data.abstract"
    _order = "code"
    _description = "Tax Classification"

    code = fields.Char(size=8)

    description = fields.Text()

    ibs_reduction_percent = fields.Float(
        string="IBS Reduction (%)",
        digits=(16, 2),
        default=0.0,
    )

    cbs_reduction_percent = fields.Float(
        string="CBS Reduction (%)",
        digits=(16, 2),
        default=0.0,
    )

    regular_taxation = fields.Boolean(
        default=False,
    )

    presumed_credit = fields.Boolean(
        default=False,
    )

    credit_reversal = fields.Boolean(
        default=False,
    )

    rate_type = fields.Selection(
        selection=TAX_RATE_TYPE,
        default=TAX_RATE_TYPE_DEFAULT,
        required=True,
    )

    document_type_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.document.type",
        relation="tax_classification_document_type_rel",
        string="Related DFes",
        help="Related Digital Fiscal Documents",
    )
