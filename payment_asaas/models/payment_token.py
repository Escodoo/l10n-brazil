from odoo import api, fields, models


class PaymentTokenAsaas(models.Model):
    _inherit = "payment.token"

    asaas_card_token = fields.Char(
        string="Asaas card Token",
        required=False,
    )

    @api.model
    def asaas_create(self, values):
        """Treats tokenizing data.

        Formats the response data to the result and returns a resulting dict
        containing card token, formated name (Customer Name or Card holder name)
        and partner_id will be returned.
        """
        partner_id = self.env["res.partner"].browse(values["partner_id"])

        if partner_id:
            description = "Partner: %s (id: %s)" % (partner_id.name, partner_id.id)
        else:
            description = values["cc_holder_name"]

        customer_params = {"description": description}

        res = {
            "acquirer_ref": partner_id.id,
            "name": "%s" % (customer_params.get("description")),
            "asaas_card_token": values["asaas_card_token"],
        }

        return res
