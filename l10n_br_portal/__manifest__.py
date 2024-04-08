# Copyright 2019 KMEE
# Copyright 2024 XippTech
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "L10n Br Portal",
    "summary": """
        Campos Brasileiros no Portal""",
    "version": "17.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Xipp Tech, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-brazil",
    "depends": [
        "portal",
        "l10n_br_zip",
    ],
    "demo": [
        "demo/res_users_demo.xml",
    ],
    "data": [
        "views/portal_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "l10n_br_portal/static/src/l10n_br_portal.js",
            "l10n_br_portal/static/lib/cleave/cleave.min.js",
        ],
        "web.assets_tests": [
            "l10n_br_portal/static/tests/**/*",
        ],
    },
    "auto_install": True,
}
