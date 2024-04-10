# Copyright 2024 - TODAY, Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Payment Asaas",
    "summary": """
        Payment Acquirer: Asaas Implementation""",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Escodoo, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-brazil",
    "depends": [
        "sale",  # Used sale order in currency validation
        "web_tour",
        "website_sale",
    ],
    "data": [
        "views/payment_asaas_templates.xml",
        "data/payment_acquirer_data.xml",
        "views/payment_acquirer.xml",
    ],
    "uninstall_hook": "uninstall_hook",
}
