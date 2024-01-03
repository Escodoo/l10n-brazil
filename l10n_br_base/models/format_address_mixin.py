# Copyright (C) 2021  Renato Lima - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import models


class FormatAddressMixin(models.AbstractModel):
    _inherit = "format.address.mixin"

    def _view_get_address(self, arch):
        address_view_id = self.env.company.country_id.address_view_id.sudo()
        if address_view_id.model != self._name:
            address_view_id.model = False
        return super()._view_get_address(arch)
