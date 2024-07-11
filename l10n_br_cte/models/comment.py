# Copyright 2024 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields

from odoo.addons.spec_driven_model.models import spec_models


class CTeComment(spec_models.StackedModel):
    _name = "l10n_br_fiscal.comment"
    _inherit = ["l10n_br_fiscal.comment", "cte.40.tcte_obscont"]
    _stacked = "cte.40.tcte_obscont"
    _field_prefix = "cte40_"
    _schema_name = "cte"
    _schema_version = "4.0.0"
    _odoo_module = "l10n_br_cte"
    _spec_module = "odoo.addons.l10n_br_cte_spec.models.v4_0.cte_tipos_basico_v4_00"
    _spec_tab_name = "CTe"
    _binding_module = "nfelib.cte.bindings.v4_0.cte_tipos_basico_v4_00"

    cte40_xCampo = fields.Char()

    cte40_xTexto = fields.Text()

    def _export_field(self, xsd_field, class_obj, member_spec, export_value=None):
        if xsd_field == "cte40_xCampo":
            return self.name[:20].strip()
        if xsd_field == "cte40_xTexto":
            if self.env.context["params"]["model"] == "l10n_br_fiscal.document":
                doc = self.env["l10n_br_fiscal.document"].browse(
                    self.env.context["params"]["id"]
                )
                vals = {"user": self.env.user, "ctx": self._context, "doc": doc}
                return self.compute_message(vals)[:160].strip()
        return super()._export_field(xsd_field, class_obj, member_spec, export_value)
