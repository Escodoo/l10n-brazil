# Copyright (C) 2026 - TODAY, Cristiano Mafra Junior <cristiano.mafra@escodoo.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class DocumentImportWizard(models.TransientModel):
    _inherit = "l10n_br_fiscal.document.import.wizard"

    purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Order",
        domain="[('partner_id', '=', issuer_partner_id),"
        " ('state', 'in', ('purchase', 'done'))]",
        help="Purchase order this document is expected to bill, shown next to "
        "the document total so both amounts can be compared before importing. "
        "Kept for reference only: it does not change the imported lines.",
    )

    purchase_amount_total = fields.Monetary(
        related="purchase_order_id.amount_total",
        string="Purchase Order Total",
    )
