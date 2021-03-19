# Copyright (C) 2021 - TODAY Marcel Savegnago - Escodoo (https://www.escodoo.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade

_column_renames = {
    'l10n_br_fiscal_operation_line': [
        ('contract_fiscal_operation_id', 'contract_sale_fiscal_operation_id')],}


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    openupgrade.rename_columns(env.cr, _column_renames)
