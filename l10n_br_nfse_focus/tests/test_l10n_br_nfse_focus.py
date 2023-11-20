from unittest.mock import MagicMock, call, patch

from odoo.exceptions import UserError
from odoo.tests import common

from odoo.addons.l10n_br_fiscal.constants.fiscal import (
    MODELO_FISCAL_NFE,
    MODELO_FISCAL_NFSE,
    PROCESSADOR_NENHUM,
    PROCESSADOR_OCA,
    SITUACAO_EDOC_AUTORIZADA,
    SITUACAO_EDOC_CANCELADA,
)
from odoo.addons.l10n_br_fiscal.models.document_workflow import (
    DocumentWorkflow as FiscalDocument,
)

from ..models.document import (
    API_ENDPOINT,
    NFSE_URL,
    Document,
    NFSeFocus,
    filter_focusnfe,
    filter_oca_nfse,
)

MOCK_PATH = "odoo.addons.l10n_br_nfse_focus"

PAYLOAD = [
    {
        "rps": {
            "data_emissao": "2023-11-20T18:30:00",
            "incentivador_cultural": False,
            "natureza_operacao": "1",
            "optante_simples_nacional": True,
            "status": "1",
            "cnpj": "12345678901234",
            "inscricao_municipal": "12345",
            "codigo_municipio": "1234567",
            "id": "abc123",
        }
    },
    {
        "service": {
            "aliquota": 3,
            "discriminacao": "Nota fiscal referente a serviços prestados",
            "iss_retido": "false",
            "item_lista_servico": "0107",
            "codigo_tributario_municipio": "620910000",
            "valor_servicos": 1.0,
        }
    },
    {
        "tomador": {
            "cnpj": "07504505000132",
            "razao_social": "Acras Tecnologia da Informação LTDA",
            "email": "contato@focusnfe.com.br",
            "endereco": {
                "logradouro": "Rua Dias da Rocha Filho",
                "numero": "999",
                "complemento": "Prédio 04 - Sala 34C",
                "bairro": "Alto da XV",
                "codigo_municipio": "4106902",
                "uf": "PR",
                "cep": "80045165",
            },
        }
    },
    {
        "prestador": {
            "cnpj": "18765499000199",
            "inscricao_municipal": "12345",
            "codigo_municipio": "3516200",
        }
    },
]

PAYLOAD_REF = "00012345"


class TestL10nBrNfseFocus(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.tpAmb = "2"
        self.token = "123456789"
        self.company = self.env.ref("l10n_br_base.empresa_lucro_presumido")
        self.company.focusnfe_homologation_token = self.token
        self.company.provedor_nfse = "focusnfe"
        self.nfse_demo = self.env.ref("l10n_br_fiscal.demo_nfe_same_state")
        self.nfse_demo.document_number = "0001"
        self.nfse_demo.rps_number = "0002"

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

    @patch("odoo.addons.l10n_br_nfse_focus.models.document.requests.post")
    def test_processar_documento(self, mock_post):
        nfse_focus = NFSeFocus(self.tpAmb, self.token, self.company)

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"status": "simulado"}

        result = nfse_focus.processar_documento(PAYLOAD)

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {"status": "simulado"})

    @patch("odoo.addons.l10n_br_nfse_focus.models.document.requests.post")
    def test_post(self, mock_post):
        nfse_focus = NFSeFocus(self.tpAmb, self.token, self.company)
        URL = NFSE_URL[self.tpAmb] + API_ENDPOINT["envio"]

        # Response 200
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"status": "success"}
        result = nfse_focus._post(URL, PAYLOAD_REF, PAYLOAD)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {"status": "success"})

        # Response 201
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {"status": "created"}
        result = nfse_focus._post(URL, PAYLOAD_REF, PAYLOAD)
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.json(), {"status": "created"})

        # Response 202
        mock_post.return_value.status_code = 202
        mock_post.return_value.json.return_value = {"status": "accepted"}
        result = nfse_focus._post(URL, PAYLOAD_REF, PAYLOAD)
        self.assertEqual(result.status_code, 202)
        self.assertEqual(result.json(), {"status": "accepted"})

        # Response 422
        mock_post.return_value.status_code = 422
        mock_post.return_value.json.return_value = {"errors": ["Invalid data"]}
        result = nfse_focus._post(URL, PAYLOAD_REF, PAYLOAD)
        self.assertEqual(result.status_code, 422)
        self.assertEqual(result.json(), {"errors": ["Invalid data"]})

        # Response 500
        mock_post.return_value.status_code = 500
        mock_post.return_value.text = "Internal server error"
        with self.assertRaises(UserError) as error:
            nfse_focus._post(URL, PAYLOAD_REF, PAYLOAD)
        self.assertEqual(str(error.exception), "500 - Internal server error")

    @patch("odoo.addons.l10n_br_nfse_focus.models.document.requests.get")
    def test_consulta_nfse_rps(self, mock_get):
        nfse_focus = NFSeFocus(self.tpAmb, self.token, self.company)

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "status": "success",
            "data": {"nfse_info": "…"},
        }
        result = nfse_focus.consulta_nfse_rps(PAYLOAD_REF, {"completa": "sim"})

        self.assertEqual(result.status_code, 200)
        self.assertEqual(
            result.json(), {"status": "success", "data": {"nfse_info": "…"}}
        )

    @patch("odoo.addons.l10n_br_nfse_focus.models.document.requests.get")
    def test_get(self, mock_get):
        nfse_focus = NFSeFocus(self.tpAmb, self.token, self.company)

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"data": "…"}
        result = nfse_focus._get(NFSE_URL[self.tpAmb], {"completa": "sim"})

        self.assertEqual(result.status_code, 200)

    @patch("odoo.addons.l10n_br_nfse_focus.models.document.requests.delete")
    def test_cancela_documento(self, mock_delete):
        nfse_focus = NFSeFocus(self.tpAmb, self.token, self.company)

        mock_delete.return_value.status_code = 204
        result = nfse_focus.cancela_documento(PAYLOAD_REF, "Teste de cancelamento")

        self.assertEqual(result.status_code, 204)

    def test_make_pdf_focus(self):
        document = self.nfse_demo
        document.processador_edoc = PROCESSADOR_NENHUM
        document.document_type_id.code = MODELO_FISCAL_NFE

        attachment_model = MagicMock()
        attachment_model.create = MagicMock()

        original_env = document.env
        document.env = MagicMock(return_value={"ir.attachment": attachment_model})

        try:
            result = document.make_pdf_focus(b"PDF content")
        finally:
            document.env = original_env

        self.assertIsNone(result)

    def test_serialize(self):
        doc = self.nfse_demo
        edocs = []
        with patch.object(Document, "_serialize", return_value=edocs) as mock_serialize:
            result = doc._serialize(edocs)

        mock_serialize.assert_called_once_with(edocs)
        self.assertEqual(result, edocs)

    @patch("odoo.addons.l10n_br_nfse.models.document.Document._prepare_lote_rps")
    @patch("odoo.addons.l10n_br_nfse.models.document.Document._prepare_dados_servico")
    @patch("odoo.addons.l10n_br_nfse.models.document.Document._prepare_dados_tomador")
    @patch("odoo.addons.l10n_br_nfse_focus.models.document.filter_oca_nfse")
    @patch("odoo.addons.l10n_br_nfse_focus.models.document.filter_focusnfe")
    def test_serialize_nfse_focus(
        self,
        mock_filter_focusnfe,
        mock_filter_oca_nfse,
        mock_prepare_lote_rps,
        mock_prepare_dados_servico,
        mock_prepare_dados_tomador,
    ):
        mock_filter_focusnfe.return_value = True
        mock_filter_oca_nfse.return_value = True

        document = self.nfse_demo

        with patch(
            "odoo.addons.l10n_br_nfse.models.document.Document._prepare_lote_rps"
        ) as mock_lote_rps, patch(
            "odoo.addons.l10n_br_nfse.models.document.Document._prepare_dados_servico"
        ) as mock_dados_servico, patch(
            "odoo.addons.l10n_br_nfse.models.document.Document._prepare_dados_tomador"
        ) as mock_dados_tomador:

            mock_lote_rps.return_value = {"lote_rps_data": "Test Data Lote RPS"}
            mock_dados_servico.return_value = {"servico_data": "Test Data Servico"}
            mock_dados_tomador.return_value = {"lote_rps_data": "Test Data Lote RPS"}

            result = document.serialize_nfse_focus()

        mock_lote_rps.assert_called_with()
        mock_dados_servico.assert_called_with()
        mock_dados_tomador.assert_called_with()

        expected_result = [
            {"rps": {"lote_rps_data": "Test Data Lote RPS"}},
            {"service": {"servico_data": "Test Data Servico"}},
            {"tomador": {"lote_rps_data": "Test Data Lote RPS"}},
        ]
        self.assertEqual(result, expected_result)

    @patch("odoo.addons.l10n_br_nfse_focus.models.document.NFSeFocus")
    def test_processador_nfse_focus(self, mock_nfse_focus):
        self.nfse_demo._processador_nfse_focus()

        self.assertEqual(
            mock_nfse_focus.call_args,
            call(
                tpAmb="2",
                token=self.company.get_focusnfe_token(),
                company=self.company,
            ),
        )

        mock_nfse_focus.assert_called_once()

    def test_document_export(self):
        record = self.nfse_demo
        record.processador_edoc = PROCESSADOR_OCA
        record.document_type_id.code = MODELO_FISCAL_NFSE

        with patch.object(
            FiscalDocument, "_document_export"
        ) as mock_super_document_export:
            record._document_export()
            mock_super_document_export.assert_called_once()

        with patch(
            "odoo.addons.l10n_br_nfse_focus.models.document.Document._document_export"
        ) as mock_document_export:
            record._document_export()
            mock_document_export.assert_called_once()

            with patch(
                "odoo.addons.l10n_br_fiscal.models.document_event.Event.create_event_save_xml"
            ) as mock_create_event:
                self.assertIsNotNone(record.company_id.provedor_nfse)

                record.event_ids.create_event_save_xml(
                    company_id=record.company_id,
                    environment=record.nfse_environment,
                    event_type="0",
                    xml_file="",
                    document_id=record,
                )

                mock_create_event.assert_called_with(
                    company_id=record.company_id,
                    environment=record.nfse_environment,
                    event_type="0",
                    xml_file="",
                    document_id=record,
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

                    mock_search.assert_called_once_with([("state", "in", ["enviada"])])
                    mock_document_status.assert_called_once()

    def test_exec_before_SITUACAO_EDOC_CANCELADA(self):
        record = self.nfse_demo
        record.state = SITUACAO_EDOC_CANCELADA

        with patch.object(
            Document, "_exec_before_SITUACAO_EDOC_CANCELADA"
        ) as mock_parent_method:
            record._exec_before_SITUACAO_EDOC_CANCELADA(
                SITUACAO_EDOC_CANCELADA, SITUACAO_EDOC_AUTORIZADA
            )
            mock_parent_method.assert_called_once_with(
                SITUACAO_EDOC_CANCELADA, SITUACAO_EDOC_AUTORIZADA
            )
