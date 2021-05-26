# Copyright 2017 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SubsequentOperation(models.Model):
    _inherit = 'l10n_br_fiscal.subsequent.operation'

    gerar_documento = fields.Selection(
        selection=[
            ('now', 'Enviar Imediatamente'),
            ('with_delay', 'Enviar Depois'),
        ],
        string='Gerar Documento',
        default='now',
        required=True,
    )
