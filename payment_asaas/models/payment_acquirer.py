# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PaymentAcquirerAsaas(models.Model):

    _inherit = "payment.acquirer"

    provider = fields.Selection(
        selection_add=[("asaas", "Asaas")],
        ondelete={"asaas": "set default"},
    )
    asaas_token = fields.Char(
        required_if_provider="asaas",
        groups="base.group_user",
    )

    def asaas_s2s_form_validate(self, data):
        """Validates user input"""
        self.ensure_one()
        for field_name in ["cc_holder_name"]:
            if not data.get(field_name):
                return False
        return True

    @api.model
    def asaas_s2s_form_process(self, data):
        """Saves the payment.token object with data from Asaas server

        Cvc, number and expiry date card info should be empty by this point.
        """
        payment_token = (
            self.env["payment.token"]
            .sudo()
            .create(
                {
                    "cc_number": data.get("cc_number"),
                    "cc_cvc": int(data.get("cc_cvc")),
                    "cc_holder_name": data.get("cc_holder_name"),
                    "cc_expiry": data.get("cc_expiry"),
                    "cc_brand": data.get("cc_brand"),
                    "acquirer_id": int(data.get("acquirer_id")),
                    "partner_id": int(data.get("partner_id")),
                    "asaas_card_token": data["cc_token"],
                }
            )
        )
        return payment_token

    @api.model
    def _get_asaas_api_url(self):
        """Get Asaas API URLs used in all s2s communication

        Takes environment in consideration.
        """
        if self.state == "enabled":
            return "api.asaas.com"
        else:
            return "sandbox.asaas.com/api"

    def _get_asaas_api_headers(self):
        """Get Asaas API headers used in all s2s communication

        Uses user token as authentication.
        """
        ASAAS_HEADERS = {
            "accept": "application/json",
            "content-type": "application/json",
            "access_token": self.sudo().asaas_token,
        }

        return ASAAS_HEADERS

    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * authorize: support authorizing payment (separates
                         authorization and capture)
            * tokenize: support saving payment data in a payment.tokenize
                        object
        """
        res = super()._get_feature_support()
        res["authorize"].append("asaas")
        res["tokenize"].append("asaas")
        return res
