# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form

from odoo.addons.purchase_requisition.tests.common import TestPurchaseRequisitionCommon


class L10nBrPurchaseRequisition(TestPurchaseRequisitionCommon):
    def test_l10n_br_purchase_requisition(self):

        # Create purchase order from purchase requisition
        po_form = Form(
            self.env["purchase.order"].with_context(
                default_requisition_id=self.requisition1.id
            )
        )
        po_form.partner_id = self.res_partner_1
        po = po_form.save()
        self.assertTrue(po.order_line.fiscal_operation_id.id)
        self.assertTrue(po.order_line.fiscal_operation_line_id.id)
