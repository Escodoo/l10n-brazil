# Copyright 2024 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FiscalDocumentMixin(models.AbstractModel):
    _inherit = "l10n_br_fiscal.document.mixin.fields"

    tms_commitment_date = fields.Datetime("Delivery Date")
    tms_expected_date = fields.Datetime("Expected Date")

    tms_product_transported_id = fields.Many2one(
        "product.product", string="Product Transported"
    )  # TODO: avaliar se cabe utilizar a unidade de medida em algum lugar..
    # exemplo se for peso, palete, unidade
    tms_main_product = fields.Char(
        related="tms_product_transported_id.name",
        string="Main Product",
        store=True,
        readonly=False,
    )
    tms_other_product_features = fields.Char(string="Other Product Features")
    tms_units = fields.Integer(string="Units")
    tms_units_description = fields.Char(string="Units Description", default="Unit")
    tms_volume = fields.Integer(string="Volume (m³)")
    tms_weight = fields.Float(string="Weight (kg)")
    tms_cargo_value = fields.Float(string="Cargo Value")
    tms_insured_value = fields.Float(string="Insured Value")
    tms_distance = fields.Float(string="Distance (km)")

    # tms_transport_modal = fields.Selection(
    #     selection=[
    #         ("01", "Road"),
    #         ("02", "Air"),
    #         ("03", "Water"),
    #         ("04", "Rail"),
    #         ("05", "Pipeline"),
    #         ("06", "Multimodal"),
    #     ],
    #     string="Transport Mode",
    # )
