# © 2012 KMEE INFORMATICA LTDA
#   @author Luis Felipe Mileo <mileo@kmee.com.br>
#   @author Daniel Sadamo <daniel.sadamo@kmee.com.br>
#   @author Fernando Marcato <fernando.marcato@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import fields, models


class AccountPaymentLineCreate(models.TransientModel):
    _inherit = "account.payment.line.create"

    allow_error = fields.Boolean(
        string="Permitir linhas com erro na exportação, "
        "já incluidas em outras ordens",
    )

    allow_rejected = fields.Boolean(
        string="Permitir linhas com retorno rejeitado",
    )
