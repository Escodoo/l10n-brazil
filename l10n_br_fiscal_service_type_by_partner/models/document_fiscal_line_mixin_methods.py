# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class FiscalDocumentLineMixinMethods(models.AbstractModel):
    _inherit = "l10n_br_fiscal.document.line.mixin.methods"

    @api.onchange("product_id")
    def _onchange_product_id_fiscal(self):
        super()._onchange_product_id_fiscal()
        if self.product_id:
            partner_lc = self.partner_id.partner_lc_ids.filtered(
                lambda lc: lc.product_id == self.product_id
            )
            if partner_lc:
                self.service_type_id = partner_lc.service_type_id
