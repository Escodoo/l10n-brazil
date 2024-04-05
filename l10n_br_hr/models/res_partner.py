# (c) 2019 KMEE INFORMATICA LTDA
# (c) 2024 Xipp Tech - Ravi do Valle Luz <raviluz@xipptech.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_employee_dependent = fields.Boolean(string="Is an employee dependent")

    def create_depentent(self):
        self.env["hr.employee.dependent"].create([
            dict(partner_id=r.id) for r in self
        ])
        return True

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        if "create_depentent" in self._context:
            return recs
        
        recs.filtered("is_employee_dependent").with_context(
            create_depentent=True
        ).create_depentent()

        return recs

    def write(self, vals):
        res = super().write(vals)
        if "is_employee_dependent" in vals and not self.is_employee_dependent:
            self.create_depentent()
        return res
