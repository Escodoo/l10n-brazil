# Copyright 2020 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from ...l10n_br_fiscal.constants.fiscal import TAX_FRAMEWORK


class ContractLine(models.Model):
    _name = "contract.line"
    _inherit = [_name, "l10n_br_fiscal.document.line.mixin"]

    company_id = fields.Many2one(
        related="contract_id.company_id",
    )

    fiscal_tax_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.tax",
        relation="fiscal_contract_line_tax_rel",
        column1="document_id",
        column2="fiscal_tax_id",
        string="Fiscal Taxes",
    )

    tax_framework = fields.Selection(
        selection=TAX_FRAMEWORK,
        related="contract_id.company_id.tax_framework",
        string="Tax Framework",
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="contract_id.partner_id",
        string="Partner",
    )

    ind_final = fields.Selection(related="contract_id.ind_final")

    def _prepare_invoice_line(self, move_form):
        self.ensure_one()
        invoice_line_vals = super()._prepare_invoice_line(move_form)
        quantity = invoice_line_vals.get("quantity")
        if invoice_line_vals:
            invoice_line_vals.update(self._prepare_br_fiscal_dict())
            invoice_line_vals["quantity"] = quantity
        return invoice_line_vals

    @api.model
    def create(self, values):
        res = super().create(values)
        if res.contract_id.fiscal_operation_id and not res.fiscal_operation_id:
            res.fiscal_operation_id = res.contract_id.fiscal_operation_id
            res._onchange_fiscal_operation_id()
        return res
