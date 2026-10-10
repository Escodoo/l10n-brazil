# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import Mock, patch

import requests

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import DereCommon

INTEGRA = "odoo.addons.l10n_br_dere.models.receita_integra.DereReceitaIntegra"


@tagged("post_install", "-at_install")
class TestDereTransmissionHardening(DereCommon):
    def _sent_batch(self):
        declaration = self._create_declaration("2026-10")
        return self.env["l10n_br_dere.batch"].create(
            {
                "name": "hardening",
                "declaration_id": declaration.id,
                "tp_amb": "2",
                "state": "sent",
                "protocol": "P" * 28,
                "xml_content": "<x/>",
            }
        )

    def test_token_without_access_token_is_rejected(self):
        response = Mock(status_code=200, text='{"expires_in": 3600}')
        response.json.return_value = {"expires_in": 3600}
        with patch(
            "odoo.addons.l10n_br_dere.models.receita_integra.requests.post",
            return_value=response,
        ):
            with self.assertRaises(UserError):
                self.env["l10n_br_dere.receita.integra"]._request_token(self.company)
        self.assertFalse(
            self.env["l10n_br_dere.receita.integra"]._cached_token(self.company)
        )

    def test_token_non_json_body_is_a_user_error(self):
        response = Mock(status_code=200, text="<html>gateway</html>")
        response.json.side_effect = ValueError("no json")
        with patch(
            "odoo.addons.l10n_br_dere.models.receita_integra.requests.post",
            return_value=response,
        ):
            with self.assertRaises(UserError):
                self.env["l10n_br_dere.receita.integra"]._request_token(self.company)

    def test_cron_backs_off_when_gateway_is_unreachable(self):
        batch = self._sent_batch()
        with patch(
            INTEGRA + ".consult_batch",
            side_effect=requests.ConnectionError("down"),
        ):
            self.env["l10n_br_dere.batch"]._cron_consult_batches()
        self.assertEqual(batch.state, "sent")
        self.assertEqual(batch.consult_attempts, 1)
        self.assertTrue(batch.next_consult_at)

    def test_manual_consult_reports_unreachable_gateway(self):
        batch = self._sent_batch()
        with patch(
            INTEGRA + ".consult_batch",
            side_effect=requests.Timeout("slow"),
        ):
            with self.assertRaises(UserError):
                batch.action_consult()
