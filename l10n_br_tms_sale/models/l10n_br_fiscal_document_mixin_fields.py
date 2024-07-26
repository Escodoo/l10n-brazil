# Copyright 2024 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FiscalDocumentMixin(models.AbstractModel):

    _inherit = "l10n_br_fiscal.document.mixin.fields"

    commitment_date = fields.Datetime("Delivery Date")
    expected_date = fields.Datetime("Expected Date")

    # Remetente
    partner_sendering_id = fields.Many2one(
        "res.partner",
        string="Sender Address",
        help="Responsible for sending the goods, usually the issuer of the NFe.",
    )

    # Expedidor
    partner_shippering_id = fields.Many2one(
        "res.partner",
        string="Shipper Address",
        help="The one responsible for delivering the cargo to the carrier when \
            the shipment is not carried out by the sender.",
    )

    # # Destinatário
    # partner_shipping_id = fields.Many2one(
    #     "res.partner",
    #     string="Recipient",
    #     help="The one who receives the goods at the end of the transport \
    #         route, can be an individual or a company.",
    # )

    # Recebedor
    partner_receivering_id = fields.Many2one(
        "res.partner",
        string="Receiver Address",
        help="Actor who receives the goods. He is considered an intermediary \
            between the issuer and the final recipient.",
    )

    partner_insurance_id = fields.Many2one("res.partner", string="Insurance Partner")

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

    tms_transport_modal = fields.Selection(
        selection=[
            ("01", "Road"),
            ("02", "Air"),
            ("03", "Water"),
            ("04", "Rail"),
            ("05", "Pipeline"),
            ("06", "Multimodal"),
        ],
        string="Transport Mode",
    )
