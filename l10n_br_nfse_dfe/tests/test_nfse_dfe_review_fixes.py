# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import gzip
import os
from unittest import mock

import psycopg2
from odoo.addons.l10n_br_nfse_dfe.models.res_company import _NFSE_RUN
from odoo.addons.l10n_br_nfse_dfe.services import nfse_xml
from odoo.addons.l10n_br_nfse_dfe.services.adn_dfe import AdnDfeClient, AdnDfeResponse
from odoo.tests.common import TransactionCase

KEY = "35" + "1" * 48


class TestNfseDfeReviewFixes(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("l10n_br_base.empresa_lucro_presumido")
        cls.dfe = cls.env["l10n_br_fiscal_dfe.dfe"].sudo()

    def _events(self, key=KEY):
        return self.dfe.search(
            [("access_key", "=", key), ("document_type_dfe", "=", "event")]
        )

    def test_second_event_of_same_note_is_stored(self):
        first = {
            "NSU": "000000000000101",
            "ChaveAcesso": KEY,
            "TipoDocumento": "EVENTO",
            "TipoEvento": "e101103",
        }
        cancel = {
            "NSU": "000000000000102",
            "ChaveAcesso": KEY,
            "TipoDocumento": "EVENTO",
            "TipoEvento": "e101101",
        }
        self.company._nfse_create_event(first, b"", first["NSU"])
        self.company._nfse_create_event(cancel, b"", cancel["NSU"])
        self.assertEqual(
            sorted(self._events().mapped("event_type_dfe")), ["101101", "101103"]
        )

    def test_repeated_event_is_still_deduplicated(self):
        item = {
            "NSU": "000000000000103",
            "ChaveAcesso": KEY,
            "TipoDocumento": "EVENTO",
            "TipoEvento": "e101101",
        }
        self.company._nfse_create_event(item, b"", item["NSU"])
        # Same event again, even with a new NSU: not stored twice.
        again = dict(item, NSU="000000000000104")
        self.company._nfse_create_event(again, b"", again["NSU"])
        self.assertEqual(len(self._events()), 1)

    def test_database_error_does_not_advance_the_cursor(self):
        item = {"NSU": "000000000000777", "ChaveAcesso": KEY, "TipoDocumento": "NFSE"}
        error = psycopg2.OperationalError("could not serialize access")
        with mock.patch.object(
            type(self.company), "_nfse_process_item", side_effect=error
        ):
            with self.assertRaises(psycopg2.OperationalError):
                self.company._nfse_process_items([item])

    def test_bad_item_is_still_skipped_and_cursor_advances(self):
        item = {"NSU": "000000000000778", "ChaveAcesso": KEY, "TipoDocumento": "NFSE"}
        with (
            mock.patch.object(
                type(self.company),
                "_nfse_process_item",
                side_effect=ValueError("bad xml"),
            ),
            self.assertLogs(
                "odoo.addons.l10n_br_nfse_dfe.models.res_company", level="WARNING"
            ),
        ):
            highest = self.company._nfse_process_items([item])
        self.assertEqual(int(highest), 778)

    def test_gzip_over_the_limit_is_rejected(self):
        small = gzip.compress(b"<a>ok</a>")
        self.assertEqual(
            nfse_xml.decode_arquivo_xml(base64.b64encode(small).decode()), b"<a>ok</a>"
        )
        bomb = gzip.compress(b"<a>" + b"0" * 4096 + b"</a>")
        with mock.patch.object(nfse_xml, "NFSE_MAX_XML_BYTES", 1024):
            self.assertIsNone(
                nfse_xml.decode_arquivo_xml(base64.b64encode(bomb).decode())
            )

    def test_cron_is_not_reset_on_module_update(self):
        data = self.env["ir.model.data"].search(
            [
                ("module", "=", "l10n_br_nfse_dfe"),
                ("name", "=", "ir_cron_search_nfse_dfe_documents"),
            ]
        )
        self.assertTrue(data.noupdate)

    def test_one_certificate_and_session_per_run(self):
        company = self.company
        created = []
        real_client = AdnDfeClient

        def make_client(base_url, pem_path):
            client = real_client(base_url, pem_path)
            created.append((base_url, pem_path))
            return client

        ok = AdnDfeResponse(200, {}, b"{}", {}, "{}")
        module = "odoo.addons.l10n_br_nfse_dfe.models.res_company"
        with (
            mock.patch.object(
                type(company), "_nfse_certificate_pem", return_value=b"pem"
            ) as pem,
            mock.patch(f"{module}.AdnDfeClient", side_effect=make_client),
            mock.patch.object(real_client, "get", return_value=ok),
        ):
            with company._nfse_mtls_run():
                for _page in range(5):
                    company._nfse_adn_request("/contribuintes/DFe/0")
                company._nfse_sefin_request("/nfse/x")
                paths = {path for _url, path in created}
                self.assertTrue(os.path.exists(next(iter(paths))))
        # One conversion, one file, one client per base URL (ADN and Sefin).
        self.assertEqual(pem.call_count, 1)
        self.assertEqual(len(paths), 1)
        self.assertEqual(len(created), 2)
        self.assertFalse(os.path.exists(next(iter(paths))))

    def test_without_a_run_each_request_is_independent(self):
        company = self.company
        ok = AdnDfeResponse(200, {}, b"{}", {}, "{}")
        with (
            mock.patch.object(
                type(company), "_nfse_certificate_pem", return_value=b"pem"
            ) as pem,
            mock.patch.object(AdnDfeClient, "get", return_value=ok),
        ):
            company._nfse_adn_request("/a")
            company._nfse_adn_request("/b")
        self.assertEqual(pem.call_count, 2)

    def test_run_cleans_up_when_the_body_fails(self):
        company = self.company
        ok = AdnDfeResponse(200, {}, b"{}", {}, "{}")
        seen = []
        with (
            mock.patch.object(
                type(company), "_nfse_certificate_pem", return_value=b"pem"
            ),
            mock.patch.object(AdnDfeClient, "get", return_value=ok),
        ):
            with self.assertRaises(RuntimeError):
                with company._nfse_mtls_run():
                    company._nfse_adn_request("/a")
                    seen.extend(run["pem_path"] for run in _NFSE_RUN.runs.values())
                    raise RuntimeError("boom")
            self.assertFalse(os.path.exists(seen[0]))
            self.assertFalse(getattr(_NFSE_RUN, "runs", {}))
