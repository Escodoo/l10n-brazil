# Copyright (C) 2021 - TODAY Gabriel Cardoso de Faria - Kmee
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models


class FiscalDocumentLine(models.Model):
    _inherit = "l10n_br_fiscal.document.line"

    account_line_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="fiscal_document_line_id",
        string="Invoice Lines",
    )

    def write(self, values):
        if values.get('document_id'):
            dummy_doc = self.env["res.company"].search([]).mapped("fiscal_dummy_id")
            dummy_doc_line = fields.first(dummy_doc.fiscal_line_ids).id
            if values.get('document_id') != dummy_doc_line and not values.get('product_id'):
                values["document_id"] = dummy_doc_line
        return super().write(values)
