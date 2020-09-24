# Copyright 2020 - TODAY, Marcel Savegnago - Escodoo <https://www.escodoo.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade


# def rename_wizards(cr):
#     if openupgrade.table_exists(cr, 'l10n_br_account_tax_template'):
#         openupgrade.rename_tables(cr, [(
#             'l10n_br_account_tax_template',
#             'account_tax_template'),
#         ])
#         openupgrade.rename_models(cr, [(
#             'l10n_br_account.tax.template',
#             'account.tax.template'),
#         ])
#
#
# @openupgrade.migrate()
# def migrate(env, version):
#     rename_wizards(env.cr)
