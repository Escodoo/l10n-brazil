# Copyright 2026 Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import models
from odoo.exceptions import ValidationError

from odoo.addons.l10n_br_fiscal.constants.fiscal import MODELO_FISCAL_NFSE

from ..constants.nfse_dfe import NFSE_ACCESS_KEY_SIZE


class L10nBrFiscalDocument(models.Model):
    _inherit = "l10n_br_fiscal.document"

    def _check_key(self):
        """Skip the 44-digit check for a national NFS-e key.

        ``ChaveEdoc`` only accepts the NF-e layout. A national NFS-e key has
        50 digits, so the duplicate search still runs and the check digit
        validation is left to the documents that use a 44-digit key.
        """
        nfse_docs = self.filtered(self._is_national_nfse_key)
        for record in nfse_docs:
            duplicates = self.search_count(
                [
                    ("id", "!=", record.id),
                    ("company_id", "=", record.company_id.id),
                    ("issuer", "=", record.issuer),
                    ("document_key", "=", record.document_key),
                    ("document_type_id.code", "=", MODELO_FISCAL_NFSE),
                    ("state", "!=", "cancelada"),
                ]
            )
            if duplicates:
                raise ValidationError(
                    self.env._(
                        "There is already a fiscal document with this key: %(doc_key)s",
                        doc_key=record.document_key,
                    )
                )
        others = self - nfse_docs
        if others:
            return super(L10nBrFiscalDocument, others)._check_key()
        return None

    def _is_national_nfse_key(self, record):
        digits = re.sub(r"\D", "", record.document_key or "")
        return bool(
            record.document_type_id
            and record.document_type_id.code == MODELO_FISCAL_NFSE
            and len(digits) == NFSE_ACCESS_KEY_SIZE
        )
