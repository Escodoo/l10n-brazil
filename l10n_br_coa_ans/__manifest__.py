# Copyright (C) 2022  Marcel Savegnago - Escodoo
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

{
    "name": "Plano de Contas ANS",
    "summary": "Plano de Contas Formato ANS segundo RN 528 04.2022",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Escodoo, " "Odoo Community Association (OCA)",
    "maintainers": ["marcelsavegnago"],
    "development_status": "Production/Stable",
    "website": "https://github.com/OCA/l10n-brazil",
    "version": "14.0.2.2.0",
    "depends": ["l10n_br_coa"],
    "data": [
        "data/l10n_br_coa_ans_template.xml",
        "data/account_type_data.xml",
        "data/account_group.xml",
        "data/account.account.template.csv",
        "data/l10n_br_coa.account.tax.group.account.template.csv",
        "data/l10n_br_coa_ans_template_post.xml",
    ],
    "post_init_hook": "post_init_hook",
}
