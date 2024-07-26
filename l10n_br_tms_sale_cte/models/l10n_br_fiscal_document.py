# Copyright 2024 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class FiscalDocument(models.Model):

    _inherit = "l10n_br_fiscal.document"

    cte40_rem = fields.Many2one(
        comodel_name="res.partner",
        related="partner_sendering_id",
    )

    cte40_exped = fields.Many2one(
        comodel_name="res.partner",
        related="partner_shippering_id",
    )

    cte40_receb = fields.Many2one(
        comodel_name="res.partner",
        related="partner_receivering_id",
    )

    @api.depends("commitment_date", "expected_date")
    def _compute_cte40_dProg(self):
        for record in self:
            if record.commitment_date:
                record.cte40_dProg = record.commitment_date.date()
            elif record.expected_date:
                record.cte40_dProg = record.expected_date.date()
            else:
                record.cte40_dProg = False

    cte40_dProg = fields.Date(
        compute="_compute_cte40_dProg",
    )

    @api.depends("partner_id")
    def _compute_service_provider(self):
        for record in self:
            if record.partner_shipping_id == record.partner_id:
                record.service_provider = "3"  # Destinatário
            elif record.partner_sendering_id == record.partner_id:
                record.service_provider = "0"  # Remetente
            elif record.partner_receivering_id == record.partner_id:
                record.service_provider = "2"  # Recebedor
            elif record.partner_shippering_id == record.partner_id:
                record.service_provider = "1"  # Expedidor
            else:
                record.service_provider = False

    service_provider = fields.Selection(compute="_compute_service_provider")

    @api.depends("tms_transport_modal")
    def _compute_transport_modal(self):
        for record in self:
            record.transport_modal = record.tms_transport_modal

    transport_modal = fields.Selection(
        compute="_compute_transport_modal", store=True, readonly=False
    )

    def _compute_cte40_vCarga(self):
        for record in self:
            record.cte40_vCarga = record.tms_cargo_value

    cte40_vCarga = fields.Monetary(
        compute="_compute_cte40_vCarga",
    )

    def _compute_cte40_vCargaAverb(self):
        for record in self:
            record.cte40_vCargaAverb = record.tms_insured_value

    cte40_vCargaAverb = fields.Monetary(
        compute="_compute_cte40_vCargaAverb",
    )

    def _compute_cte40_proPred(self):
        for record in self:
            record.cte40_proPred = record.tms_main_product

    cte40_proPred = fields.Char(compute="_compute_cte40_proPred")

    def _compute_cte40_xOutCat(self):
        for record in self:
            record.cte40_xOutCat = record.tms_other_product_features

    cte40_xOutCat = fields.Char(compute="_compute_cte40_xOutCat")

    @api.depends("tms_weight", "tms_volume", "tms_units", "tms_units_description")
    def _compute_cte40_infQ(self):
        for record in self:
            cargo_info_vals = [
                {
                    "cte40_cUnid": "01",
                    "cte40_tpMed": "Peso Bruto",
                    "cte40_qCarga": record.tms_weight,
                },
                {
                    "cte40_cUnid": "01",
                    "cte40_tpMed": "Peso Base Calculado",
                    "cte40_qCarga": record.tms_weight,
                },
                {
                    "cte40_cUnid": "01",
                    "cte40_tpMed": "Peso Aferido",
                    "cte40_qCarga": record.tms_weight,
                },
                {
                    "cte40_cUnid": "00",
                    "cte40_tpMed": "Cubagem",
                    "cte40_qCarga": record.tms_volume,
                },
                {
                    "cte40_cUnid": "03",
                    "cte40_tpMed": "Unidade"
                    if record.tms_units_description == "UN"
                    else record.tms_units_description,
                    "cte40_qCarga": record.tms_units,
                },
            ]

            record.cte40_infQ = self.env["l10n_br_cte.cargo.quantity.infos"].create(
                cargo_info_vals
            )
