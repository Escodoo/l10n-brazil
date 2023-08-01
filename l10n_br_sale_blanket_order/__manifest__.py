# Copyright 2023 - TODAY, Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Brazilian Localization Sale Blanket Order",
    "summary": """
        Brazilian Localization Sale Blanket Order""",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Escodoo,Odoo Community Association (OCA)",
    "maintainers": ["marcelsavegnago"],
    "website": "https://github.com/OCA/l10n-brazil",
    "depends": ["sale_blanket_order", "l10n_br_sale"],
    "data": [
        "wizards/sale_blanket_order_wizard.xml",
        "views/sale_blanket_order_line.xml",
        "views/sale_blanket_order.xml",
    ],
    "demo": [
        "demo/sale_blanket_order_line.xml",
        "demo/sale_blanket_order.xml",
    ],
}
