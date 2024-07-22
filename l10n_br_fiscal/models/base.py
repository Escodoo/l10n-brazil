# Copyright (C) 2024 - TODAY Ravi do Valle Luz - XippTech
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import models, api

class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def _get_optional_delegation_inherit_fields(self):
        return set()