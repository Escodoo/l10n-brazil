# Copyright (C) 2021 - TODAY Renato Lima - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    financial_move_line_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="move_id",
        compute="_compute_financial",
        string="Financial Move Lines",
        domain="[('account_id.user_type_id.type', 'in', ('receivable', 'payable'))]",
    )

    payment_move_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        string="Payment Move Lines",
        compute="_compute_payments",
        store=True,
    )

    @api.depends("line_ids", "state")
    def _compute_financial(self):
        for move in self:
            lines = move.line_ids.filtered(
                lambda l: l.account_id.internal_type in ("receivable", "payable")
            )
            move.financial_move_line_ids = lines.sorted(key="date_maturity", reverse=False)

    @api.depends("line_ids.amount_residual")
    def _compute_payments(self):
        for move in self:
            move.payment_move_line_ids = [
                aml.id
                for partial, amount, aml in move._get_reconciled_invoices_partials()
            ]
