# Copyright 2023 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields

from odoo.addons.spec_driven_model.models import spec_models


class MDFeRelated(spec_models.StackedModel):
    _name = "l10n_br_fiscal.document.related"
    _inherit = [
        "l10n_br_fiscal.document.related",
        "mdfe.30.infmdfetransp",
        "mdfe.30.tmdfe_infnfe",
        "mdfe.30.infcte",
    ]
    _stacked = "mdfe.30.tmdfe_infnfe"
    _binding_module = "nfelib.mdfe.bindings.v3_0.mdfe_tipos_basico_v3_00"
    _field_prefix = "mdfe30_"
    _schema_name = "mdfe"
    _schema_version = "3.0.0"
    _odoo_module = "l10n_br_mdfe"
    _spec_module = "odoo.addons.l10n_br_mdfe_spec.models.v3_0.mdfe_tipos_basico_v3_00"
    _spec_tab_name = "MDFe"

    mdfe30_chNFe = fields.Char(related="document_key")

    mdfe30_chCTe = fields.Char(related="document_key")

    mdfe30_chMDFe = fields.Char(related="document_key")

    mdfe30_peri = fields.One2many(comodel_name="l10n_br_mdfe.transporte.perigoso")

    mdfe30_infUnidTransp = fields.One2many(comodel_name="l10n_br_mdfe.transporte.inf")
