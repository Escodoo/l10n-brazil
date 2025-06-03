# Copyright 2025 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

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
        """Validates user input for Asaas S2S."""
        self.ensure_one()
        # Required fields for Asaas card tokenization
        for field_name in ["cc_token", "cc_holder_name"]:
            if not data.get(field_name):
                return False
        return True

    @api.model
    def asaas_s2s_form_process(self, data):
        """Saves the payment.token object with data from Asaas server.

        Card number, cvc, and expiry date should not be stored at this point.
        """
        payment_token = (
            self.env["payment.token"]
            .sudo()
            .create(
                {
                    "cc_holder_name": data["cc_holder_name"],
                    "acquirer_id": int(data["acquirer_id"]),
                    "partner_id": int(data["partner_id"]),
                    "asaas_card_token": data["cc_token"],
                }
            )
        )
        return payment_token

    @api.model
    def _get_asaas_api_url(self):
        """Get Asaas API URL for all S2S communication.

        Takes environment into consideration.
        """
        if self.state == "enabled":
            return "https://api.asaas.com/v3"
        else:
            return "https://sandbox.asaas.com/api/v3"

    def _get_asaas_api_headers(self):
        """Get Asaas API headers for all S2S communication.

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
