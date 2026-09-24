# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime

from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_br_dere.models import xml_builder

from .common import DereCommon

SCHEMAS = "http://www.dere.gov.br/schemas"
RETURN_VERSIONS = {
    "evtRetornoTabela": "v1_0_1",
    "evtRetornoBalan": "v1_0_0",
    "evtRetornoAplicFin": "v1_0_0",
    "evtRetornoRDed": "v0_0_1",
    "evtRetornoReabert": "v0_0_1",
    "evtRetornoMensal": "v0_0_2",
}
VALID_HASH = "A" * 43 + "="


@tagged("post_install", "-at_install")
class TestDereReturns(DereCommon):
    def _event_return(self, tag, event, receipt, info_evento="", hash_value=None):
        seq = "" if tag == "evtRetornoTabela" else "<seqEvento>00</seqEvento>"
        return (
            f'<DeRE xmlns="{SCHEMAS}/{tag}/{RETURN_VERSIONS[tag]}">'
            f'<{tag} id="{event.event_id_attr}">'
            f"<ideContrib><nrInsc>{self.company._dere_cnpj_root()}</nrInsc>"
            "</ideContrib>"
            "<ideStatus><cdRetorno>1</cdRetorno>"
            "<descRetorno>Sucesso</descRetorno></ideStatus>"
            "<infoRecEv>"
            f"<nrRecibo>{receipt}</nrRecibo>{seq}"
            "<dhRecepcao>2026-12-05T12:00:00.1234567-03:00</dhRecepcao>"
            "<dhProcess>2026-12-05T12:00:01.0000000-03:00</dhProcess>"
            f"<tpEv>{event.event_type}</tpEv>"
            f"<hash>{hash_value or VALID_HASH}</hash>"
            "</infoRecEv>"
            f"{info_evento}"
            f"</{tag}>"
            "</DeRE>"
        )

    def _lot(self, *returns):
        events = "".join(
            f'<evento id="{event.event_id_attr}">{xml}</evento>'
            for event, xml in returns
        )
        return (
            f'<DeRE xmlns="{SCHEMAS}/retornoLoteDere/v1_0_1">'
            "<retornoLoteEventos>"
            "<status><cdResposta>2</cdResposta>"
            "<descResposta>Done</descResposta></status>"
            f"<retornoEventos>{events}</retornoEventos>"
            "</retornoLoteEventos>"
            "</DeRE>"
        )

    def _consult(self, parent, *returns):
        events = self.env["l10n_br_dere.event"].union(*(ev for ev, _xml in returns))
        field = (
            "table_period_id"
            if parent._name == "l10n_br_dere.table.period"
            else "declaration_id"
        )
        batch = self.env["l10n_br_dere.batch"].create(
            {
                field: parent.id,
                "tp_amb": "2",
                "state": "sent",
                "protocol": "1.000000.1",
                "event_ids": [Command.set(events.ids)],
            }
        )
        parent._apply_consult_result(batch, self._lot(*returns))
        return batch

    def _pgcc_receipt(self, declaration):
        return self._event(declaration, "D-1011").nr_recibo

    def _balan_info(self, declaration, totals=""):
        return (
            "<infoEvento>"
            f"<idePeriodo><perApur>{declaration.per_apur}</perApur></idePeriodo>"
            f"<infoAdic><nrReciboPGCC>{self._pgcc_receipt(declaration)}"
            "</nrReciboPGCC></infoAdic>"
            f"{totals}"
            "</infoEvento>"
        )

    def _schema_messages(self, event):
        return event.message_ids.filtered(
            lambda message: "official XSD" in (message.body or "")
        )

    def test_parse_datetime_normalizes_fraction_and_offset(self):
        self.assertEqual(
            xml_builder.parse_datetime("2026-12-05T12:00:00.1234567-03:00"),
            datetime(2026, 12, 5, 15, 0, 0, 123456),
        )
        self.assertEqual(
            xml_builder.parse_datetime("2026-10-16T12:00:00Z"),
            datetime(2026, 10, 16, 12, 0, 0),
        )
        self.assertFalse(xml_builder.parse_datetime(""))
        self.assertFalse(xml_builder.parse_datetime("not a date"))

    def test_return_metadata_is_stored_per_event(self):
        declaration = self._prepare_trial()
        event = self._event(declaration, "D-1101")
        receipt = self._event_receipt("D-1101", declaration.per_apur)
        self._consult(
            declaration,
            (
                event,
                self._event_return(
                    "evtRetornoBalan", event, receipt, self._balan_info(declaration)
                ),
            ),
        )
        self.assertEqual(event.state, "accepted")
        self.assertEqual(event.nr_recibo, receipt)
        self.assertEqual(event.return_type, "D-9101")
        self.assertEqual(event.seq_evento, "00")
        self.assertEqual(event.dh_recepcao, datetime(2026, 12, 5, 15, 0, 0, 123456))
        self.assertEqual(event.dh_process, datetime(2026, 12, 5, 15, 0, 1))
        self.assertEqual(event.nr_recibo_pgcc, self._pgcc_receipt(declaration))
        self.assertIn("evtRetornoBalan", event.return_xml)
        self.assertFalse(self._schema_messages(event))

    def test_invalid_return_is_kept_and_flagged(self):
        declaration = self._prepare_trial()
        event = self._event(declaration, "D-1101")
        receipt = self._event_receipt("D-1101", declaration.per_apur)
        self._consult(
            declaration,
            (
                event,
                self._event_return(
                    "evtRetornoBalan",
                    event,
                    receipt,
                    self._balan_info(declaration),
                    hash_value="abcd",
                ),
            ),
        )
        self.assertEqual(event.state, "accepted")
        self.assertTrue(event.return_xml)
        self.assertTrue(self._schema_messages(event))

    def test_return_types_are_not_event_types(self):
        selection = dict(self.env["l10n_br_dere.event"]._fields["event_type"].selection)
        self.assertFalse([code for code in selection if code.startswith("D-9")])
