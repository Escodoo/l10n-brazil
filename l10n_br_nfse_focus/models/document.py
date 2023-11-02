# Copyright 2023 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import json
from datetime import datetime

import pytz
import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_br_fiscal.constants.fiscal import (
    EVENT_ENV_HML,
    EVENT_ENV_PROD,
    SITUACAO_EDOC_AUTORIZADA,
    SITUACAO_EDOC_ENVIADA,
    SITUACAO_EDOC_REJEITADA,
)
from odoo.addons.l10n_br_fiscal.models.document import Document as FiscalDocument
from odoo.addons.l10n_br_nfse.models.document import filter_processador_edoc_nfse

NFSE_URL = {
    "1": "https://api.focusnfe.com.br",
    "2": "https://homologacao.focusnfe.com.br",
}

API_ENDPOINT = {
    "envio": "/v2/nfse?ref=",
    "status": "/v2/nfse/",
    "resposta": "/v2/nfse/",
    "cancelamento": "/v2/nfse/",
}


class NFSeFocus(object):
    def __init__(self, tpAmb, token_focusnfe, company):
        self.tpAmb = tpAmb
        self.token_focusnfe = token_focusnfe
        self.company = company

    def processar_documento(self, edoc):
        nfse = {}
        nfse["prestador"] = {}
        nfse["servico"] = {}
        nfse["tomador"] = {}
        nfse["tomador"]["endereco"] = {}

        nfse["razao_social"] = self.company.name
        nfse["data_emissao"] = edoc[0]["rps"]["data_emissao"]
        nfse["incentivador_cultural"] = edoc[0]["rps"]["incentivador_cultural"]
        nfse["natureza_operacao"] = edoc[0]["rps"]["natureza_operacao"]
        nfse["optante_simples_nacional"] = edoc[0]["rps"]["optante_simples_nacional"]
        nfse["status"] = edoc[0]["rps"]["status"]

        # Prestador
        nfse["prestador"]["cnpj"] = edoc[0]["rps"]["cnpj"]
        nfse["prestador"]["inscricao_municipal"] = edoc[0]["rps"]["inscricao_municipal"]
        nfse["prestador"]["codigo_municipio"] = self.company.city_id.ibge_code

        # Serviço
        nfse["servico"]["aliquota"] = edoc[1]["service"]["aliquota"]
        nfse["servico"]["base_calculo"] = edoc[1]["service"]["base_calculo"]
        nfse["servico"]["discriminacao"] = edoc[1]["service"]["discriminacao"]
        nfse["servico"]["iss_retido"] = edoc[1]["service"]["iss_retido"]
        nfse["servico"]["item_lista_servico"] = edoc[1]["service"]["item_lista_servico"]
        nfse["servico"]["valor_iss"] = edoc[1]["service"]["valor_iss"]
        nfse["servico"]["valor_iss_retido"] = edoc[1]["service"]["valor_iss_retido"]
        nfse["servico"]["valor_pis"] = (
            edoc[1]["service"]["valor_pis"] or edoc[1]["service"]["valor_pis_retido"]
        )
        nfse["servico"]["valor_cofins"] = (
            edoc[1]["service"]["valor_cofins"]
            or edoc[1]["service"]["valor_cofins_retido"]
        )
        nfse["servico"]["valor_inss"] = (
            edoc[1]["service"]["valor_inss"] or edoc[1]["service"]["valor_inss_retido"]
        )
        nfse["servico"]["valor_ir"] = (
            edoc[1]["service"]["valor_ir"] or edoc[1]["service"]["valor_ir_retido"]
        )
        nfse["servico"]["valor_csll"] = (
            edoc[1]["service"]["valor_csll"] or edoc[1]["service"]["valor_csll_retido"]
        )
        nfse["servico"]["valor_deducoes"] = edoc[1]["service"]["valor_deducoes"]
        nfse["servico"]["fonte_total_tributos"] = "IBPT"
        nfse["servico"]["desconto_incondicionado"] = edoc[1]["service"][
            "valor_desconto_incondicionado"
        ]
        nfse["servico"]["desconto_condicionado"] = 0
        nfse["servico"]["outras_retencoes"] = edoc[1]["service"]["outras_retencoes"]

        nfse["servico"]["valor_liquido"] = edoc[1]["service"]["valor_servicos"]
        nfse["servico"]["valor_servicos"] = edoc[1]["service"]["valor_servicos"]
        nfse["servico"]["codigo_tributario_municipio"] = edoc[1]["service"][
            "codigo_tributacao_municipio"
        ]

        # Tomador
        nfse["tomador"]["cnpj"] = (
            edoc[2]["tomador"]["cnpj"] or edoc[2]["tomador"]["cpf"]
        )
        nfse["tomador"]["razao_social"] = edoc[2]["tomador"]["razao_social"]
        nfse["tomador"]["endereco"]["bairro"] = edoc[2]["tomador"]["bairro"]
        nfse["tomador"]["endereco"]["cep"] = edoc[2]["tomador"]["cep"]
        nfse["tomador"]["endereco"]["codigo_municipio"] = edoc[2]["tomador"][
            "codigo_municipio"
        ]
        nfse["tomador"]["endereco"]["logradouro"] = edoc[2]["tomador"]["endereco"]
        nfse["tomador"]["endereco"]["numero"] = edoc[2]["tomador"]["numero"]
        nfse["tomador"]["endereco"]["uf"] = edoc[2]["tomador"]["uf"]

        payload = json.dumps(nfse)
        ref = {"ref": edoc[0]["rps"]["id"]}
        return self._post(NFSE_URL[self.tpAmb] + API_ENDPOINT["envio"], payload, ref)

    def _post(self, url, payload, ref):
        response = requests.post(
            url, params=ref, data=payload, auth=(self.token_focusnfe, "")
        )
        if response.status_code in {200, 201, 202, 422}:
            return response
        else:
            raise UserError(_("%s - %s" % (response.status_code, response.text)))

    def consulta_nfse_rps(self, ref, completa):
        return self._get(NFSE_URL[self.tpAmb] + API_ENDPOINT["status"] + ref, completa)

    def _get(self, url, completa):
        response = requests.get(url, params=completa, auth=(self.token_focusnfe, ""))
        return response

    def cancela_documento(self, ref, cancel_reason):
        data = {}
        data["justificativa"] = cancel_reason
        response = requests.delete(
            NFSE_URL[self.tpAmb] + API_ENDPOINT["cancelamento"] + ref,
            data=json.dumps(data),
            auth=(self.token_focusnfe, ""),
        )
        return response


def filter_focusnfe(record):
    return record.company_id.provedor_nfse == "focusnfe"


class Document(models.Model):
    _inherit = "l10n_br_fiscal.document"

    def make_pdf_focus(self, content):
        if not self.filtered(filter_processador_edoc_nfse):
            return super().make_pdf()

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
        edocs = super()._serialize(edocs)
        for record in self.filtered(filter_processador_edoc_nfse).filtered(
            filter_focusnfe
        ):
            edocs.append(record.serialize_nfse_focus())
        return edocs

    def serialize_nfse_focus(self):
        dados_lote_rps = self._prepare_lote_rps()
        dados_servico = self._prepare_dados_servico()
        dados_tomador = self._prepare_dados_tomador()
        nfse = []
        nfse.append({"rps": dados_lote_rps})
        nfse.append({"service": dados_servico})
        nfse.append({"tomador": dados_tomador})
        return nfse

    def _processador_nfse_focus(self):
        return NFSeFocus(
            tpAmb=self.nfse_environment,
            token_focusnfe=self.company_id.token_focusnfe,
            company=self.company_id,
        )

    def _document_export(self, pretty_print=True):
        result = super(FiscalDocument, self)._document_export()
        for record in self.filtered(filter_focusnfe):
            if record.company_id.provedor_nfse:
                event_id = self.event_ids.create_event_save_xml(
                    company_id=self.company_id,
                    environment=(
                        EVENT_ENV_PROD
                        if self.nfse_environment == "1"
                        else EVENT_ENV_HML
                    ),
                    event_type="0",
                    xml_file="",
                    document_id=self,
                )
                record.authorization_event_id = event_id

        return result

    def cancel_document_focus(self):
        for record in self.filtered(filter_processador_edoc_nfse).filtered(
            filter_focusnfe
        ):
            processador = record._processador_nfse_focus()
            ref = "rps" + record.rps_number
            response = processador.cancela_documento(ref, record.cancel_reason)

            json = response.json()

            if response.status_code in [200, 400]:
                try:
                    code = json["codigo"]
                    response = True
                except Exception:
                    code = ""
                try:
                    status = json["status"]
                except Exception:
                    status = ""
                if code == "nfe_cancelada" or status == "cancelado":
                    record.cancel_event_id = record.event_ids.create_event_save_xml(
                        company_id=record.company_id,
                        environment=(
                            EVENT_ENV_PROD
                            if self.nfse_environment == "1"
                            else EVENT_ENV_HML
                        ),
                        event_type="2",
                        xml_file="",
                        document_id=record,
                    )

                    record.cancel_event_id.set_done(
                        status_code=4,
                        response=_("Processado com Sucesso"),
                        protocol_date=fields.Datetime.to_string(fields.Datetime.now()),
                        protocol_number="",
                        file_response_xml="",
                    )

                    return response

                else:
                    raise UserError(_("%s - %s" % (response.status_code, status)))
            else:
                raise UserError(_("%s - %s" % (response.status_code, status)))

    def _document_status(self):
        for record in self.filtered(filter_processador_edoc_nfse).filtered(
            filter_focusnfe
        ):
            processador = record._processador_nfse_focus()
            ref = "rps" + record.rps_number
            completa = 0
            response = processador.consulta_nfse_rps(ref, completa)

            json = response.json()

            if json["status"] == "autorizado":

                aware_datetime = datetime.strptime(
                    json["data_emissao"], "%Y-%m-%dT%H:%M:%S%z"
                )
                utc_datetime = aware_datetime.astimezone(pytz.utc)
                naive_datetime = utc_datetime.replace(tzinfo=None)
                record.write(
                    {
                        "verify_code": json["codigo_verificacao"],
                        "document_number": json["numero"],
                        "authorization_date": naive_datetime,
                    }
                )

                xml = requests.get(
                    NFSE_URL[processador.tpAmb] + json["caminho_xml_nota_fiscal"]
                ).content.decode("utf-8")
                pdf_content = requests.get(json["url_danfse"]).content

                record.make_pdf_focus(pdf_content)

                record.authorization_event_id.set_done(
                    status_code=4,
                    response=_("Processado com Sucesso"),
                    protocol_date=record.authorization_date,
                    protocol_number=record.authorization_protocol,
                    file_response_xml=xml,
                )
                record._change_state(SITUACAO_EDOC_AUTORIZADA)

            return _(json["status"])

    def _eletronic_document_send(self):
        super()._eletronic_document_send()
        for record in self.filtered(filter_processador_edoc_nfse).filtered(
            filter_focusnfe
        ):
            processador = record._processador_nfse_focus()
            for edoc in record.serialize():
                response = processador.processar_documento(edoc)
                json = response.json()

                if response.status_code == 202:
                    if json["status"] == "processando_autorizacao":
                        record._change_state(SITUACAO_EDOC_ENVIADA)
                elif response.status_code == 422:
                    try:
                        code = json["codigo"]
                    except Exception:
                        code = ""

                    if code == "nfe_autorizada" and self.state in [
                        "a_enviar",
                        "enviado",
                        "rejeitada",
                    ]:
                        record._document_status()
                    else:
                        record._change_state(SITUACAO_EDOC_REJEITADA)
                else:
                    record._change_state(SITUACAO_EDOC_REJEITADA)

    def _exec_before_SITUACAO_EDOC_CANCELADA(self, old_state, new_state):
        super()._exec_before_SITUACAO_EDOC_CANCELADA(old_state, new_state)
        return self.cancel_document_focus()
