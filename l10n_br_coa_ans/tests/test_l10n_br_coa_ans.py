# Copyright (C) 2022 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo.tests.common import TransactionCase


class L10nBrAnsCOA(TransactionCase):
    def setUp(self):
        super(L10nBrAnsCOA, self).setUp()

        self.l10n_br_coa_ans = self.env.ref(
            "l10n_br_coa_ans.l10n_br_coa_ans_chart_template"
        )
        self.l10n_br_company = self.env["res.company"].create(
            {"name": "Empresa Teste do Plano de Contas"}
        )

    def test_l10n_br_coa_ans(self):
        """Test installing the chart of accounts template in a new company"""
        self.l10n_br_coa_ans.try_loading(company=self.l10n_br_company)
        self.assertEqual(self.l10n_br_coa_ans, self.l10n_br_company.chart_template_id)
