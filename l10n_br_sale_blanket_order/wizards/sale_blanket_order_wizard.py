# Copyright 2023 - TODAY, Marcel Savergnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SaleBlanketOrderWizard(models.TransientModel):

    _inherit = "sale.blanket.order.wizard"

    def _prepare_so_line_vals(self, line):

        fiscal_vals = line.blanket_line_id._prepare_br_fiscal_dict()
        vals = super()._prepare_so_line_vals(line=line)
        vals.update(fiscal_vals)
        return vals

    def _prepare_so_vals(
        self,
        customer,
        user_id,
        currency_id,
        pricelist_id,
        payment_term_id,
        order_lines_by_customer,
    ):
        fiscal_vals = self.blanket_order_id._prepare_br_fiscal_dict()
        vals = super()._prepare_so_vals(
            customer=customer,
            user_id=user_id,
            currency_id=currency_id,
            pricelist_id=pricelist_id,
            payment_term_id=payment_term_id,
            order_lines_by_customer=order_lines_by_customer,
        )
        vals.update(fiscal_vals)
        return vals
