# Copyright 2017 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import models, _
from odoo.addons.queue_job.job import job

_logger = logging.getLogger(__name__)


class FiscalDocument(models.Model):
    _inherit = 'l10n_br_fiscal.document'

    @job
    def _send_document_job(self):
        for record in self:
            record._eletronic_document_send()

    def _document_send(self):
        no_electronic = self.filtered(lambda d: not d.document_electronic)
        no_electronic._no_eletronic_document_send()
        electronic = self - no_electronic

        send_now = electronic.filtered(
            lambda documento:
                documento.operacao_id.queue_document_send == 'send_now'
        )
        send_later = electronic - send_now

        if send_now:
            _logger.info(_('Enviando documento fiscal agora: %s',
                         send_now.ids))
            send_now._send_document_job()
        if send_later:
            _logger.info(_('Enviando documento fiscal depois: %s',
                         send_later.ids))
            send_later.with_delay()._send_document_job()
