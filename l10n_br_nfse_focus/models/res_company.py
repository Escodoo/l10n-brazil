# Copyright 2023 - TODAY, KMEE INFORMATICA LTDA
# Copyright 2023 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    provedor_nfse = fields.Selection(
        selection_add=[
            ("focusnfe", "FocusNFe"),
        ]
    )

    focusnfe_production_token = fields.Char(
        string="FocusNFe Production Token",
    )

    focusnfe_homologation_token = fields.Char(
        string="FocusNFe Homologation Token",
    )

    def get_focusnfe_token(self):
        self.ensure_one()
        return (
            self.focusnfe_production_token
            if self.nfse_environment == "1"
            else self.focusnfe_homologation_token
        )
