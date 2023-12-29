# Copyright 2023 - TODAY, KMEE INFORMATICA LTDA
# Copyright 2023 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import json
from datetime import datetime

import pytz
import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_br_fiscal.constants.fiscal import (
    EVENT_ENV_HML,
    EVENT_ENV_PROD,
    MODELO_FISCAL_NFSE,
    PROCESSADOR_OCA,
    SITUACAO_EDOC_AUTORIZADA,
    SITUACAO_EDOC_CANCELADA,
    SITUACAO_EDOC_ENVIADA,
    SITUACAO_EDOC_REJEITADA,
)
from odoo.addons.l10n_br_fiscal.models.document import Document as FiscalDocument

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


def filter_oca_nfse(record):
    if record.processador_edoc == PROCESSADOR_OCA and record.document_type_id.code in [
        MODELO_FISCAL_NFSE,
    ]:
        return True
    return False


def filter_focusnfe(record):
    return record.company_id.provedor_nfse == "focusnfe"


class NFSeFocus(object):
    def __init__(self, tpAmb, token, company):
        self.tpAmb = tpAmb
        self.company = company
        self.token = company.get_focusnfe_token()

    def processar_documento(self, edoc):
        rps = edoc[0]["rps"]
        service = edoc[1]["service"]
        tomador = edoc[2]["tomador"]

        nfse = {
            "prestador": {
                "cnpj": rps.get("cnpj"),
                "inscricao_municipal": rps.get("inscricao_municipal"),
                "codigo_municipio": self.company.city_id.ibge_code,
            },
            "servico": {
                "aliquota": service.get("aliquota"),
                "base_calculo": round(service.get("base_calculo", 0), 2),
                "discriminacao": service.get("discriminacao"),
                "iss_retido": service.get("iss_retido"),
                "codigo_municipio": service.get("municipio_prestacao_servico"),
                "item_lista_servico": service.get(
                    self.company.focusnfe_service_type_value
                ),
                "codigo_cnae": service.get(self.company.focusnfe_cnae_code_value),
                "valor_iss": round(service.get("valor_iss", 0), 2),
                "valor_iss_retido": round(service.get("valor_iss_retido", 0), 2),
                "valor_pis": round(service.get("valor_pis_retido", 0), 2),
                "valor_cofins": round(service.get("valor_cofins_retido", 0), 2),
                "valor_inss": round(service.get("valor_inss_retido", 0), 2),
                "valor_ir": round(service.get("valor_ir_retido", 0), 2),
                "valor_csll": round(service.get("valor_csll_retido", 0), 2),
                "valor_deducoes": round(service.get("valor_deducoes", 0), 2),
                "fonte_total_tributos": "IBPT",
                "desconto_incondicionado": round(
                    service.get("valor_desconto_incondicionado", 0), 2
                ),
                "desconto_condicionado": 0,
                "outras_retencoes": round(service.get("outras_retencoes", 0), 2),
                "valor_servicos": round(service.get("valor_servicos", 0), 2),
                "valor_liquido": round(service.get("valor_liquido_nfse", 0), 2),
                "codigo_tributario_municipio": service.get(
                    "codigo_tributacao_municipio"
                ),
            },
            "tomador": {
                "cnpj": tomador.get("cnpj") or tomador.get("cpf"),
                "razao_social": tomador.get("razao_social"),
                "email": tomador.get("email"),
                "endereco": {
                    "bairro": tomador.get("bairro"),
                    "cep": tomador.get("cep"),
                    "codigo_municipio": str(tomador.get("codigo_municipio")),
                    "logradouro": tomador.get("endereco"),
                    "numero": tomador.get("numero"),
                    "uf": tomador.get("uf"),
                },
            },
            "razao_social": self.company.name,
            "data_emissao": rps.get("data_emissao"),
            "incentivador_cultural": rps.get("incentivador_cultural"),
            "natureza_operacao": rps.get("natureza_operacao"),
            "optante_simples_nacional": rps.get("optante_simples_nacional"),
            "status": rps.get("status"),
            "codigo_obra": rps.get("codigo_obra"),
            "art": rps.get("art"),
        }

        payload = json.dumps(nfse)
        ref = {"ref": rps.get("id")}
        return self._post(NFSE_URL[self.tpAmb] + API_ENDPOINT["envio"], payload, ref)

    def _post(self, url, payload, ref):
        response = requests.post(url, params=ref, data=payload, auth=(self.token, ""))
        if response.status_code in {200, 201, 202, 422}:
            return response
        else:
            raise UserError(_("%s - %s" % (response.status_code, response.text)))

    def consulta_nfse_rps(self, ref, completa):
        return self._get(NFSE_URL[self.tpAmb] + API_ENDPOINT["status"] + ref, completa)

    def _get(self, url, completa):
        response = requests.get(url, params=completa, auth=(self.token, ""))
        return response

    def cancela_documento(self, ref, cancel_reason):
        data = {"justificativa": cancel_reason}
        response = requests.delete(
            NFSE_URL[self.tpAmb] + API_ENDPOINT["cancelamento"] + ref,
            data=json.dumps(data),
            auth=(self.token, ""),
        )
        return response


class Document(models.Model):
    _inherit = "l10n_br_fiscal.document"

    def make_pdf_focus(self, content):
        if not self.filtered(filter_oca_nfse).filtered(filter_focusnfe):
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
        for record in self.filtered(filter_oca_nfse).filtered(filter_focusnfe):
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
            token=self.company_id.get_focusnfe_token(),
            company=self.company_id,
        )

    def _document_export(self, pretty_print=True):
        if self.filtered(filter_oca_nfse).filtered(filter_focusnfe):
            result = super(FiscalDocument, self)._document_export()
        else:
            result = super()._document_export()
        for record in self.filtered(filter_oca_nfse).filtered(filter_focusnfe):
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

    def _document_status(self):
        result = super(FiscalDocument, self)._document_status()
        for record in self.filtered(filter_oca_nfse).filtered(filter_focusnfe):
            processador = record._processador_nfse_focus()
            ref = "rps" + record.rps_number
            completa = 0
            response = processador.consulta_nfse_rps(ref, completa)

            json = response.json()

            if response.status_code == 200:
                if record.state in ["a_enviar", "enviada", "rejeitada"]:
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
                            NFSE_URL[processador.tpAmb]
                            + json["caminho_xml_nota_fiscal"]
                        ).content.decode("utf-8")
                        pdf_content = (
                            requests.get(json["url"]).content
                            or requests.get(json["url_danfse"]).content
                        )

                        record.make_pdf_focus(pdf_content)

                        if not record.authorization_event_id:
                            record._document_export()

                        if record.authorization_event_id:
                            record.authorization_event_id.set_done(
                                status_code=4,
                                response=_("Processado com Sucesso"),
                                protocol_date=record.authorization_date,
                                protocol_number=record.authorization_protocol,
                                file_response_xml=xml,
                            )
                            record._change_state(SITUACAO_EDOC_AUTORIZADA)

                    elif json["status"] == "erro_autorizacao":
                        record.write(
                            {
                                "edoc_error_message": json["erros"][0]["mensagem"],
                            }
                        )
                        record._change_state(SITUACAO_EDOC_REJEITADA)
                    elif json["status"] == "cancelado":
                        record._change_state(SITUACAO_EDOC_CANCELADA)

                result = _(json["status"])
            else:
                result = "Unable to retrieve the document status."
        return result

    def cancel_document_focus(self):
        for record in self.filtered(filter_oca_nfse).filtered(filter_focusnfe):
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

                    status_rps = processador.consulta_nfse_rps(ref, 0)
                    status_json = status_rps.json()
                    pdf_content = (
                        requests.get(status_json["url"]).content
                        or requests.get(status_json["url_danfse"]).content
                    )
                    record.make_pdf_focus(pdf_content)

                    return response

                else:
                    raise UserError(_("%s - %s" % (response.status_code, status)))
            else:
                raise UserError(_("%s - %s" % (response.status_code, status)))

    def _eletronic_document_send(self):
        super()._eletronic_document_send()
        for record in self.filtered(filter_oca_nfse).filtered(filter_focusnfe):
            processador = record._processador_nfse_focus()
            for edoc in record.serialize():
                response = processador.processar_documento(edoc)
                json = response.json()

                if response.status_code == 202:
                    if json["status"] == "processando_autorizacao":
                        if record.state == "rejeitada":
                            record.state_edoc = SITUACAO_EDOC_ENVIADA
                        else:
                            record._change_state(SITUACAO_EDOC_ENVIADA)
                elif response.status_code == 422:
                    try:
                        code = json["codigo"]
                    except Exception:
                        code = ""

                    if code == "nfe_autorizada" and self.state in [
                        "a_enviar",
                        "enviada",
                        "rejeitada",
                    ]:
                        record._document_status()
                    else:
                        record._change_state(SITUACAO_EDOC_REJEITADA)
                else:
                    record._change_state(SITUACAO_EDOC_REJEITADA)

    @api.model
    def _cron_document_status_focus(self):
        records = (
            self.search([("state", "in", ["enviada"])])
            .filtered(filter_oca_nfse)
            .filtered(filter_focusnfe)
        )
        if records:
            records._document_status()

    def _exec_before_SITUACAO_EDOC_CANCELADA(self, old_state, new_state):
        super()._exec_before_SITUACAO_EDOC_CANCELADA(old_state, new_state)
        return self.cancel_document_focus()
