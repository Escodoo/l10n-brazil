# Copyright (C) 2026 - TODAY, Cristiano Mafra Junior <cristiano.mafra@escodoo.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase


class TestDocumentImportWizardPurchase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("l10n_br_base.empresa_lucro_presumido")
        cls.supplier = cls.env.ref("l10n_br_base.res_partner_cliente1_sp")
        cls.product = cls.env.ref("product.product_product_6")
        cls.order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.supplier.id,
                "company_id": cls.company.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "product_qty": 2,
                            "price_unit": 100.0,
                            "date_planned": "2026-01-01",
                            "name": cls.product.name,
                            "product_uom": cls.product.uom_id.id,
                        },
                    )
                ],
            }
        )
        cls.wizard = cls.env["l10n_br_fiscal.document.import.wizard"].create(
            {"company_id": cls.company.id}
        )

    def test_purchase_total_follows_the_selected_order(self):
        """Picking an order must expose its total, so it can be compared with
        the total declared in the document being imported."""
        self.wizard.purchase_order_id = self.order

        self.assertEqual(self.wizard.purchase_amount_total, self.order.amount_total)

    def test_no_order_selected_leaves_no_total(self):
        """With no order picked there is nothing to compare against."""
        self.assertFalse(self.wizard.purchase_order_id)
        self.assertFalse(self.wizard.purchase_amount_total)
