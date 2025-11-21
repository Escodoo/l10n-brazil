from odoo import fields, models
class CityTaxationIbsCbsCClass(models.Model):
    _name = "l10n_br_fiscal.ibs_cbs.cclass"
    _description = "IBS/CBS cClassTrib"
    _rec_name = "name"

    name = fields.Char(
        required=True,
    )

    cst_id = fields.Many2one(
        "l10n_br_fiscal.ibs_cbs.cst",
        string="CST",
        required=True,
        ondelete="cascade",
    )

    code = fields.Char(
        string="cClassTrib",
        required=True,
    )


    def name_get(self):
        res = []
        for rec in self:
            display = "[%s] %s - %s" % (
                rec.cst_id.code or "",
                rec.code or "",
                rec.name or "",
            )
            display = display.strip(" -[]")
            res.append((rec.id, display))
        return res
