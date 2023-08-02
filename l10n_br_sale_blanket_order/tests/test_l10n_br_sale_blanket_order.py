# Copyright 2023 - TODAY, Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from datetime import date, timedelta
from odoo.tests.common import SavepointCase
from odoo.exceptions import UserError


class L10nBrSaleBLanketOrderTest(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()        

        # Set up some test data like partner, payment term, company, pricelist, etc.
        cls.partner = cls.env.ref("base.res_partner_1")
        cls.payment_term = cls.env.ref("account.account_payment_term_immediate")
        cls.company = cls.env.ref("l10n_br_base.empresa_lucro_presumido")
        cls.pricelist = cls.env.ref("product.list0")
        cls.validity_date = date.today() + timedelta(days=2)

        cls.product = cls.env.ref("product.product_delivery_01")
        cls.product_uom = cls.env.ref("uom.product_uom_unit")

    # Helper method to create a new Blanket Order for testing.
    def _create_blanket_order(self):
        values = {
            "partner_id": self.partner.id,
            "validity_date": self.validity_date,
            "payment_term_id": self.payment_term.id,
            "pricelist_id": self.pricelist.id,
            "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom": self.product_uom.id,
                            "original_uom_qty": 20.0,
                            "price_unit": 25.0,
                        },
                    )
            ],
        }
        # Create new register blanket.order
        blanket_order = self.env['sale.blanket.order'].create(values)
        blanket_order.sudo().onchange_partner_id()

        return blanket_order
    
    # Helper method to create a new wizard for testing, based on a Blanket Order.
    def _create_wizard(self, blanket_order):
        lines = []
        for line in blanket_order.line_ids.filtered(lambda l: l.remaining_uom_qty != 0.0):
            line_vals = {
                "blanket_line_id": line.id,
                "product_id": line.product_id.id,
                "date_schedule": line.date_schedule,
                "qty": line.remaining_uom_qty,
            }
            lines.append((0, 0, line_vals))

        # Create a new wizard record for the given Blanket Order
        wizard = self.env["sale.blanket.order.wizard"].create({
            "blanket_order_id": blanket_order.id,
            "line_ids": lines,
        })

        return wizard

    # Test method to confirm and process a Blanket Order.
    def test_confirm_and_process_blanket_order(self):
        # Create a new Blanket Order for testing
        blanket_order = self._create_blanket_order()

        # Check if the blanket order is in "draft" state initially
        self.assertEqual(blanket_order.state, "draft", "Error: Blanket Order is not in draft state.")

        # Confirm the blanket order
        blanket_order.sudo().action_confirm()   

        # Check if the state is updated to "Open" after confirmation
        self.assertEqual(blanket_order.state, "open", "Error: Blanket Order is not in open state after confirmation.")

        # Check the order line (len)     
        bo_lines = self.env["sale.blanket.order.line"].search(
            [("order_id", "=", blanket_order.id)]
        )

        self.assertEqual(len(bo_lines), 1)

        # Create a new wizard for the Blanket Order
        wizard = self._create_wizard(blanket_order)

        # Create sale order(s) using the wizard
        wizard.create_sale_order()
        
        # Check if the state is updated to "Done" after processing
        self.assertEqual(blanket_order.state, "done", "Error: Blanket Order is not in done state after processing.")
