# Copyright 2025 - TODAY, Cristiano Mafra Junior <cristiano.mafra@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CityTaxationIbsCbsCst(models.Model):
    _name = "l10n_br_fiscal.ibs_cbs.cst"
    _description = "IBS/CBS CST"
    _rec_name = "name"

    name = fields.Char(
        required=True,
    )
    code = fields.Char(
        string="CST",
        required=True,
    )

    cclass_ids = fields.One2many(
        "l10n_br_fiscal.ibs_cbs.cclass",
        "cst_id",
        string="Classes Tributárias (cClassTrib)",
    )

    def name_get(self):
        res = []
        for rec in self:
            display = "%s - %s" % (rec.code or "", rec.name or "")
            display = display.strip(" -")
            res.append((rec.id, display))
        return res
