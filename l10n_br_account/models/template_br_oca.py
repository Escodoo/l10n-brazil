# Copyright (C) 2019  Renato Lima - Akretion
# Copyright 2024 Ravi do Valle Luz - XippTech
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, _, Command
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("br_oca", "account.tax")
    def _get_br_oca_fiscal_account_tax(self):
        data = self._parse_csv(
            "br_oca", "account.tax", module="l10n_br_account"
        )
        group_key = "fiscal_tax_ids@tax_group_id"
        for pseudoid, rec_data in data.items():
            if not group_key in rec_data:
                continue
            rec_data["fiscal_tax_ids"] = [Command.set(
                self.env["l10n_br_fiscal.tax"].search([
                    ("tax_group_id", "=", self.env.ref(rec_data[group_key]).id)
                ]).ids
            )]
            del rec_data[group_key]
        return data
    
    @template("br_oca", "account.tax.group")
    def _get_br_oca_fiscal_account_tax_group(self):
        return self._parse_csv(
            "br_oca", "account.tax.group", module="l10n_br_account"
        )
    

