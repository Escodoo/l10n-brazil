# Copyright 2023 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# Copyright 2023 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import os
from datetime import datetime
from unittest.mock import MagicMock, patch

from requests import HTTPError

from odoo.exceptions import UserError
from odoo.tests import common

from odoo.addons.l10n_br_fiscal.constants.fiscal import (
    MODELO_FISCAL_NFE,
    MODELO_FISCAL_NFSE,
    PROCESSADOR_OCA,
    SITUACAO_EDOC_A_ENVIAR,
    SITUACAO_EDOC_EM_DIGITACAO,
    SITUACAO_EDOC_ENVIADA,
    SITUACAO_EDOC_REJEITADA,
)

from ... import l10n_br_nfse_focus
from ..models.document import (
    API_ENDPOINT,
    NFSE_URL,
    Document,
    filter_focusnfe,
    filter_oca_nfse,
)

MOCK_PATH = "odoo.addons.l10n_br_nfse_focus"

PAYLOAD = []
PAYLOAD.append(
    {
        "rps": {
            "cnpj": "12345678901234",
            "inscricao_municipal": "12345",
            "id": "rps132",
            "numero": "132",
            "serie": "2",
            "tipo": "1",
            "data_emissao": "2024-02-20T17:01:47",
            "date_in_out": "2024-02-20T17:01:57",
            "natureza_operacao": "1",
            "regime_especial_tributacao": "1",
            "optante_simples_nacional": "1",
            "incentivador_cultural": "2",
            "status": "1",
            "rps_substitiuido": False,
            "intermediario_servico": False,
            "codigo_obra": "",
            "art": "",
            "carga_tributaria": 0.0,
            "total_recebido": 100.0,
            "carga_tributaria_estimada": 0.0,
        }
    },
)
PAYLOAD.append(
    {
        "service": {
            "valor_servicos": 100.0,
            "valor_deducoes": 0.0,
            "valor_pis": 0.65,
            "valor_pis_retido": 0.65,
            "valor_cofins": 3.0,
            "valor_cofins_retido": 3.0,
            "valor_inss": 0.0,
            "valor_inss_retido": 0.0,
            "valor_ir": 1.5,
            "valor_ir_retido": 1.5,
            "valor_csll": 1.0,
            "valor_csll_retido": 1.0,
            "iss_retido": "1",
            "valor_iss": 0.0,
            "valor_iss_retido": 4.0,
            "outras_retencoes": 0.0,
            "base_calculo": 100.0,
            "aliquota": 0.04,
            "valor_liquido_nfse": 89.85,
            "item_lista_servico": "1712",
            "codigo_tributacao_municipio": "171202211",
            "municipio_prestacao_servico": "",
            "discriminacao": "[ODOO_DEV] Customized Odoo Development",
            "codigo_cnae": False,
            "valor_desconto_incondicionado": 0.0,
            "codigo_municipio": "3505708",
        }
    }
)
PAYLOAD.append(
    {
        "recipient": {
            "cnpj": "07504505000132",
            "cpf": False,
            "email": "contato@focusnfe.com.br",
            "inscricao_municipal": False,
            "inscricao_estadual": False,
            "razao_social": "Acras Tecnologia da Informação LTDA",
            "endereco": "Rua Dias da Rocha Filho",
            "numero": "999",
            "bairro": "Alto da XV",
            "codigo_municipio": "4106902",
            "descricao_municipio": "São José dos Pinhais",
            "uf": "PR",
            "municipio": "Curitiba",
            "cep": "83050580",
            "complemento": "Prédio 04 - Sala 34C",
        }
    }
)

PAYLOAD_REF = "rps132"


class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data

    @property
    def text(self):
        return str(self._json_data)

    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            raise HTTPError(f"{self.status_code} HTTP error")


class TestL10nBrNfseFocus(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.tpAmb = "2"
        self.token = "123456789"
        self.company = self.env.ref("base.main_company")
        self.company.focusnfe_homologation_token = self.token
        self.company.provedor_nfse = "focusnfe"
        self.nfse_demo = self.env.ref("l10n_br_fiscal.demo_nfse_same_state")
        self.nfse_demo.document_number = "0001"
        self.nfse_demo.rps_number = "0002"
        self.nfse_focus = self.env["focusnfe.nfse"]

    def test_filter_oca_nfse(self):
        record = self.nfse_demo
        record.processador_edoc = PROCESSADOR_OCA
        record.document_type_id.code = MODELO_FISCAL_NFSE

        result = filter_oca_nfse(record)

        self.assertEqual(record.processador_edoc, PROCESSADOR_OCA)
        self.assertIn(record.document_type_id.code, MODELO_FISCAL_NFSE)
        self.assertEqual(result, True)

        record.processador_edoc = None
        record.document_type_id.code = MODELO_FISCAL_NFE

        result = filter_oca_nfse(record)

        self.assertNotEqual(record.processador_edoc, PROCESSADOR_OCA)
        self.assertNotIn(record.document_type_id.code, MODELO_FISCAL_NFSE)
        self.assertEqual(result, False)

    def test_filter_focusnfe(self):
        record = self.nfse_demo
        filter_focusnfe(record)

        self.assertEqual(record.company_id.provedor_nfse, "focusnfe")

    @patch("odoo.addons.l10n_br_nfse_focus.models.document.requests.request")
    def test_processar_documento(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"status": "simulado"}

        result = self.nfse_focus.process_focus_nfse_document(
            PAYLOAD, PAYLOAD_REF, self.company, self.tpAmb
        )

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {"status": "simulado"})

    @patch("odoo.addons.l10n_br_nfse_focus.models.document.requests.request")
    def test_make_focus_nfse_http_request_generic(self, mock_request):
        # Configuração do mock para simular diferentes respostas HTTP
        mock_request.side_effect = (
            lambda method, url, data, params, auth: mock_response_based_on_method(
                method, data
            )
        )

        # Função auxiliar para simular respostas com base no método HTTP
        def mock_response_based_on_method(method, data):
            if method == "POST":
                return MockResponse(200, {"status": "success"})
            elif method == "GET":
                return MockResponse(
                    200, {"status": "success", "data": {"nfse_info": "…"}}
                )
            elif method == "DELETE":
                return MockResponse(204, {"status": "success"})
            else:
                return MockResponse(500, "Internal server error")

        # POST Method Tests
        URL = NFSE_URL[self.tpAmb] + API_ENDPOINT["envio"]
        result_post = self.nfse_focus._make_focus_nfse_http_request(
            "POST", URL, self.token, PAYLOAD, PAYLOAD_REF
        )
        self.assertEqual(result_post.status_code, 200)
        self.assertEqual(result_post.json(), {"status": "success"})

        # GET Method Tests
        URL = NFSE_URL[self.tpAmb] + API_ENDPOINT["status"]
        result_get = self.nfse_focus._make_focus_nfse_http_request(
            "GET", URL, self.token, PAYLOAD, PAYLOAD_REF
        )
        self.assertEqual(result_get.status_code, 200)
        self.assertEqual(
            result_get.json(), {"status": "success", "data": {"nfse_info": "…"}}
        )

        # DELETE Method Tests
        URL = NFSE_URL[self.tpAmb] + API_ENDPOINT["cancelamento"]
        result_delete = self.nfse_focus._make_focus_nfse_http_request(
            "DELETE", URL, self.token, PAYLOAD, PAYLOAD_REF
        )
        self.assertEqual(result_delete.status_code, 204)
        self.assertEqual(result_delete.json(), {"status": "success"})

    @patch("odoo.addons.l10n_br_nfse_focus.models.document.requests.request")
    def test_consulta_nfse_rps(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "status": "success",
            "data": {"nfse_info": "…"},
        }
        result = self.nfse_focus.query_focus_nfse_by_rps(
            PAYLOAD_REF, 0, self.company, self.tpAmb
        )

        self.assertEqual(result.status_code, 200)
        self.assertEqual(
            result.json(), {"status": "success", "data": {"nfse_info": "…"}}
        )

    @patch("odoo.addons.l10n_br_nfse_focus.models.document.requests.request")
    def test_cancela_documento(self, mock_delete):
        mock_delete.return_value.status_code = 204
        result = self.nfse_focus.cancel_focus_nfse_document(
            PAYLOAD_REF, "Teste de cancelamento", self.company, self.tpAmb
        )

        self.assertEqual(result.status_code, 204)

    def test_make_focus_nfse_pdf(self):
        record = self.nfse_demo
        record.processador_edoc = PROCESSADOR_OCA
        record.document_type_id.code = MODELO_FISCAL_NFSE

        pdf_path = os.path.join(
            l10n_br_nfse_focus.__path__[0], "tests", "nfse", "pdf_example.pdf"
        )

        with open(pdf_path, "rb") as file:
            content = file.read()

        record.make_focus_nfse_pdf(content)

        self.assertTrue(record.document_number)

        self.assertEqual(
            record.file_report_id.name, "NFS-e-" + record.document_number + ".pdf"
        )
        self.assertEqual(record.file_report_id.res_model, record._name)
        self.assertEqual(record.file_report_id.res_id, record.id)
        self.assertEqual(record.file_report_id.mimetype, "application/pdf")
        self.assertEqual(record.file_report_id.type, "binary")

        record.document_number = None
        record.make_focus_nfse_pdf(content)

        self.assertFalse(record.document_number)
        self.assertEqual(
            record.file_report_id.name, "RPS-" + record.rps_number + ".pdf"
        )

        # Not Filtered

        record.processador_edoc = ""
        record.document_type_id.code = MODELO_FISCAL_NFE

        pdf_path = os.path.join(
            l10n_br_nfse_focus.__path__[0], "tests", "nfse", "pdf_example.pdf"
        )

        with open(pdf_path, "rb") as file:
            content = file.read()

        with patch(
            "odoo.addons.l10n_br_nfse.models.document.Document.make_pdf"
        ) as mock_super_make_pdf:

            record.make_focus_nfse_pdf(content)

        mock_super_make_pdf.assert_called_once()

    def test_serialize(self):
        doc = self.nfse_demo
        edocs = []
        with patch.object(Document, "_serialize", return_value=edocs) as mock_serialize:
            result = doc._serialize(edocs)

        mock_serialize.assert_called_once_with(edocs)
        self.assertEqual(result, edocs)

    def test_document_export(self):
        record = self.nfse_demo
        record.processador_edoc = PROCESSADOR_OCA
        record.document_type_id.code = MODELO_FISCAL_NFE

        # Not Filtered

        record = self.nfse_demo
        record.company_id.provedor_nfse = None

        record._document_export()

        self.assertFalse(record.company_id.provedor_nfse)

        # Filtered

        record = self.nfse_demo
        record.company_id.provedor_nfse = "focusnfe"
        record.processador_edoc = PROCESSADOR_OCA
        record.document_type_id.code = MODELO_FISCAL_NFSE

        record._document_export()

        self.assertTrue(record.company_id.provedor_nfse)
        self.assertTrue(record.authorization_event_id)

    @patch(
        "odoo.addons.l10n_br_nfse_focus.models.document.FocusnfeNfse.query_focus_nfse_by_rps"
    )
    def test_document_status(self, mock_query):
        document = self.nfse_demo
        document.processador_edoc = PROCESSADOR_OCA
        document.document_type_id.code = MODELO_FISCAL_NFSE
        document.document_date = datetime.strptime(
            "2024-01-01T05:10:12", "%Y-%m-%dT%H:%M:%S"
        )
        document.date_in_out = datetime.strptime(
            "2024-01-01T05:10:12", "%Y-%m-%dT%H:%M:%S"
        )

        # Response - Unable to retrieve the document status.

        result = document._document_status()

        self.assertEqual(result, "Unable to retrieve the document status.")

    @patch(
        "odoo.addons.l10n_br_nfse_focus.models.document.FocusnfeNfse._make_focus_nfse_http_request"  # noqa: E501
    )
    def test_cancel_document_focus_with_error(self, mock_request):
        # Configura o mock para lançar uma exceção UserError em resposta
        # a uma simulação de erro HTTP 400
        mock_request.side_effect = UserError(
            "Error communicating with NFSe service: 400 Bad Request"
        )

        document = self.nfse_demo
        document.processador_edoc = PROCESSADOR_OCA
        document.document_type_id.code = MODELO_FISCAL_NFSE
        document.document_date = datetime.strptime(
            "2024-01-01T05:10:12", "%Y-%m-%dT%H:%M:%S"
        )
        document.date_in_out = datetime.strptime(
            "2024-01-01T05:10:12", "%Y-%m-%dT%H:%M:%S"
        )

        with self.assertRaises(UserError) as context:
            document.cancel_document_focus()

        # Verifica se a mensagem de erro esperada está na exceção lançada
        self.assertIn(
            "Error communicating with NFSe service: 400 Bad Request",
            str(context.exception),
        )

    @patch(
        "odoo.addons.l10n_br_nfse_focus.models.document.FocusnfeNfse.process_focus_nfse_document"  # noqa: E501
    )
    def test_eletronic_document_send(self, mock_process_focus_nfse_document):
        # Configura o mock para simular diferentes respostas
        # Cria uma resposta mockada para o status 202
        mock_response_202 = MagicMock()
        mock_response_202.status_code = 202
        mock_response_202.json.return_value = {"status": "processando_autorizacao"}

        # Cria uma resposta mockada para o status 422
        mock_response_422 = MagicMock()
        mock_response_422.status_code = 422
        mock_response_422.json.return_value = {"codigo": "algum_codigo_erro"}

        # Cria uma resposta mockada para o status 500
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_500.json.return_value = {"erro": "erro interno"}

        # Simula sequencialmente respostas para chamadas subsequentes
        mock_process_focus_nfse_document.side_effect = [
            mock_response_202,
            mock_response_422,
            mock_response_500,
        ]

        document = self.nfse_demo
        document.processador_edoc = PROCESSADOR_OCA
        document.document_type_id.code = MODELO_FISCAL_NFSE
        document.document_date = datetime.strptime(
            "2024-01-01T05:10:12", "%Y-%m-%dT%H:%M:%S"
        )
        document.date_in_out = datetime.strptime(
            "2024-01-01T05:10:12", "%Y-%m-%dT%H:%M:%S"
        )

        # Testa a lógica para a resposta 202
        document._eletronic_document_send()
        # Aqui você verifica se o estado do documento foi atualizado corretamente
        # Isso depende de como você implementou a lógica de atualização de estado no seu método

        self.assertEqual(
            document.state,
            SITUACAO_EDOC_ENVIADA,
            "O estado do documento deve ser atualizado para rejeitado devido ao erro 422",
        )

        # Testa a lógica para a resposta 422
        document._eletronic_document_send()
        self.assertEqual(
            document.state,
            SITUACAO_EDOC_REJEITADA,
            "O estado do documento deve ser 'rejeitado' após processamento com status 422",
        )

        # Testa o envio do documento com a resposta 500
        document._eletronic_document_send()
        self.assertEqual(
            document.state,
            SITUACAO_EDOC_REJEITADA,
            "O estado do documento deve permanecer 'rejeitado' "
            "após processamento com status 500",
        )

        # Verifica se o método foi chamado três vezes, uma para cada cenário de teste
        self.assertEqual(
            mock_process_focus_nfse_document.call_count,
            3,
            "O método de processamento deve ser chamado três vezes",
        )

    def test_cron_document_status_focus(self):
        record = self.nfse_demo
        record.state = "enviada"

        with patch(
            "odoo.addons.l10n_br_nfse_focus.models.document.Document.search"
        ) as mock_search:
            with patch(
                "odoo.addons.l10n_br_nfse_focus.models.document.Document.filtered"
            ) as mock_filtered:
                with patch(
                    "odoo.addons.l10n_br_nfse_focus.models.document.Document._document_status"
                ) as mock_document_status:
                    mock_search.return_value = record
                    mock_filtered.return_value = record

                    record._cron_document_status_focus()

                    self.assertTrue(mock_search)
                    mock_search.assert_called_once_with([("state", "in", ["enviada"])])
                    mock_document_status.assert_called_once()

    @patch(
        "odoo.addons.l10n_br_nfse_focus.models.document.Document.cancel_document_focus"
    )
    def test_exec_before_SITUACAO_EDOC_CANCELADA(self, mock_cancel_document_focus):
        record = self.nfse_demo
        mock_cancel_document_focus.return_value = True
        result = record._exec_before_SITUACAO_EDOC_CANCELADA(
            SITUACAO_EDOC_EM_DIGITACAO, SITUACAO_EDOC_A_ENVIAR
        )
        mock_cancel_document_focus.assert_called_once()
        self.assertEqual(result, mock_cancel_document_focus.return_value)
