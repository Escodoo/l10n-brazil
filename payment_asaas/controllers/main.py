# Copyright 2025 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import pprint
from datetime import date

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class AsaasController(http.Controller):
    @http.route(
        ["/payment/asaas/webhook"],
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def payment_asaas_webhook(self, **kwargs):
        """Handle webhook notifications from Asaas.

        See: https://docs.asaas.com/docs/webhook
        """
        data = request.get_json_data()
        _logger.info("Asaas webhook received:\n%s", pprint.pformat(data))

        event = data.get("event")
        payment = data.get("payment", {})
        external_reference = payment.get("externalReference")
        payment_id = payment.get("id")
        status = payment.get("status")

        # Only process relevant events
        if event in (
            "PAYMENT_CREATED",
            "PAYMENT_RECEIVED",
            "PAYMENT_CONFIRMED",
            "PAYMENT_OVERDUE",
            "PAYMENT_REFUNDED",
            "PAYMENT_DELETED",
            "PAYMENT_UPDATED",
        ):
            try:
                tx = None
                if external_reference:
                    tx = (
                        request.env["payment.transaction"]
                        .sudo()
                        .search([("reference", "=", external_reference)], limit=1)
                    )
                if not tx:
                    _logger.warning(
                        "Asaas: externalReference not found: %s", external_reference
                    )
                    return ""
                tx._handle_notification_data(
                    "asaas",
                    {
                        "external_reference": external_reference,
                        "payment_id": payment_id,
                        "event": event,
                        "status": status,
                        "raw": data,
                    },
                )
            except ValidationError:
                _logger.exception(
                    "Error processing Asaas notification; skipping to avoid spam"
                )
        else:
            _logger.info("Asaas event ignored: %s", event)
        return ""  # Acknowledge webhook receipt to Asaas

    @http.route(
        "/payment/asaas/tokenize_card",
        type="json",
        auth="public",
        csrf=False,
    )
    def asaas_tokenize_card(
        self,
        acquirer_id,
        cc_holder_name,
        cc_number,
        cc_expiry,
        cc_cvc,
        partner_id=None,
        **kwargs,
    ):
        import requests

        payload_customer = None
        data_search = None
        data_create = None
        partner = None

        try:
            exp_month, exp_year = cc_expiry.split("/")
            exp_month = exp_month.strip()
            exp_year = exp_year.strip()
            if len(exp_year) == 2:
                exp_year = "20" + exp_year
        except Exception:
            return {"error": "Invalid expiry format"}

        acquirer = request.env["payment.acquirer"].sudo().browse(int(acquirer_id))
        headers = acquirer._get_asaas_api_headers()
        customer_id = None

        # Buscar ou criar customer no Asaas
        if partner_id:
            partner = request.env["res.partner"].sudo().browse(int(partner_id))
            if partner:
                # Buscar customer pelo CPF/CNPJ
                url_search = (
                    acquirer._get_asaas_api_url()
                    + "/customers?cpfCnpj=%s" % partner.cnpj_cpf_stripped
                )
                resp_search = requests.get(url_search, headers=headers)
                data_search = resp_search.json()
                if data_search.get("data") and len(data_search["data"]) > 0:
                    customer_id = data_search["data"][0]["id"]
                else:
                    # Criar customer se não existir
                    payload_customer = {
                        "name": partner.name,
                        "email": partner.email or "",
                        "cpfCnpj": partner.cnpj_cpf_stripped,
                        "phone": partner.phone or "",
                    }
                    url_create = acquirer._get_asaas_api_url() + "/customers"
                    resp_create = requests.post(
                        url_create, json=payload_customer, headers=headers
                    )
                    _logger.info("Asaas create customer response: %s", resp_create.text)
                    data_create = resp_create.json()
                    customer_id = data_create.get("id")

        if not customer_id:
            return {
                "error": "Customer not found or could not be created in Asaas.",
                "payload_customer": payload_customer,
                "search_response": data_search,
                "create_response": data_create,
                "partner_id": partner_id,
                "cpfCnpj": partner.cnpj_cpf_stripped if partner else None,
                "input_kwargs": kwargs,
                "acquirer_id": acquirer_id,
            }

        # Montar creditCardHolderInfo
        credit_card_holder_info = {
            "name": partner.name if partner else "",
            "email": partner.email or "" if partner else "",
            "cpfCnpj": partner.cnpj_cpf_stripped if partner else "",
            "postalCode": partner.zip or "" if partner else "",
            "addressNumber": partner.street_number or ""
            if partner and hasattr(partner, "street_number")
            else "",
            "phone": partner.phone or "" if partner else "",
        }

        # Tokenizar cartão com o customer_id
        url = acquirer._get_asaas_api_url() + "/creditCard/tokenize"
        payload = {
            "creditCard": {
                "holderName": cc_holder_name,
                "number": cc_number,
                "expiryMonth": exp_month,
                "expiryYear": exp_year,
                "ccv": cc_cvc,
            },
            "creditCardHolderInfo": credit_card_holder_info,
            "customer": customer_id,
            "remoteIp": request.httprequest.remote_addr,
        }

        _logger.info("Payload enviado para Asaas: %s", payload)

        resp = requests.post(url, json=payload, headers=headers)
        _logger.info("Asaas tokenize response: %s", resp.text)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("creditCardToken"):
                return {"cc_token": data["creditCardToken"]}
            else:
                return {
                    "error": data.get("errors", [{}])[0].get(
                        "description", "Tokenization failed"
                    )
                }
        else:
            return {"error": "Tokenization failed: %s" % resp.text}

    @http.route(
        "/payment/asaas/s2s/create_json_3ds",
        type="json",
        auth="public",
        csrf=False,
    )
    def asaas_create_json_3ds(self, **kwargs):
        import requests

        acquirer_id = kwargs.get("acquirer_id")
        customer_id = kwargs.get("customer_id")
        cc_token = kwargs.get("cc_token")
        value = kwargs.get("amount_total")
        if not value:
            return {
                "error": "O valor (amount_total) é obrigatório para criar o pagamento."
            }
        due_date = kwargs.get("due_date") or date.today().strftime("%Y-%m-%d")
        description = kwargs.get("description") or "Pagamento via Asaas"
        partner_id = kwargs.get("partner_id")

        # Buscar partner para montar creditCardHolderInfo
        partner = None
        if partner_id:
            partner = request.env["res.partner"].sudo().browse(int(partner_id))

        credit_card_holder_info = {
            "name": partner.name if partner else "",
            "email": partner.email or "" if partner else "",
            "cpfCnpj": partner.cnpj_cpf_stripped if partner else "",
            "postalCode": (partner.zip or "").replace("-", "").replace(".", "").strip()
            if partner
            else "",
            "addressNumber": partner.street_number or ""
            if partner and hasattr(partner, "street_number")
            else "",
            "phone": partner.phone or "" if partner else "",
        }

        acquirer = request.env["payment.acquirer"].sudo().browse(int(acquirer_id))
        headers = acquirer._get_asaas_api_headers()

        payment_payload = {
            "billingType": "CREDIT_CARD",
            "customer": customer_id,
            "value": float(value),
            "dueDate": due_date,
            "description": description,
            "remoteIp": request.httprequest.remote_addr,
            "creditCardToken": cc_token,
            "creditCardHolderInfo": credit_card_holder_info,
        }

        url = acquirer._get_asaas_api_url() + "/payments"
        resp = requests.post(url, json=payment_payload, headers=headers)
        _logger.info("Asaas payment response: %s", resp.text)
        data = resp.json()
        if resp.status_code == 200 and data.get("id"):
            return {"id": data["id"], "asaas_payment": data}
        else:
            return {
                "error": data.get("errors", [{}])[0].get(
                    "description", "Payment creation failed"
                ),
                "asaas_response": data,
            }
