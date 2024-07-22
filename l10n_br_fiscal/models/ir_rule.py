# Copyright (C) 2024 - TODAY Ravi do Valle Luz - XippTech
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, models
from odoo.osv import expression


class IrRule(models.Model):
    _inherit = "ir.rule"

    def _compute_domain(self, model_name, mode="read"):
        dom = super()._compute_domain(model_name, mode=mode)

        # Add support for optional delegate inheritance field
        optional_fields = self.env[
            model_name
        ]._get_optional_delegation_inherit_fields()
        complete_dom = []
        for item in dom:
            if item[0] in optional_fields and item[1] == "any":
                complete_dom += expression.OR([[item], [(item[0], "=", False)]])
            else:
                complete_dom.append(item)
        return complete_dom

