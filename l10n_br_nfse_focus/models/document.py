# Copyright 2023 - TODAY, KMEE INFORMATICA LTDA
# Copyright 2023 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import json
import logging
from datetime import datetime

import pytz
import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_br_fiscal.constants.fiscal import (
    EVENT_ENV_HML,
    EVENT_ENV_PROD,
    SITUACAO_EDOC_AUTORIZADA,
    SITUACAO_EDOC_CANCELADA,
    SITUACAO_EDOC_ENVIADA,
    SITUACAO_EDOC_REJEITADA,
)
from odoo.addons.l10n_br_fiscal_edi.models.document import Document as FiscalDocument
from odoo.addons.l10n_br_nfse.models.document import filter_processador_edoc_nfse

NFSE_URL = {
    "1": "https://api.focusnfe.com.br",
    "2": "https://homologacao.focusnfe.com.br",
}

API_ENDPOINT = {
    "envio": "/v2/nfse?",
    "status": "/v2/nfse/",
    "resposta": "/v2/nfse/",
    "cancelamento": "/v2/nfse/",
}

TIMEOUT = 60  # 60 seconds

# Constants for document status
STATUS_AUTORIZADO = "autorizado"
STATUS_CANCELADO = "cancelado"
STATUS_ERRO_AUTORIZACAO = "erro_autorizacao"
STATUS_PROCESSANDO_AUTORIZACAO = "processando_autorizacao"
CODE_NFE_CANCELADA = "nfe_cancelada"
CODE_NFE_AUTORIZADA = "nfe_autorizada"

# CPF/CNPJ length constants
CPF_LENGTH = 11
CNPJ_LENGTH = 14

# PDF validation constants
PDF_HEADER = b"%PDF-"
PDF_FOOTER = b"%%EOF"

_logger = logging.getLogger(__name__)


def filter_focusnfe(record):
    return record.company_id.provedor_nfse == "focusnfe"


def filter_focusnfe_nacional(record):
    return (
        record.company_id.provedor_nfse == "focusnfe"
        and record.company_id.focusnfe_nfse_type == "nfse_nacional"
    )


def filter_focusnfe_municipal(record):
    return (
        record.company_id.provedor_nfse == "focusnfe"
        and record.company_id.focusnfe_nfse_type == "nfse"
    )


def _clean_cpf_cnpj(value):
    """Remove formatting from CPF/CNPJ string.

    Args:
        value (str): CPF or CNPJ string with formatting.

    Returns:
        str: Cleaned CPF/CNPJ string with only digits.
    """
    if not value:
        return ""
    return value.replace(".", "").replace("/", "").replace("-", "")


def _identify_cpf_cnpj(cpf, cnpj):
    """Identify if the provided values are CPF or CNPJ.

    Args:
        cpf (str): CPF value.
        cnpj (str): CNPJ value.

    Returns:
        tuple: (is_cpf, is_cnpj, cleaned_cpf, cleaned_cnpj)
    """
    cleaned_cpf = _clean_cpf_cnpj(cpf) if cpf else ""
    cleaned_cnpj = _clean_cpf_cnpj(cnpj) if cnpj else ""
    is_cpf = bool(cleaned_cpf and len(cleaned_cpf) == CPF_LENGTH)
    is_cnpj = bool(cleaned_cnpj and len(cleaned_cnpj) == CNPJ_LENGTH)
    return is_cpf, is_cnpj, cleaned_cpf, cleaned_cnpj


def _is_valid_pdf(content):
    """Check if content is a valid PDF.

    Args:
        content (bytes): PDF content to validate.

    Returns:
        bool: True if content is a valid PDF, False otherwise.
    """
    return content.startswith(PDF_HEADER) and content.strip().endswith(PDF_FOOTER)


class FocusnfeNfseBase(models.AbstractModel):
    """Base class for FocusNFE NFSe operations with shared HTTP request logic."""

    _name = "focusnfe.nfse.base"
    _description = "FocusNFE NFSE Base"

    def _make_focus_nfse_http_request(
        self, method, url, token, data=None, params=None, service_name="NFSe"
    ):
        """Perform a generic HTTP request.

        Args:
            method (str): The HTTP method to use (e.g., 'GET', 'POST').
            url (str): The URL to which the request is sent.
            token (str): The authentication token for the service.
            data (dict, optional): The payload to send in the request body.
                Defaults to None.
            params (dict, optional): The URL parameters to append to the URL.
                Defaults to None.

        Returns:
            requests.Response: The response object from the requests library.

        Raises:
            UserError: If the HTTP request fails with a 4xx/5xx response.
        """
        auth = (token, "")
        try:
            response = requests.request(  # pylint: disable=external-request-timeout
                method,
                url,
                data=data,
                params=params,
                auth=auth,
            )
            if response.status_code == 422:
                payload = response.json()
                msg = payload.get("mensagem") or ""
                raise UserError(
                    f"Error communicating with {service_name} service: {msg}"
                )
            response.raise_for_status()  # Raises an error for 4xx/5xx responses
            return response
        except requests.HTTPError as e:
            raise UserError(
                _("Error communicating with %(service)s service: %(error)s")
                % {"service": service_name, "error": e}
            ) from e


class FocusnfeNfse(FocusnfeNfseBase):
    _name = "focusnfe.nfse"
    _description = "FocusNFE NFSE"

    def _make_focus_nfse_http_request(self, method, url, token, data=None, params=None):
        """Perform a generic HTTP request.

        Args:
            method (str): The HTTP method to use (e.g., 'GET', 'POST').
            url (str): The URL to which the request is sent.
            token (str): The authentication token for the service.
            data (dict, optional): The payload to send in the request body.
                Defaults to None.
            params (dict, optional): The URL parameters to append to the URL.
                Defaults to None.

        Returns:
            requests.Response: The response object from the requests library.

        Raises:
            UserError: If the HTTP request fails with a 4xx/5xx response.
        """
        return super()._make_focus_nfse_http_request(
            method, url, token, data, params, service_name="NFSe"
        )

    def _identify_service_recipient(self, recipient):
        """Identify whether the service recipient is a CPF or CNPJ.

        Args:
            recipient (dict): A dictionary containing either 'cpf' or 'cnpj' keys.

        Returns:
            dict: A dictionary with either a 'cpf' or 'cnpj' key and its value.
        """
        return (
            {"cpf": recipient.get("cpf")}
            if recipient.get("cpf")
            else {"cnpj": recipient.get("cnpj")}
        )

    @api.model
    def process_focus_nfse_document(self, edoc, ref, company, environment):
        """Process the electronic fiscal document.

        Args:
            edoc (tuple): The electronic document data.
            ref (str): The document reference.
            company (recordset): The company record.

        Returns:
            requests.Response: The response from the NFSe service.
        """
        token = company.get_focusnfe_token()
        data = self._prepare_payload(*edoc, company)
        payload = json.dumps(data)
        url = f"{NFSE_URL[environment]}{API_ENDPOINT['envio']}"
        ref = {"ref": ref}
        return self._make_focus_nfse_http_request(
            "POST", url, token, data=payload, params=ref
        )

    def _prepare_payload(self, rps, service, recipient, company):
        """Construct the NFSe payload.

        Args:
            rps (dict): Information about the RPS.
            service (dict): Details of the service provided.
            recipient (dict): Information about the service recipient.
            company (recordset): The company record.

        Returns:
            dict: The complete payload for the NFSe request.
        """
        rps_info = rps.get("rps")
        service_info = service.get("service")
        recipient_info = recipient.get("recipient")
        recipient_identification = self._identify_service_recipient(recipient_info)

        vals = {
            "prestador": self._prepare_provider_data(rps_info, company),
            "servico": self._prepare_service_data(service_info, company),
            "tomador": self._prepare_recipient_data(
                recipient_info, recipient_identification, company
            ),
            "razao_social": company.name,
            "data_emissao": rps_info.get("data_emissao"),
            "incentivador_cultural": rps_info.get("incentivador_cultural", False),
            "natureza_operacao": rps_info.get("natureza_operacao"),
            "optante_simples_nacional": rps_info.get("optante_simples_nacional", False),
            "status": rps_info.get("status"),
            "informacoes_adicionais_contribuinte": (
                rps_info.get("customer_additional_data", False)[:256]
                if rps_info.get("customer_additional_data")
                else False
            ),
        }
        codigo_obra = rps_info.get("codigo_obra", False)
        art = rps_info.get("art", False)

        if codigo_obra:
            vals["codigo_obra"] = codigo_obra

        if art:
            vals["art"] = art

        return vals

    def _prepare_provider_data(self, rps, company):
        """Construct the provider section of the payload.

        Args:
            rps (dict): Information about the RPS.
            company (recordset): The company record.

        Returns:
            dict: The provider section of the payload.
        """
        return {
            "cnpj": rps.get("cnpj"),
            "inscricao_municipal": rps.get("inscricao_municipal"),
            "codigo_municipio": company.city_id.ibge_code,
        }

    def _prepare_service_data(self, service, company):
        """Construct the service section of the payload.

        Args:
            service (dict): Details of the service provided.
            company (recordset): The company record.

        Returns:
            dict: The service section of the payload.
        """
        return {
            "aliquota": service.get("aliquota")
            if company.focusnfe_tax_rate_format == "decimal"
            else round(service.get("aliquota", 0.0) * 100, 1),
            "base_calculo": round(service.get("base_calculo", 0), 2),
            "discriminacao": service.get("discriminacao"),
            "iss_retido": service.get("iss_retido"),
            "codigo_municipio": service.get("municipio_prestacao_servico"),
            "item_lista_servico": service.get(company.focusnfe_nfse_service_type_value),
            "codigo_cnae": service.get(company.focusnfe_nfse_cnae_code_value),
            "valor_iss": round(service.get("valor_iss", 0), 2),
            "valor_iss_retido": round(service.get("valor_iss_retido", 0), 2),
            "valor_pis": round(service.get("valor_pis_retido", 0), 2),
            "valor_cofins": round(service.get("valor_cofins_retido", 0), 2),
            "valor_inss": round(service.get("valor_inss_retido", 0), 2),
            "valor_ir": round(service.get("valor_ir_retido", 0), 2),
            "valor_csll": round(service.get("valor_csll_retido", 0), 2),
            "valor_deducoes": round(service.get("valor_deducoes", 0), 2),
            "fonte_total_tributos": service.get("fonte_total_tributos", "IBPT"),
            "desconto_incondicionado": round(
                service.get("valor_desconto_incondicionado", 0), 2
            ),
            "desconto_condicionado": round(service.get("desconto_condicionado", 0), 2),
            "outras_retencoes": round(service.get("outras_retencoes", 0), 2),
            "valor_servicos": round(service.get("valor_servicos", 0), 2),
            "valor_liquido": round(service.get("valor_liquido_nfse", 0), 2),
            "codigo_tributario_municipio": service.get("codigo_tributacao_municipio"),
            "codigo_nbs": service.get("codigo_nbs"),
            "codigo_indicador_operacao": service.get("codigo_indicador_operacao"),
            "codigo_classificacao_tributaria": service.get(
                "codigo_classificacao_tributaria"
            ),
            "codigo_situacao_tributaria": service.get("codigo_situacao_tributaria"),
            "ibs_cbs_base_calculo": service.get("ibs_cbs_base_calculo"),
            "ibs_uf_aliquota": round(service.get("ibs_uf_aliquota", 0), 2)
            if service.get("ibs_uf_aliquota")
            else None,
            "ibs_mun_aliquota": 0.0,
            "cbs_aliquota": round(service.get("cbs_aliquota", 0), 2)
            if service.get("cbs_aliquota")
            else None,
            "ibs_uf_valor": round(service.get("ibs_uf_valor", 0), 2)
            if service.get("ibs_uf_valor")
            else None,
            "ibs_mun_valor": 0.0,
            "cbs_valor": round(service.get("cbs_valor", 0), 2)
            if service.get("cbs_valor")
            else None,
        }

    def _prepare_recipient_data(self, recipient, identification, company):
        """Construct the recipient section of the payload.

        Args:
            recipient (dict): Information about the service recipient.
            identification (dict): The recipient's identification (CPF or CNPJ).
            company (recordset): The company record.
        Returns:
            dict: The recipient section of the payload.
        """

        if recipient.get("nif"):
            recipient["codigo_municipio"] = company.city_id.ibge_code

        return {
            **identification,
            "nif": recipient.get("nif"),
            "nif_motivo_ausencia": recipient.get("nif_motivo_ausencia"),
            "razao_social": recipient.get("razao_social"),
            "email": recipient.get("email"),
            "endereco": {
                "bairro": recipient.get("bairro"),
                "cep": recipient.get("cep"),
                "codigo_municipio": recipient.get("codigo_municipio"),
                "logradouro": recipient.get("endereco"),
                "numero": recipient.get("numero"),
                "uf": recipient.get("uf"),
            },
        }

    @api.model
    def query_focus_nfse_by_rps(self, ref, complete, company, environment):
        """Query NFSe by RPS.

        Args:
            ref (str): The RPS reference.
            complete (bool): Whether to return complete information.
            company (recordset): The company record.

        Returns:
            requests.Response: The response from the NFSe service.
        """
        token = company.get_focusnfe_token()
        url = f"{NFSE_URL[environment]}{API_ENDPOINT['status']}{ref}"
        return self._make_focus_nfse_http_request(
            "GET", url, token, params={"completa": complete}
        )

    @api.model
    def cancel_focus_nfse_document(self, ref, cancel_reason, company, environment):
        """Cancel an electronic fiscal document.

        Args:
            ref (str): The document reference.
            cancel_reason (str): The reason for cancellation.
            company (recordset): The company record.

        Returns:
            requests.Response: The response from the NFSe service.
        """
        token = company.get_focusnfe_token()
        data = {"justificativa": cancel_reason}
        url = f"{NFSE_URL[environment]}{API_ENDPOINT['cancelamento']}{ref}"
        return self._make_focus_nfse_http_request(
            "DELETE", url, token, data=json.dumps(data)
        )


API_ENDPOINT_NACIONAL = {
    "envio": "/v2/nfsen",
    "status": "/v2/nfsen/",
    "resposta": "/v2/nfsen/",
    "cancelamento": "/v2/nfsen/",
}


class FocusnfeNfseNacional(FocusnfeNfseBase):
    _name = "focusnfe.nfse.nacional"
    _description = "FocusNFE NFSe Nacional"

    def _make_focus_nfse_http_request(self, method, url, token, data=None, params=None):
        """Perform a generic HTTP request.

        Args:
            method (str): The HTTP method to use (e.g., 'GET', 'POST').
            url (str): The URL to which the request is sent.
            token (str): The authentication token for the service.
            data (dict, optional): The payload to send in the request body.
                Defaults to None.
            params (dict, optional): The URL parameters to append to the URL.
                Defaults to None.

        Returns:
            requests.Response: The response object from the requests library.

        Raises:
            UserError: If the HTTP request fails with a 4xx/5xx response.
        """
        return super()._make_focus_nfse_http_request(
            method, url, token, data, params, service_name="NFSe Nacional"
        )

    @api.model
    def process_focus_nfse_nacional_document(self, edoc, ref, company, environment):
        """Process the electronic fiscal document for NFSe Nacional.

        Args:
            edoc (dict): The electronic document data.
            ref (str): The document reference.
            company (recordset): The company record.
            environment (str): The environment (1=production, 2=homologation).

        Returns:
            requests.Response: The response from the NFSe Nacional service.
        """
        token = company.get_focusnfe_token()
        data = self._prepare_payload_nacional(edoc, company)
        payload = json.dumps(data)
        url = f"{NFSE_URL[environment]}{API_ENDPOINT_NACIONAL['envio']}"
        ref_params = {"ref": ref}
        return self._make_focus_nfse_http_request(
            "POST", url, token, data=payload, params=ref_params
        )

    def _prepare_dates_nacional(self, rps_info):
        """Prepare emission and competence dates for NFSe Nacional.

        Args:
            rps_info (dict): RPS information.

        Returns:
            tuple: (emission_date, competence_date)
        """
        emission_date = rps_info.get("data_emissao", "")
        if emission_date and not emission_date.endswith(("-0300", "-0200", "+0000")):
            # Add timezone if not present (assuming -0300 for Brazil)
            emission_date = emission_date + "-0300"

        competence_date = (
            rps_info.get("data_emissao", "")[:10]
            if rps_info.get("data_emissao")
            else ""
        )

        return emission_date, competence_date

    def _prepare_provider_nacional(self, rps_info, company):
        """Prepare provider data for NFSe Nacional.

        Args:
            rps_info (dict): RPS information.
            company (recordset): The company record.

        Returns:
            dict: Provider data with CPF/CNPJ identification.
        """
        cnpj_prestador = rps_info.get("cnpj", "")
        cpf_prestador = rps_info.get("cpf", "")
        (
            is_cpf_prestador,
            is_cnpj_prestador,
            cpf_prestador_limpo,
            cnpj_prestador_limpo,
        ) = _identify_cpf_cnpj(cpf_prestador, cnpj_prestador)

        optante_simples = rps_info.get("optante_simples_nacional", "1")
        codigo_opcao_simples_nacional = "2" if optante_simples == "1" else "1"

        regime_especial_tributacao = (
            rps_info.get("regime_especial_tributacao", "0") or "0"
        )

        return {
            "is_cpf": is_cpf_prestador,
            "is_cnpj": is_cnpj_prestador,
            "cpf_limpo": cpf_prestador_limpo,
            "cnpj_limpo": cnpj_prestador_limpo,
            "codigo_opcao_simples_nacional": codigo_opcao_simples_nacional,
            "regime_especial_tributacao": regime_especial_tributacao,
            "codigo_municipio_emissora": str(company.city_id.ibge_code or ""),
        }

    def _prepare_recipient_nacional(self, recipient_info):
        """Prepare recipient data for NFSe Nacional.

        Args:
            recipient_info (dict): Recipient information.

        Returns:
            dict: Recipient data with CPF/CNPJ identification.
        """
        cnpj_tomador = recipient_info.get("cnpj", "")
        cpf_tomador = recipient_info.get("cpf", "")
        is_cpf, is_cnpj, cpf_limpo, cnpj_limpo = _identify_cpf_cnpj(
            cpf_tomador, cnpj_tomador
        )

        cep_tomador = recipient_info.get("cep", "")
        if isinstance(cep_tomador, int):
            cep_tomador = str(cep_tomador)

        return {
            "is_cpf": is_cpf,
            "is_cnpj": is_cnpj,
            "cpf_limpo": cpf_limpo,
            "cnpj_limpo": cnpj_limpo,
            "razao_social": recipient_info.get("razao_social", ""),
            "codigo_municipio": str(recipient_info.get("codigo_municipio", "")),
            "cep": cep_tomador or "",
            "logradouro": recipient_info.get("endereco", ""),
            "numero": recipient_info.get("numero", ""),
            "complemento": recipient_info.get("complemento", ""),
            "bairro": recipient_info.get("bairro", ""),
            "telefone": recipient_info.get("telefone", ""),
            "email": recipient_info.get("email", ""),
        }

    def _prepare_service_basic_nacional(self, service_info):
        """Prepare basic service data for NFSe Nacional.

        Args:
            service_info (dict): Service information.

        Returns:
            dict: Basic service data.
        """
        codigo_municipio_prestacao = service_info.get("municipio_prestacao_servico", "")

        codigo_tributacao_nacional_iss = service_info.get(
            "codigo_tributacao_nacional_iss", ""
        )
        if not codigo_tributacao_nacional_iss:
            codigo_tributacao_nacional_iss = service_info.get(
                "codigo_tributacao_municipio", ""
            )
        if not codigo_tributacao_nacional_iss:
            codigo_tributacao_nacional_iss = service_info.get("item_lista_servico", "")

        # TODO: improve logic to get ISS taxation code
        tributacao_iss = 1

        # TODO: improve logic to get ISS retention code
        tipo_retencao_iss = "2" if service_info.get("iss_retido") == "1" else "1"

        return {
            "codigo_municipio_prestacao": str(codigo_municipio_prestacao),
            "codigo_tributacao_nacional_iss": codigo_tributacao_nacional_iss,
            "descricao": service_info.get("discriminacao", ""),
            "valor": round(service_info.get("valor_servicos", 0), 2),
            "tributacao_iss": str(tributacao_iss),
            "tipo_retencao_iss": str(tipo_retencao_iss),
        }

    def _prepare_tax_data_nacional(self, service_info, valor_servico):
        """Prepare tax data (PIS/COFINS, etc.) for NFSe Nacional.

        Args:
            service_info (dict): Service information.
            valor_servico (float): Service value.

        Returns:
            dict: Tax data.
        """
        # PIS/COFINS tax situation
        situacao_tributaria_pis_cofins = (
            service_info.get("situacao_tributaria_pis", "")
            or service_info.get("situacao_tributaria_cofins", "")
            or ""
        )
        if situacao_tributaria_pis_cofins == "99":
            situacao_tributaria_pis_cofins = "00"

        # PIS/COFINS calculation base
        base_calculo_pis = service_info.get("base_calculo_pis", 0)
        base_calculo_cofins = service_info.get("base_calculo_cofins", 0)
        base_calculo_pis_cofins = round(
            base_calculo_pis if base_calculo_pis else base_calculo_cofins, 2
        )

        if situacao_tributaria_pis_cofins:
            if situacao_tributaria_pis_cofins in ["00", "08", "09"]:
                base_calculo_pis_cofins = 0.0
            else:
                if not base_calculo_pis_cofins or base_calculo_pis_cofins == 0:
                    base_calculo_pis_cofins = round(valor_servico, 2)

        # Format rates as strings with 2 decimal places
        aliquota_pis_raw = round(service_info.get("aliquota_pis", 0), 2)
        aliquota_pis = f"{aliquota_pis_raw:.2f}"
        aliquota_cofins_raw = round(service_info.get("aliquota_cofins", 0), 2)
        aliquota_cofins = f"{aliquota_cofins_raw:.2f}"

        return {
            "situacao_tributaria_pis_cofins": situacao_tributaria_pis_cofins or "",
            "base_calculo_pis_cofins": round(base_calculo_pis_cofins, 2),
            "aliquota_pis": aliquota_pis,
            "aliquota_cofins": aliquota_cofins,
            "valor_pis": round(service_info.get("valor_pis", 0), 2),
            "valor_cofins": round(service_info.get("valor_cofins", 0), 2),
            "tipo_retencao_pis_cofins": service_info.get(
                "tipo_retencao_pis_cofins", "2"
            ),
            "valor_cp": round(service_info.get("valor_inss_retido", 0), 2),
            "valor_irrf": round(service_info.get("valor_ir_retido", 0), 2),
            "valor_csll": round(service_info.get("valor_csll_retido", 0), 2),
        }

    def _prepare_payload_nacional(self, edoc, company):
        """Construct the NFSe Nacional payload.

        Args:
            edoc (dict): The electronic document data containing rps,
                service, recipient.
            company (recordset): The company record.

        Returns:
            dict: The complete payload for the NFSe Nacional request.
        """
        rps_info = edoc.get("rps", {})
        service_info = edoc.get("service", {})
        recipient_info = edoc.get("recipient", {})

        # Prepare dates
        emission_date, competence_date = self._prepare_dates_nacional(rps_info)

        # Prepare provider data
        provider_data = self._prepare_provider_nacional(rps_info, company)

        # Prepare recipient data
        recipient_data = self._prepare_recipient_nacional(recipient_info)

        # Prepare service data
        service_basic = self._prepare_service_basic_nacional(service_info)
        tax_data = self._prepare_tax_data_nacional(service_info, service_basic["valor"])

        # Build payload
        payload = {
            "data_emissao": emission_date,
            "data_competencia": competence_date,
            "codigo_municipio_emissora": provider_data["codigo_municipio_emissora"],
            **(
                {"cnpj_prestador": provider_data["cnpj_limpo"]}
                if provider_data["is_cnpj"]
                else {}
            ),
            **(
                {"cpf_prestador": provider_data["cpf_limpo"]}
                if provider_data["is_cpf"]
                else {}
            ),
            "codigo_opcao_simples_nacional": provider_data[
                "codigo_opcao_simples_nacional"
            ],
            "regime_especial_tributacao": provider_data["regime_especial_tributacao"],
            **(
                {"cnpj_tomador": recipient_data["cnpj_limpo"]}
                if recipient_data["is_cnpj"]
                else {}
            ),
            **(
                {"cpf_tomador": recipient_data["cpf_limpo"]}
                if recipient_data["is_cpf"]
                else {}
            ),
            "razao_social_tomador": recipient_data["razao_social"],
            "codigo_municipio_tomador": recipient_data["codigo_municipio"],
            "cep_tomador": recipient_data["cep"],
            "logradouro_tomador": recipient_data["logradouro"],
            "numero_tomador": recipient_data["numero"],
            "complemento_tomador": recipient_data["complemento"],
            "bairro_tomador": recipient_data["bairro"],
            "telefone_tomador": recipient_data["telefone"],
            "email_tomador": recipient_data["email"],
            "codigo_municipio_prestacao": service_basic["codigo_municipio_prestacao"],
            "codigo_tributacao_nacional_iss": service_basic[
                "codigo_tributacao_nacional_iss"
            ],
            "descricao_servico": service_basic["descricao"],
            "valor_servico": service_basic["valor"],
            "tributacao_iss": service_basic["tributacao_iss"],
            "tipo_retencao_iss": service_basic["tipo_retencao_iss"],
            **tax_data,
        }

        return payload

    @api.model
    def query_focus_nfse_nacional_by_ref(self, ref, company, environment):
        """Query NFSe Nacional by reference.

        Args:
            ref (str): The document reference.
            company (recordset): The company record.
            environment (str): The environment (1=production, 2=homologation).

        Returns:
            requests.Response: The response from the NFSe Nacional service.
        """
        token = company.get_focusnfe_token()
        url = f"{NFSE_URL[environment]}{API_ENDPOINT_NACIONAL['status']}{ref}"
        return self._make_focus_nfse_http_request("GET", url, token)

    @api.model
    def cancel_focus_nfse_nacional_document(
        self, ref, cancel_reason, company, environment
    ):
        """Cancel an electronic fiscal document for NFSe Nacional.

        Args:
            ref (str): The document reference.
            cancel_reason (str): The reason for cancellation.
            company (recordset): The company record.
            environment (str): The environment (1=production, 2=homologation).

        Returns:
            requests.Response: The response from the NFSe Nacional service.
        """
        token = company.get_focusnfe_token()
        data = {"justificativa": cancel_reason}
        url = f"{NFSE_URL[environment]}{API_ENDPOINT_NACIONAL['cancelamento']}{ref}"
        return self._make_focus_nfse_http_request(
            "DELETE", url, token, data=json.dumps(data)
        )


class Document(models.Model):
    _inherit = "l10n_br_fiscal.document"

    def make_focus_nfse_pdf(self, content):
        """Generate a PDF for a NFSe document using Focus NFSe service.

        Parameters:
            - content: The binary content of the PDF to be attached.

        Returns:
            None. Creates or updates an 'ir.attachment' record with the PDF content.
        """
        if not self.filtered(filter_processador_edoc_nfse).filtered(filter_focusnfe):
            return super().make_pdf()
        else:
            if self.document_number:
                filename = "NFS-e-" + self.document_number + ".pdf"
            else:
                filename = "RPS-" + self.rps_number + ".pdf"

            vals_dict = {
                "name": filename,
                "res_model": self._name,
                "res_id": self.id,
                "datas": base64.b64encode(content),
                "mimetype": "application/pdf",
                "type": "binary",
            }
            if self.file_report_id:
                self.file_report_id.write(vals_dict)
            else:
                self.file_report_id = self.env["ir.attachment"].create(vals_dict)

    def _serialize(self, edocs):
        """Serialize electronic documents (edocs) for sending to the NFSe provider.

        Parameters:
            - edocs: The initial list of electronic documents to serialize.

        Returns:
            The updated list of serialized electronic documents, including additional
            NFSe-specific information.
        """
        edocs = super()._serialize(edocs)
        # Handle NFSe Nacional
        for record in self.filtered(filter_processador_edoc_nfse).filtered(
            filter_focusnfe_nacional
        ):
            edoc = {
                "rps": record._prepare_lote_rps(),
                "service": record._prepare_dados_servico(),
                "recipient": record._prepare_dados_tomador(),
            }
            edocs.append(edoc)
        # Handle NFSe Municipal (original)
        for record in self.filtered(filter_processador_edoc_nfse).filtered(
            filter_focusnfe_municipal
        ):
            edoc = []
            edoc.append({"rps": record._prepare_lote_rps()})
            edoc.append({"service": record._prepare_dados_servico()})
            edoc.append({"recipient": record._prepare_dados_tomador()})
            edocs.append(edoc)
        return edocs

    def _document_export(self, pretty_print=True):
        """Prepare and export the document's electronic information.

        Parameters:
            - pretty_print: A boolean indicating whether the exported data should be
            formatted for readability.

        Returns:
            The result of the document export operation.
        """
        if self.filtered(filter_processador_edoc_nfse).filtered(filter_focusnfe):
            result = super(FiscalDocument, self)._document_export()
        else:
            result = super()._document_export()
        for record in self.filtered(filter_processador_edoc_nfse).filtered(
            filter_focusnfe
        ):
            event_id = record.event_ids.create_event_save_xml(
                company_id=record.company_id,
                environment=(
                    EVENT_ENV_PROD if record.nfse_environment == "1" else EVENT_ENV_HML
                ),
                event_type="0",
                xml_file="",
                document_id=record,
            )
            record.authorization_event_id = event_id
        return result

    def _parse_authorization_datetime(self, json_data):
        """Parse authorization datetime from JSON data.

        Args:
            json_data (dict): JSON response data.

        Returns:
            datetime: Naive datetime in UTC.
        """
        aware_datetime = datetime.strptime(
            json_data["data_emissao"], "%Y-%m-%dT%H:%M:%S%z"
        )
        utc_datetime = aware_datetime.astimezone(pytz.utc)
        return utc_datetime.replace(tzinfo=None)

    def _fetch_xml_from_path(self, record, xml_path):
        """Fetch XML content from the given path.

        Args:
            record: The document record.
            xml_path (str): Path to XML file.

        Returns:
            str: XML content as string, empty if path is invalid.
        """
        if not xml_path:
            return ""
        try:
            return requests.get(
                NFSE_URL[record.nfse_environment] + xml_path,
                timeout=TIMEOUT,
            ).content.decode("utf-8")
        except Exception as e:
            _logger.warning("Failed to fetch XML from %s: %s", xml_path, e)
            return ""

    def _fetch_pdf_from_urls(self, record, json_data, use_url_first=False):
        """Fetch PDF content from URLs in JSON data.

        Args:
            record: The document record.
            json_data (dict): JSON response data.
            use_url_first (bool): If True, try 'url' first, then 'url_danfse'.
                                 If False, only try 'url_danfse'.

        Returns:
            bytes: PDF content, or None if not found or invalid.
        """
        if record.company_id.focusnfe_nfse_force_odoo_danfse:
            return None

        pdf_url = None
        if use_url_first:
            pdf_url = json_data.get("url")
            if pdf_url:
                try:
                    pdf_content = requests.get(
                        pdf_url,
                        timeout=TIMEOUT,
                        verify=record.company_id.nfse_ssl_verify,
                    ).content
                    if _is_valid_pdf(pdf_content):
                        return pdf_content
                except Exception as e:
                    _logger.warning("Failed to fetch PDF from %s: %s", pdf_url, e)

        pdf_url = json_data.get("url_danfse", "")
        if pdf_url:
            try:
                pdf_content = requests.get(
                    pdf_url,
                    timeout=TIMEOUT,
                    verify=record.company_id.nfse_ssl_verify,
                ).content
                if _is_valid_pdf(pdf_content):
                    return pdf_content
            except Exception as e:
                _logger.warning("Failed to fetch PDF from %s: %s", pdf_url, e)

        return None

    def _process_authorized_status_base(
        self,
        record,
        json_data,
        verify_code_key="codigo_verificacao",
        use_url_first=False,
        xml_required=True,
    ):
        """Base method to process authorized status.

        Args:
            record: The document record.
            json_data (dict): JSON response data.
            verify_code_key (str): Key to get verification code from json_data.
            use_url_first (bool): Whether to try 'url' first for PDF.
            xml_required (bool): Whether XML path is required (municipal)
                or optional (nacional).
        """
        naive_datetime = self._parse_authorization_datetime(json_data)
        verify_code = (
            json_data.get(verify_code_key, "")
            if verify_code_key
            else json_data.get("codigo_verificacao", "")
        )
        document_number = json_data.get("numero", "")

        record.write(
            {
                "verify_code": verify_code,
                "document_number": document_number,
                "authorization_date": naive_datetime,
            }
        )

        xml_path = json_data.get("caminho_xml_nota_fiscal", "")
        if xml_required and not xml_path:
            # Will raise KeyError if not present
            xml_path = json_data.get("caminho_xml_nota_fiscal")

        xml = self._fetch_xml_from_path(record, xml_path) if xml_path else ""

        if not record.authorization_event_id:
            record._document_export()

        if record.authorization_event_id:
            # For municipal, xml is required; for nacional, only if available
            if xml_required or xml:
                record.authorization_event_id.set_done(
                    status_code=4,
                    response=_("Successfully Processed"),
                    protocol_date=record.authorization_date,
                    protocol_number=record.authorization_protocol,
                    file_response_xml=xml,
                )
                record._change_state(SITUACAO_EDOC_AUTORIZADA)

                if record.company_id.focusnfe_nfse_force_odoo_danfse:
                    record.make_pdf()
                else:
                    pdf_content = self._fetch_pdf_from_urls(
                        record, json_data, use_url_first
                    )
                    if pdf_content:
                        record.make_focus_nfse_pdf(pdf_content)

    def _process_authorized_status_nacional(self, record, json_data):
        """Process authorized status for NFSe Nacional."""
        self._process_authorized_status_base(
            record,
            json_data,
            verify_code_key="codigo_verificacao",
            use_url_first=False,
            xml_required=False,
        )

    def _process_authorized_status_municipal(self, record, json_data):
        """Process authorized status for NFSe Municipal."""
        self._process_authorized_status_base(
            record,
            json_data,
            verify_code_key="codigo_verificacao",
            use_url_first=True,
            xml_required=True,
        )

    def _process_error_status(self, record, json_data):
        """Process error authorization status."""
        erros = json_data.get("erros", [])
        error_msg = erros[0]["mensagem"] if erros else _("Authorization error")
        record.write(
            {
                "edoc_error_message": error_msg,
            }
        )
        record._change_state(SITUACAO_EDOC_REJEITADA)

    def _process_status_nacional(self, record):
        """Process status check for NFSe Nacional."""
        ref = str(record.rps_number)
        response = record.env[
            "focusnfe.nfse.nacional"
        ].query_focus_nfse_nacional_by_ref(
            ref, record.company_id, record.nfse_environment
        )

        json = response.json()

        edoc_states = ["a_enviar", "enviada", "rejeitada"]
        if record.company_id.focusnfe_nfse_update_authorized_document_status:
            edoc_states.append("autorizada")

        if response.status_code == 200:
            if record.state in edoc_states:
                if (
                    json["status"] == STATUS_AUTORIZADO
                    and record.state_edoc != SITUACAO_EDOC_AUTORIZADA
                ):
                    self._process_authorized_status_nacional(record, json)
                elif json["status"] == STATUS_ERRO_AUTORIZACAO:
                    self._process_error_status(record, json)
                elif json["status"] == STATUS_CANCELADO:
                    if record.state_edoc != SITUACAO_EDOC_CANCELADA:
                        record._document_cancel(record.cancel_reason)

            return _(json["status"])

        return "Unable to retrieve the document status."

    def _process_status_municipal(self, record):
        """Process status check for NFSe Municipal."""
        ref = "rps" + record.rps_number
        response = record.env["focusnfe.nfse"].query_focus_nfse_by_rps(
            ref, 0, record.company_id, record.nfse_environment
        )

        json = response.json()

        edoc_states = ["a_enviar", "enviada", "rejeitada"]
        if record.company_id.focusnfe_nfse_update_authorized_document_status:
            edoc_states.append("autorizada")

        if response.status_code == 200:
            if record.state in edoc_states:
                if (
                    json["status"] == STATUS_AUTORIZADO
                    and record.state_edoc != SITUACAO_EDOC_AUTORIZADA
                ):
                    self._process_authorized_status_municipal(record, json)
                elif json["status"] == STATUS_ERRO_AUTORIZACAO:
                    record.write(
                        {
                            "edoc_error_message": json["erros"][0]["mensagem"],
                        }
                    )
                    record._change_state(SITUACAO_EDOC_REJEITADA)
                elif json["status"] == STATUS_CANCELADO:
                    if record.state_edoc != SITUACAO_EDOC_CANCELADA:
                        record._document_cancel(record.cancel_reason)

            return _(json["status"])

        return "Unable to retrieve the document status."

    def _document_status(self):
        """Check and update the status of the NFSe document.

        Parameters:
            None.

        Returns:
            A string indicating the current status of the document.
        """
        result = super()._document_status()
        # Handle NFSe Nacional
        for record in self.filtered(filter_processador_edoc_nfse).filtered(
            filter_focusnfe_nacional
        ):
            result = self._process_status_nacional(record)
        # Handle NFSe Municipal (original)
        for record in self.filtered(filter_processador_edoc_nfse).filtered(
            filter_focusnfe_municipal
        ):
            result = self._process_status_municipal(record)

        return result

    def create_cancel_event(self, status_json, record):
        """Create a cancel event and process it.

        Parameters:
            record: The NFSe record that is being canceled.

        Returns:
            The created event.
        """
        xml_path = status_json.get("caminho_xml_cancelamento", "")
        xml = ""
        if xml_path:
            xml = requests.get(
                NFSE_URL[record.nfse_environment] + xml_path,
                timeout=TIMEOUT,
            ).content.decode("utf-8")

        event = record.event_ids.create_event_save_xml(
            company_id=record.company_id,
            environment=(
                EVENT_ENV_PROD if record.nfse_environment == "1" else EVENT_ENV_HML
            ),
            event_type="2",
            xml_file="",
            document_id=record,
        )
        event.set_done(
            status_code=4,
            response=_("Successfully Processed"),
            protocol_date=fields.Datetime.to_string(fields.Datetime.now()),
            protocol_number="",
            file_response_xml=xml,
        )
        return event

    def fetch_and_verify_pdf_content(self, status_json, record):
        """Fetch and verify the PDF content from the provided URL.

        Parameters:
            status_json: JSON response containing the URLs for the PDF.
            record: The NFSe record for which the PDF is being retrieved.

        Returns:
            None. Updates the record with the PDF content if valid.
        """
        pdf_content = requests.get(
            status_json["url"],
            timeout=TIMEOUT,
            verify=record.company_id.nfse_ssl_verify,
        ).content
        if not _is_valid_pdf(pdf_content):
            pdf_content = requests.get(
                status_json["url_danfse"],
                timeout=TIMEOUT,
                verify=record.company_id.nfse_ssl_verify,
            ).content
        if _is_valid_pdf(pdf_content):
            record.make_focus_nfse_pdf(pdf_content)

    def _handle_cancelled_status(self, record, status_json, use_url_first=False):
        """Handle already cancelled status.

        Args:
            record: The document record.
            status_json (dict): Status JSON response.
            use_url_first (bool): Whether to try 'url' first for PDF.
        """
        record.cancel_event_id = record.create_cancel_event(status_json, record)
        if record.company_id.focusnfe_nfse_force_odoo_danfse:
            record.make_pdf()
        else:
            if use_url_first:
                record.fetch_and_verify_pdf_content(status_json, record)
            else:
                url_danfse = status_json.get("url_danfse", "")
                if url_danfse:
                    pdf_content = requests.get(
                        url_danfse,
                        timeout=TIMEOUT,
                        verify=record.company_id.nfse_ssl_verify,
                    ).content
                    if _is_valid_pdf(pdf_content):
                        record.make_focus_nfse_pdf(pdf_content)

    def _process_cancel_base(
        self,
        record,
        ref,
        query_method,
        cancel_method,
        use_url_first=False,
        apply_barueri_hack=False,
    ):
        """Base method to process cancellation.

        Args:
            record: The document record.
            ref (str): Document reference.
            query_method: Method to query document status.
            cancel_method: Method to cancel document.
            use_url_first (bool): Whether to try 'url' first for PDF.
            apply_barueri_hack (bool): Whether to apply Barueri-specific hack.

        Returns:
            requests.Response: The cancellation response.
        """
        # Check current status
        status_response = query_method(ref, record.company_id, record.nfse_environment)
        status_json = status_response.json()

        if status_response.status_code == 200:
            status = (
                status_json.get("status", "")
                if isinstance(status_json, dict)
                else status_json.get("status", "")
            )
            if (
                status == STATUS_CANCELADO
                and record.state_edoc != SITUACAO_EDOC_CANCELADA
            ):
                self._handle_cancelled_status(record, status_json, use_url_first)
                return status_response

        # Perform cancellation
        response = cancel_method(
            ref, record.cancel_reason, record.company_id, record.nfse_environment
        )
        json_data = response.json()

        if response.status_code in [200, 400]:
            code = json_data.get("codigo", "")
            status = json_data.get("status", "")

            # Barueri hack - temporary
            if (
                apply_barueri_hack
                and not code
                and record.company_id.city_id.ibge_code == "3505708"
            ):
                code = json_data.get("erros", [{}])[0].get("codigo", "")
                if code == "OK200":
                    code = CODE_NFE_CANCELADA

            if code == CODE_NFE_CANCELADA or status == STATUS_CANCELADO:
                # Query status again after cancellation
                status_rps = query_method(
                    ref, record.company_id, record.nfse_environment
                )
                status_json = status_rps.json()
                self._handle_cancelled_status(record, status_json, use_url_first)
                return response

            raise UserError(
                _(
                    "%(code)s - %(status)s",
                    code=response.status_code,
                    status=status,
                )
            )

        raise UserError(
            _(
                "%(code)s - %(msg)s",
                code=response.status_code,
                msg=json_data.get("mensagem", ""),
            )
        )

    def _process_cancel_nacional(self, record):
        """Process cancellation for NFSe Nacional."""
        ref = str(record.rps_number)
        nfse_nacional = record.env["focusnfe.nfse.nacional"]

        def query_method(ref, company, environment):
            return nfse_nacional.query_focus_nfse_nacional_by_ref(
                ref, company, environment
            )

        def cancel_method(ref, cancel_reason, company, environment):
            return nfse_nacional.cancel_focus_nfse_nacional_document(
                ref, cancel_reason, company, environment
            )

        return self._process_cancel_base(
            record, ref, query_method, cancel_method, use_url_first=False
        )

    def _process_cancel_municipal(self, record):
        """Process cancellation for NFSe Municipal."""
        ref = "rps" + record.rps_number
        nfse = record.env["focusnfe.nfse"]

        def query_method(ref, company, environment):
            return nfse.query_focus_nfse_by_rps(ref, 0, company, environment)

        def cancel_method(ref, cancel_reason, company, environment):
            return nfse.cancel_focus_nfse_document(
                ref, cancel_reason, company, environment
            )

        return self._process_cancel_base(
            record,
            ref,
            query_method,
            cancel_method,
            use_url_first=True,
            apply_barueri_hack=True,
        )

    def cancel_document_focus(self):
        """Cancel a NFSe document with the Focus NFSe provider.

        Parameters:
            None.

        Returns:
            The response regarding the cancellation request.
        """
        # Handle NFSe Nacional
        for record in self.filtered(filter_processador_edoc_nfse).filtered(
            filter_focusnfe_nacional
        ):
            return self._process_cancel_nacional(record)
        # Handle NFSe Municipal (original)
        for record in self.filtered(filter_processador_edoc_nfse).filtered(
            filter_focusnfe_municipal
        ):
            return self._process_cancel_municipal(record)

    def _process_send_nacional(self, record):
        """Process document send for NFSe Nacional."""
        for edoc in record.serialize():
            ref = str(record.rps_number)
            response = self.env[
                "focusnfe.nfse.nacional"
            ].process_focus_nfse_nacional_document(
                edoc, ref, record.company_id, record.nfse_environment
            )
            json = response.json()

            if response.status_code == 202:
                if json["status"] == STATUS_PROCESSANDO_AUTORIZACAO:
                    if record.state == "rejeitada":
                        record.state_edoc = SITUACAO_EDOC_ENVIADA
                    else:
                        record._change_state(SITUACAO_EDOC_ENVIADA)
            elif response.status_code == 422:
                code = json.get("codigo", "")
                if code == CODE_NFE_AUTORIZADA and record.state in [
                    "a_enviar",
                    "enviada",
                    "rejeitada",
                ]:
                    record._document_status()
                else:
                    record._change_state(SITUACAO_EDOC_REJEITADA)
            else:
                record._change_state(SITUACAO_EDOC_REJEITADA)

    def _process_send_municipal(self, record):
        """Process document send for NFSe Municipal."""
        for edoc in record.serialize():
            ref = "rps" + record.rps_number
            response = self.env["focusnfe.nfse"].process_focus_nfse_document(
                edoc, ref, record.company_id, record.nfse_environment
            )
            json = response.json()

            if response.status_code == 202:
                if json["status"] == STATUS_PROCESSANDO_AUTORIZACAO:
                    if record.state == "rejeitada":
                        record.state_edoc = SITUACAO_EDOC_ENVIADA
                    else:
                        record._change_state(SITUACAO_EDOC_ENVIADA)
            elif response.status_code == 422:
                code = json.get("codigo", "")
                if code == CODE_NFE_AUTORIZADA and record.state in [
                    "a_enviar",
                    "enviada",
                    "rejeitada",
                ]:
                    record._document_status()
                else:
                    record._change_state(SITUACAO_EDOC_REJEITADA)
            else:
                record._change_state(SITUACAO_EDOC_REJEITADA)

    def _eletronic_document_send(self):
        """Send the electronic document to the NFSe provider.

        Parameters:
            None.

        Returns:
            None. Updates the document's status based on the response.
        """
        res = super()._eletronic_document_send()
        # Handle NFSe Nacional
        for record in self.filtered(filter_processador_edoc_nfse).filtered(
            filter_focusnfe_nacional
        ):
            self._process_send_nacional(record)
        # Handle NFSe Municipal (original)
        for record in self.filtered(filter_processador_edoc_nfse).filtered(
            filter_focusnfe_municipal
        ):
            self._process_send_municipal(record)
        return res

    def _exec_before_SITUACAO_EDOC_CANCELADA(self, old_state, new_state):
        """Hook method before changing document's state to 'Cancelled'.

        Parameters:
            - old_state: The document's previous state.
            - new_state: The new state.

        Returns:
            The result of the cancellation process.
        """
        super()._exec_before_SITUACAO_EDOC_CANCELADA(old_state, new_state)
        return self.cancel_document_focus()

    @api.model
    def _cron_document_status_focus(self):
        """Scheduled method to check the status of sent NFSe documents.

        Parameters:
            None.

        Returns:
            None. Updates the status of each document based on the NFSe provider's
            response.
        """
        records = (
            self.search([("state", "in", ["enviada"])], limit=25)
            .filtered(filter_processador_edoc_nfse)
            .filtered(filter_focusnfe)
        )
        # Iterate over each record individually, as _document_status()
        # may expect a singleton in some cases
        for record in records:
            record._document_status()
