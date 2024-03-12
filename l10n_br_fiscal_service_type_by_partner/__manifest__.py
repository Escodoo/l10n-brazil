# Copyright 2024 - TODAY, Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Brazilian Fiscal Service Type by Partner",
    "summary": """
        Brazilian Fiscal Service Type by Partner""",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Escodoo, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-brazil",
    "depends": ["l10n_br_fiscal"],
    "data": [
        "views/res_partner_view.xml",
        "views/service_type_view.xml",
        "security/ir.model.access.csv",
    ],
}
