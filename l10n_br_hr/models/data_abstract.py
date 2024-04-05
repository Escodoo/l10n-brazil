# Copyright (C) 2019  Renato Lima - Akretion <renato.lima@akretion.com.br>
# Copyright (C) 2024 Xipp Tech - Ravi do Valle Luz <raviluz@xipptech.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models
from odoo.osv import expression


class DataAbstract(models.AbstractModel):
    _name = "l10n_br_hr.data.abstract"
    _description = "HR Data Abstract"
    _order = "code"

    code = fields.Char(required=True, index=True)

    name = fields.Text(required=True, index=True)

    @api.depends("name", "code")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.code} - {rec.name}"

    @api.model
    def _name_search(
        self, name, args=None, operator="ilike", limit=None, order=None
    ):
        args = args or []
        domain = []
        if name:
            domain = ["|", ("code", operator, name), ("name", operator, name)]
            return self._search(
                expression.AND([domain, args]),
                limit=limit,
                order=order,
            )
        return super()._name_search(
            name, args=args, operator=operator, limit=limit, order=order
        )
