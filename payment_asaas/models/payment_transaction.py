# Copyright 2025 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import pprint

import requests

from odoo import fields, models

_logger = logging.getLogger(__name__)


class PaymentTransactionAsaas(models.Model):
    _inherit = "payment.transaction"

    asaas_s2s_capture_link = fields.Char(
        string="Capture Link Asaas",
        required=False,
    )
    asaas_s2s_void_link = fields.Char(
        string="Cancel Link Asaas",
        required=False,
    )
    asaas_s2s_check_link = fields.Char(
        string="Check Link Asaas",
        required=False,
    )

    def _check_asaas_customer(self):
        """Check if the customer exists in Asaas."""
        url = "%s/customers?cpfCnpj=%s" % (
            self.acquirer_id._get_asaas_api_url(),
            self.partner_id.vat,
        )
        _logger.info("_check_asaas_customer: Sending values to URL %s", url)
        r = requests.get(
            url,
            headers=self.acquirer_id._get_asaas_api_headers(),
        )
        res = r.json()
        _logger.info(
            "_check_asaas_customer: Values received:\n%s",
            self.pprint_filtered_response(res),
        )
        return res

    def _create_asaas_customer(self):
        """Create a customer in Asaas."""
        url = "%s/customers" % self.acquirer_id._get_asaas_api_url()
        _logger.info("_create_asaas_customer: Sending values to URL %s", url)
        r = requests.post(
            url,
            json=self._get_asaas_customer_params(),
            headers=self.acquirer_id._get_asaas_api_headers(),
        )
        res = r.json()
        _logger.info(
            "_create_asaas_customer: Values received:\n%s",
            self.pprint_filtered_response(res),
        )
        return res

    def _create_asaas_payment(self, customer_id):
        """Create a payment in Asaas using a card token."""
        url = "%s/payments" % self.acquirer_id._get_asaas_api_url()
        _logger.info("_create_asaas_payment: Sending values to URL %s", url)
        r = requests.post(
            url,
            json=self._get_asaas_payment_params(customer_id),
            headers=self.acquirer_id._get_asaas_api_headers(),
        )
        res = r.json()
        _logger.info(
            "_create_asaas_payment: Values received:\n%s",
            self.pprint_filtered_response(res),
        )
        return res

    def asaas_s2s_do_transaction(self, **kwargs):
        self.ensure_one()
        verify_customer = self._check_asaas_customer()
        if verify_customer.get("data") and len(verify_customer["data"]) > 0:
            customer_id = verify_customer["data"][0]["id"]
        else:
            create_customer = self._create_asaas_customer()
            customer_id = create_customer.get("id")
        res = self._create_asaas_payment(customer_id)
        return self._asaas_s2s_validate_tree(res)

    def _asaas_s2s_validate_tree(self, tree):
        """Validates the Asaas transaction and updates the transaction record."""
        self.ensure_one()
        if self.state != "draft":
            _logger.info(
                "Asaas: trying to validate an already validated tx (ref %s)",
                self.reference,
            )
            return True

        if tree.get("id") and tree.get("status") in (
            "PENDING",
            "RECEIVED",
            "CONFIRMED",
        ):
            self.log_transaction(reference=tree.get("id"), message=tree.get("status"))
            # Store links if provided by Asaas (not always present)
            self.asaas_s2s_check_link = tree.get("url", "")
            # Set transaction state
            if tree.get("status") == "RECEIVED":
                self._set_transaction_done()
            elif tree.get("status") == "CONFIRMED":
                self._set_transaction_done()
            else:
                self._set_transaction_authorized()
            self.execute_callback()
            if self.payment_token_id:
                self.payment_token_id.verified = True
            return True
        else:
            self._validate_tree_message(tree)
            return False

    def _validate_tree_message(self, tree):
        if tree.get("errors"):
            error = tree["errors"][0].get("description", "Unknown error")
            _logger.warning(error)
            self.sudo().write(
                {
                    "state_message": error,
                    "acquirer_reference": tree.get("id"),
                    "date": fields.datetime.now(),
                }
            )
            self._set_transaction_cancel()

    def _get_asaas_customer_params(self):
        """Builds the customer payload for Asaas."""
        return {
            "name": self.partner_name,
            "email": self.partner_email,
            "phone": self.partner_phone,
            "cpfCnpj": self.partner_id.cpf_cnpj_stripped,
            "postalCode": self.partner_zip,
            "address": self.partner_address,
            "addressNumber": self.partner_id.street_number,
            "city": self.partner_city,
            "state": self.partner_state_id.code if self.partner_state_id else "",
            "complement": self.partner_id.street2 or "",
        }

    def _get_asaas_payment_params(self, customer_id):
        """Builds the payment payload for Asaas using a card token."""
        return {
            "billingType": "CREDIT_CARD",
            "customer": customer_id,
            "dueDate": fields.Date.today().strftime("%Y-%m-%d"),
            "value": self.amount,
            "description": self.reference,
            "externalReference": self.reference,
            "creditCardToken": self.payment_token_id.asaas_card_token,
            "creditCardHolderInfo": {
                "name": self.partner_name,
                "email": self.partner_email,
                "cpfCnpj": self.partner_id.cpf_cnpj_stripped,
                "postalCode": self.partner_zip,
                "addressNumber": self.partner_id.street_number,
                "addressComplement": self.partner_id.street2 or "",
                "address": self.partner_address,
                "city": self.partner_city,
                "state": self.partner_state_id.code if self.partner_state_id else "",
                "phone": self.partner_phone,
            },
            "remoteIp": self.env.context.get("remote_ip"),
        }

    def log_transaction(self, reference, message):
        """Logs a transaction. It can be either a successful or a failed one."""
        self.sudo().write(
            {
                "date": fields.datetime.now(),
                "acquirer_reference": reference,
                "state_message": message,
            }
        )

    @staticmethod
    def pprint_filtered_response(response):
        # Returns response removing payment's sensitive information
        output_response = response.copy()
        output_response.pop("links", None)
        output_response.pop("metadata", None)
        output_response.pop("notification_urls", None)
        output_response.pop("payment_method", None)
        return pprint.pformat(output_response)
