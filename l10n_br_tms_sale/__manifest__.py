# Copyright 2024 - TODAY, Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "L10n Br Tms Sale",
    "summary": """
        Brazilian Localization TMS Sale""",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Escodoo,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-brazil",
    "depends": [
        "l10n_br_sale",
    ],
    "data": [
        "views/product_pricelist_item.xml",
        "views/sale_order_line.xml",
        "views/sale_order.xml",
    ],
    "demo": [
        "demo/product_product.xml",
        "demo/product_pricelist_item.xml",
    ],
}
