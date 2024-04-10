# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import pprint

import requests

from odoo import fields, models
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):

    _inherit = "payment.transaction"

    asaas_s2s_capture_link = fields.Char(
        string="Capture Link Asaas",
        required=False,
    )
    asaas_s2s_void_link = fields.Char(
        string="Cancel Link",
        required=False,
    )
    asaas_s2s_check_link = fields.Char(
        string="Check Link Asaas",
        required=False,
    )

    def _check_asaas_customer(self):
        """Check exists the s2s Customer."""

        url = "https://%s/v3/customers?cpfCnpj=%s" % (
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
        """Creates the s2s Customer."""

        url = "https://%s/v3/customers" % (self.acquirer_id._get_asaas_api_url())

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
        url = "https://%s/v3/payments/" % (self.acquirer_id._get_asaas_api_url())

        self.payment_token_id.active = False

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
        if len(verify_customer["data"]) > 0:
            customer_id = verify_customer["data"][0]["id"]
            res = self._create_asaas_payment(customer_id)
        else:
            create_customer = self._create_asaas_customer()
            customer_id = create_customer["id"]
            res = self._create_asaas_payment(customer_id)

        return res

    def _get_asaas_customer_params(self):
        """
        Returns dict containing the required body information to create a
        Customer on Asaas.

        Returns:
            dict: Customer parameters
        """

        CUSTOMER_PARAMS = {
            "name": self.partner_name,
            "email": self.partner_email,
            "phone": self.partner_phone,
            "cpfCnpj": self.partner_id.vat,
            "postalCode": self.partner_zip,
            "address": self.partner_address,
            "addressNumber": self.partner_id.street_number,
            "city": self.partner_city,
            "state": self.partner_country_id.name,
            "complement": self.partner_id.street2 or False,
        }

        return CUSTOMER_PARAMS

    def _get_asaas_payment_params(self, customer_id):
        """
        Returns dict containing the required body information to create a
        Payment on Asaas.

        Returns:
            dict: Payment parameters
        """

        PAYMENT_PARAMS = {
            "billingType": "CREDIT_CARD",
            "customer": customer_id,
            "dueDate": self.create_date.strftime("%Y-%m-%d"),
            "value": self.amount,
            "description": self.reference,
            "externalReference": self.reference,
            "creditCard": {
                "holderName": "john doe",
                "number": "5162306219378829",
                "expiryMonth": "05",
                "expiryYear": "2025",
                "ccv": "318",
            },
            "creditCardHolderInfo": {
                "name": self.partner_name,
                "email": self.partner_email,
                "cpfCnpj": self.partner_id.vat,
                "postalCode": self.partner_zip,
                "phone": self.partner_phone,
                "address": self.partner_address,
                "addressNumber": self.partner_id.street_number,
                "city": self.partner_city,
                "state": self.partner_country_id.name,
            },
            "remoteIp": request.httprequest.remote_addr,
        }

        return PAYMENT_PARAMS

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
