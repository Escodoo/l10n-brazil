# Copyright 2025 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PaymentTokenAsaas(models.Model):
    _inherit = "payment.token"

    asaas_card_token = fields.Char(
        string="Asaas Card Token",
        required=False,
        help="Token returned by Asaas for credit card operations.",
    )

    @api.model
    def asaas_create(self, values):
        """Process tokenization data for Asaas.

        Formats the response data and returns a dict containing the card token,
        formatted name (Customer Name or Card holder name), and partner_id.
        """
        partner = self.env["res.partner"].browse(values["partner_id"])

        if partner:
            description = "Partner: %s (id: %s)" % (partner.name, partner.id)
        else:
            description = values.get("cc_holder_name", "")

        res = {
            "acquirer_ref": partner.id if partner else False,
            "name": description,
            "asaas_card_token": values.get("asaas_card_token")
            or values.get("creditCardToken"),
        }

        return res
