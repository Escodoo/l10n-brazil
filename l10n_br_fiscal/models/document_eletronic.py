# Copyright (C) 2019  Renato Lima - Akretion
# Copyright (C) 2019  KMEE INFORMATICA LTDA
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..constants.fiscal import (
    DOCUMENT_ISSUER,
    DOCUMENT_ISSUER_COMPANY,
    PROCESSADOR_NENHUM,
    SITUACAO_EDOC_AUTORIZADA,
)


def filter_processador(record):
    if record.document_electronic and record.processador_edoc == PROCESSADOR_NENHUM:
        return True
    return False


class DocumentEletronic(models.AbstractModel):
    _name = "l10n_br_fiscal.document.electronic"
    _description = "Fiscal Eletronic Document"
    _inherit = "l10n_br_fiscal.document.workflow"

    issuer = fields.Selection(
        selection=DOCUMENT_ISSUER,
        default=DOCUMENT_ISSUER_COMPANY,
        required=True,
    )

    status_code = fields.Char(
        copy=False,
    )

    status_name = fields.Char(
        copy=False,
    )

    status_description = fields.Char(
        compute="_compute_status_description",
        copy=False,
    )

    # Authorization Event Related Fields
    authorization_event_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.event",
        string="Authorization Event",
        readonly=True,
        copy=False,
    )

    authorization_date = fields.Datetime(
        readonly=True,
        related="authorization_event_id.protocol_date",
    )

    authorization_protocol = fields.Char(
        related="authorization_event_id.protocol_number",
        readonly=True,
    )

    send_file_id = fields.Many2one(
        comodel_name="ir.attachment",
        related="authorization_event_id.file_request_id",
        string="Send Document File XML",
        ondelete="restrict",
        readonly=True,
    )

    authorization_file_id = fields.Many2one(
        comodel_name="ir.attachment",
        related="authorization_event_id.file_response_id",
        string="Authorization File XML",
        ondelete="restrict",
        readonly=True,
    )

    # Cancel Event Related Fields
    cancel_event_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.event",
        string="Cancel Event",
        copy=False,
    )

    cancel_date = fields.Datetime(
        readonly=True,
        related="cancel_event_id.protocol_date",
    )

    cancel_protocol_number = fields.Char(
        related="cancel_event_id.protocol_number",
        readonly=True,
    )

    cancel_file_id = fields.Many2one(
        comodel_name="ir.attachment",
        related="cancel_event_id.file_response_id",
        string="Cancel File XML",
        ondelete="restrict",
        readonly=True,
    )

    # Invalidate Event Related Fields
    invalidate_event_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.event",
        string="Invalidate Event",
        copy=False,
    )

    invalidate_date = fields.Datetime(
        readonly=True,
        related="invalidate_event_id.protocol_date",
    )

    invalidate_protocol_number = fields.Char(
        related="invalidate_event_id.protocol_number",
        readonly=True,
    )

    invalidate_file_id = fields.Many2one(
        comodel_name="ir.attachment",
        related="invalidate_event_id.file_response_id",
        string="Invalidate File XML",
        ondelete="restrict",
        readonly=True,
    )

    document_version = fields.Char(string="Version", default="4.00", readonly=True)

    is_edoc_printed = fields.Boolean(string="Is Printed?", readonly=True)

    file_report_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Document Report",
        ondelete="restrict",
        readonly=True,
        copy=False,
    )

    @api.depends("status_code", "status_name")
    def _compute_status_description(self):
        for record in self:
            if record.status_code:
                record.status_description = "{} - {}".format(
                    record.status_code or "",
                    record.status_name or "",
                )
            else:
                record.status_description = False

    def _eletronic_document_send(self):
        """Implement this method in your transmission module,
        to send the electronic document and use the method _change_state
        to update the state of the transmited document,

        def _eletronic_document_send(self):
            super()._document_send()
            for record in self.filtered(myfilter):
                Do your transmission stuff
                [...]
                Change the state of the document
        """
        for record in self.filtered(filter_processador):
            record._change_state(SITUACAO_EDOC_AUTORIZADA)

    def _document_send(self):
        no_electronic = self.filtered(
            lambda d: not d.document_electronic
            or not d.issuer == DOCUMENT_ISSUER_COMPANY
        )
        no_electronic._no_eletronic_document_send()
        electronic = self - no_electronic
        electronic._eletronic_document_send()

    def serialize(self):
        edocs = []
        self._serialize(edocs)
        return edocs

    def _serialize(self, edocs):
        return edocs

    def _target_new_tab(self, attachment_id):
        if attachment_id:
            return {
                "type": "ir.actions.act_url",
                "url": "/web/content/{id}/{nome}".format(
                    id=attachment_id.id, nome=attachment_id.name
                ),
                "target": "new",
            }

    def view_xml(self):
        self.ensure_one()
        xml_file = self.authorization_file_id or self.send_file_id
        if not xml_file:
            self._document_export()
            xml_file = self.authorization_file_id or self.send_file_id
        if not xml_file:
            raise UserError(_("No XML file generated!"))
        return self._target_new_tab(xml_file)

    def make_pdf(self):
        pass

    def view_pdf(self):
        self.ensure_one()
        if not self.file_report_id or not self.authorization_file_id:
            self.make_pdf()
        if not self.file_report_id:
            raise UserError(_("No PDF file generated!"))
        return self._target_new_tab(self.file_report_id)

    def _document_status(self):
        """Retorna o status do documento em texto e se necessário,
        atualiza o status do documento"""
        return

    def action_open_nfse_document_from_provider(self):
        self.ensure_one()
        nfse = self.document_number or '481'
        inscricao = self.company_inscr_mun
        verificacao = self.move_ids[0].verify_code or 'WZ4RQEZ2'
        url = "https://nfe.prefeitura.sp.gov.br/contribuinte/notaprint.aspx?nf=%s&inscricao=%s&verificacao=%s" % (nfse, inscricao, verificacao)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }
