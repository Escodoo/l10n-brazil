# Copyright 2026 Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import gzip
from datetime import timedelta
from io import BytesIO
from unittest import mock

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

from odoo.addons.l10n_br_fiscal_dfe.constants.dfe import DFE_INTERVAL_NO_DOCS
from odoo.addons.l10n_br_nfse_dfe.services.adn_dfe import AdnDfeClient, AdnDfeResponse

PROVIDER_CNPJ = "59594315000157"
DECOY_CNPJ = "81493979000189"
TAKER_CNPJ = "81583054000129"
ACCESS_KEY = "8" * 50
NS = "http://www.sped.fazenda.gov.br/nfse"


def nfse_xml(access_key=ACCESS_KEY, retention="1"):
    """National NFS-e with a decoy CNPJ before the provider."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<NFSe xmlns="{NS}">
  <infNFSe Id="NFS{access_key}">
    <nNFSe>123</nNFSe>
    <dhProc>2023-09-09T12:42:06-03:00</dhProc>
    <cLocIncid>3550308</cLocIncid>
    <emit>
      <CNPJ>{DECOY_CNPJ}</CNPJ>
      <xNome>Decoy Emitter</xNome>
    </emit>
    <valores>
      <vBC>20.00</vBC>
      <pAliqAplic>2.00</pAliqAplic>
      <vISSQN>0.40</vISSQN>
      <vLiq>20.00</vLiq>
    </valores>
    <DPS>
      <infDPS>
        <dhEmi>2023-09-09T09:42:06-03:00</dhEmi>
        <serie>00007</serie>
        <nDPS>2</nDPS>
        <prest>
          <CNPJ>{PROVIDER_CNPJ}</CNPJ>
          <xNome>Provider Test</xNome>
        </prest>
        <toma>
          <CNPJ>{TAKER_CNPJ}</CNPJ>
          <xNome>Empresa Lucro Presumido</xNome>
        </toma>
        <serv>
          <cServ>
            <cTribNac>010101</cTribNac>
            <cNBS>123456789</cNBS>
            <xDescServ>Consulting</xDescServ>
          </cServ>
        </serv>
        <valores>
          <vServPrest><vServ>20.00</vServ></vServPrest>
          <trib><tribMun><tpRetISSQN>{retention}</tpRetISSQN></tribMun></trib>
        </valores>
      </infDPS>
    </DPS>
  </infNFSe>
</NFSe>
""".encode()


def event_xml(access_key=ACCESS_KEY, event_type="101101"):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<evento xmlns="{NS}">
  <infEvento>
    <chNFSe>{access_key}</chNFSe>
    <tpEvento>{event_type}</tpEvento>
  </infEvento>
</evento>
""".encode()


def gzip_base64(payload):
    buffer = BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb") as handle:
        handle.write(payload)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def response(status, body=None, headers=None):
    return AdnDfeResponse(
        status_code=status,
        body=body,
        content=b"",
        headers=headers or {},
        text="",
    )


class TestNfseDfe(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("l10n_br_base.empresa_lucro_presumido")
        cls.company.nfse_dfe_environment = "producao_restrita"
        cls.provider = cls.env["res.partner"].search(
            [("cnpj_cpf_stripped", "=", PROVIDER_CNPJ)], limit=1
        )
        if not cls.provider:
            raise AssertionError("Demo provider CNPJ 59594315000157 was not found")

    def _documents(self):
        return self.env["l10n_br_fiscal_dfe.document"].search(
            [("company_id", "=", self.company.id), ("fiscal_type", "=", "nfse")]
        )

    def _logs(self):
        return self.env["l10n_br_fiscal_dfe.distribution_log"].search(
            [("company_id", "=", self.company.id), ("fiscal_type", "=", "nfse")]
        )

    def _distribute(self, side_effect, page_size=None):
        patchers = [
            mock.patch.object(type(self.company), "_nfse_adn_request", side_effect)
        ]
        if page_size:
            patchers.append(
                mock.patch(
                    "odoo.addons.l10n_br_nfse_dfe.models.res_company.NFSE_LOTE_SIZE",
                    page_size,
                )
            )
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.company._nfse_document_distribution()

    def test_lote_note_event_and_dedup(self):
        note = {
            "NSU": 10,
            "ChaveAcesso": ACCESS_KEY,
            "TipoDocumento": "NFSE",
            "ArquivoXml": gzip_base64(nfse_xml()),
        }
        event = {
            "NSU": 11,
            "ChaveAcesso": ACCESS_KEY,
            "TipoDocumento": "EVENTO",
            "TipoEvento": "101101",
            "ArquivoXml": base64.b64encode(event_xml()).decode("ascii"),
        }
        calls = []

        def side_effect(_company, path, params=None):
            calls.append((path, params))
            return response(200, {"LoteDFe": [note, event]})

        self._distribute(side_effect)
        documents = self._documents()
        if not documents:
            self.fail(self._logs().mapped("message"))
        self.assertEqual(len(documents), 1)
        document = documents
        self.assertEqual(document.access_key, ACCESS_KEY)
        self.assertEqual(document.emitter, "Provider Test")
        self.assertEqual(document.document_number, "123")
        self.assertEqual(document.serie, "7")
        self.assertEqual(document.document_amount, 20.0)
        self.assertEqual(document.document_state, "3")
        self.assertEqual(document.document_state_label, "Cancelled")
        self.assertEqual(document.partner_id, self.provider)
        self.assertFalse(document.is_own_document)
        self.assertEqual(document.document_emission_date.hour, 12)
        self.assertEqual(
            set(document.dfe_ids.mapped("document_type_dfe")), {"complete", "event"}
        )
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][0].endswith("/contribuintes/DFe/0"))
        self.assertEqual(calls[0][1]["cnpjConsulta"], TAKER_CNPJ)

        self.company.nfse_dfe_next_query = False
        self.company._nfse_document_distribution()
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(self._documents()), 1)
        self.assertEqual(len(document.dfe_ids), 2)

    def test_pagination_stops_on_404(self):
        calls = []

        def side_effect(_company, path, params=None):
            calls.append(path)
            if len(calls) == 1:
                return response(
                    200,
                    {
                        "LoteDFe": [
                            {
                                "NSU": 10,
                                "ChaveAcesso": ACCESS_KEY,
                                "TipoDocumento": "NFSE",
                                "ArquivoXml": base64.b64encode(nfse_xml()).decode(),
                            }
                        ]
                    },
                )
            return response(404)

        self.company.nfse_last_nsu = "0"
        self._distribute(side_effect, page_size=1)
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[1].endswith("/contribuintes/DFe/10"))
        self.assertEqual(self.company.nfse_last_nsu, "000000000000010")
        self.assertEqual(self.company.nfse_dfe_last_status_code, "137")

    def test_404_keeps_cursor_and_schedules_empty_interval(self):
        self.company.nfse_last_nsu = "000000000000005"
        self.company.nfse_dfe_next_query = False
        before = fields.Datetime.now()

        def side_effect(_company, path, params=None):
            return response(404)

        self._distribute(side_effect)
        self.assertEqual(self.company.nfse_last_nsu, "000000000000005")
        self.assertEqual(self.company.nfse_dfe_last_status_code, "137")
        delta = self.company.nfse_dfe_next_query - before
        self.assertGreaterEqual(delta, DFE_INTERVAL_NO_DOCS - timedelta(seconds=5))
        self.assertLessEqual(delta, DFE_INTERVAL_NO_DOCS + timedelta(minutes=2))

    def test_429_honors_retry_after(self):
        self.company.nfse_last_nsu = "000000000000005"
        self.company.nfse_dfe_next_query = False
        before = fields.Datetime.now()

        def side_effect(_company, path, params=None):
            return response(429, headers={"Retry-After": "90"})

        self._distribute(side_effect)
        self.assertEqual(self.company.nfse_last_nsu, "000000000000005")
        self.assertEqual(self.company.nfse_dfe_last_status_code, "656")
        seconds = (self.company.nfse_dfe_next_query - before).total_seconds()
        self.assertGreaterEqual(seconds, 85)
        self.assertLessEqual(seconds, 100)

    def test_nfe_distribution_does_not_call_adn(self):
        parent = (
            "odoo.addons.l10n_br_fiscal_dfe.models.res_company."
            "ResCompany._dfe_document_distribution"
        )
        with (
            mock.patch.object(
                type(self.company), "_nfse_document_distribution"
            ) as nfse_loop,
            mock.patch(parent, return_value=None) as soap_loop,
        ):
            self.company._dfe_document_distribution("nfe")
        nfse_loop.assert_not_called()
        soap_loop.assert_called_once()

    def test_nfse_distribution_dispatches_to_adn_loop(self):
        with mock.patch.object(
            type(self.company), "_nfse_document_distribution", return_value=None
        ) as nfse_loop:
            self.company._dfe_document_distribution("nfse")
        nfse_loop.assert_called_once()

    def test_44_digit_key_still_matches_partner(self):
        digits = "31282204000196"
        partner = self.env["res.partner"].search(
            [("cnpj_cpf_stripped", "=", digits)], limit=1
        )
        if not partner:
            partner = self.env["res.partner"].create(
                {
                    "name": "NF-e Partner",
                    "is_company": True,
                    "vat": "31.282.204/0001-96",
                }
            )
        key = f"352001{digits}550010000000012062777161"
        self.assertEqual(len(key), 44)
        document = self.env["l10n_br_fiscal_dfe.document"].create(
            {
                "access_key": key,
                "company_id": self.company.id,
                "fiscal_type": "nfe",
            }
        )
        self.assertEqual(len(document.access_key), 44)
        self.assertEqual(document.partner_id, partner)
        nfse_key = self.env["l10n_br_fiscal_dfe.document"].create(
            {
                "access_key": "9" * 50,
                "company_id": self.company.id,
                "fiscal_type": "nfse",
                "vat": self.company.vat,
            }
        )
        self.assertEqual(len(nfse_key.access_key), 50)
        self.assertTrue(nfse_key.is_own_document)

    def test_import_requires_complete_xml(self):
        document = self.env["l10n_br_fiscal_dfe.document"].create(
            {
                "access_key": "6" * 50,
                "company_id": self.company.id,
                "fiscal_type": "nfse",
            }
        )
        with self.assertRaises(UserError):
            document.import_document()

    def test_specific_search_accepts_50_digits(self):
        wizard = self.env["dfe.specific.search.wizard"].create(
            {
                "company_id": self.company.id,
                "fiscal_type": "nfse",
                "search_type": "access_key",
            }
        )
        with self.assertRaises(UserError):
            wizard._validate_access_key("1" * 44)
        wizard._validate_access_key(ACCESS_KEY)

    def test_adn_client_keeps_tls_verification(self):
        client = AdnDfeClient(
            "https://adn.producaorestrita.nfse.gov.br", "/tmp/unused.pem"
        )
        self.assertIs(client._session.verify, True)
        mocked = mock.Mock(
            status_code=200,
            content=b"",
            headers={},
            text="",
        )
        mocked.json.return_value = {}
        with mock.patch.object(client._session, "get", return_value=mocked) as get:
            client.get("/contribuintes/DFe/0", params={"lote": "true"})
        self.assertTrue(get.call_args.args[0].endswith("/contribuintes/DFe/0"))
