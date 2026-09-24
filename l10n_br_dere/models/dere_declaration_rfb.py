# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from collections import defaultdict

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.tools import float_is_zero, float_round

from ..constants import (
    EVENT_D1011,
    EVENT_D1101,
    EVENT_D1106,
    EVENT_D1121,
    RETURN_D9101,
    RETURN_D9106,
)

RFB_RETURN_EVENTS = (EVENT_D1101, EVENT_D1106, EVENT_D1121)


def _amount(value):
    return float(value) if value else 0.0


def _rounded(value):
    return float_round(abs(value or 0.0), precision_digits=2)


class DereDeclaration(models.Model):
    _inherit = "l10n_br_dere.declaration"

    rfb_total_ids = fields.Many2many(
        comodel_name="l10n_br_dere.event.total",
        compute="_compute_rfb_assessment",
        string="RFB totals",
    )
    rfb_mismatch = fields.Boolean(
        compute="_compute_rfb_assessment",
        string="RFB mismatch",
        help="The RFB return differs from the local data or used another "
        "receipt than the events in force.",
    )

    @api.depends(
        "event_ids.state",
        "event_ids.nr_recibo_pgcc",
        "event_ids.total_ids.has_difference",
        "table_period_id.event_ids.nr_recibo",
    )
    def _compute_rfb_assessment(self):
        for rec in self:
            events = rec._rfb_return_events()
            rec.rfb_total_ids = events.total_ids
            rec.rfb_mismatch = bool(rec._rfb_issues(events))

    def _rfb_return_events(self):
        self.ensure_one()
        events = self.env["l10n_br_dere.event"]
        for event_type in RFB_RETURN_EVENTS:
            events |= self._active_event(event_type)
        return events

    def _rfb_issues(self, events):
        self.ensure_one()
        pgcc_receipt = self._active_event(EVENT_D1011).nr_recibo
        issues = []
        for event in events:
            used = event.nr_recibo_pgcc
            if used and pgcc_receipt and used != pgcc_receipt:
                issues.append(
                    _(
                        "%(event)s was totalized with PGCC receipt %(used)s "
                        "instead of the D-1011 receipt in force %(active)s."
                    )
                    % {
                        "event": event.event_type,
                        "used": used,
                        "active": pgcc_receipt,
                    }
                )
            for total in event.total_ids.filtered("has_difference"):
                issues.append(
                    _("%(event)s total %(code)s: RFB %(rfb).2f, " "local %(local).2f.")
                    % {
                        "event": event.event_type,
                        "code": total.dere12_codTrib or "",
                        "rfb": total.dere12_vApurTot,
                        "local": total.local_v_apur,
                    }
                )
        return issues

    def _local_rfb_totals(self, event_type):
        self.ensure_one()
        if event_type == EVENT_D1106:
            amount = sum(_rounded(line.dere12_vApur) for line in self.reserve_line_ids)
            return {(False, False): amount}
        totals = defaultdict(float)
        for line in self.trial_line_ids:
            account = line.pgcc_account_id
            key = (account.tax_code_id.code or False, account.dere12_indTribISS or "0")
            totals[key] += _rounded(line.dere12_vApur)
        return dict(totals)

    def _store_rfb_totals(self, event, totals):
        self.ensure_one()
        event.sudo().total_ids.unlink()
        local = self._local_rfb_totals(event.event_type)
        rows = []
        for item in totals:
            key = (item.get("codTrib") or False, item.get("indTribISS") or False)
            rows.append(
                {
                    "event_id": event.id,
                    "dere12_codTrib": key[0],
                    "dere12_indTribISS": key[1],
                    "dere12_vApurTot": _amount(item.get("vApurTot")),
                    "dere12_vTotSaldoInic": _amount(item.get("vTotSaldoInic")),
                    "dere12_vTotSaldoFinal": _amount(item.get("vTotSaldoFinal")),
                    "local_v_apur": local.pop(key, 0.0),
                }
            )
        rows += [
            {
                "event_id": event.id,
                "dere12_codTrib": code,
                "dere12_indTribISS": ind_trib_iss,
                "dere12_vApurTot": 0.0,
                "local_v_apur": amount,
            }
            for (code, ind_trib_iss), amount in local.items()
            if not float_is_zero(amount, precision_digits=2)
        ]
        return self.env["l10n_br_dere.event.total"].sudo().create(rows)

    def _apply_return_content(self, event, payload):
        res = super()._apply_return_content(event, payload)
        if event.state != "accepted" or not payload:
            return res
        if event.return_type in (RETURN_D9101, RETURN_D9106):
            self._store_rfb_totals(event, payload.get("totals") or [])
        issues = self._rfb_issues(event)
        if issues:
            self.message_post(
                body=Markup("%s<br/>%s")
                % (
                    _("The RFB return differs from the local data:"),
                    Markup("<br/>").join(issues),
                )
            )
        return res
