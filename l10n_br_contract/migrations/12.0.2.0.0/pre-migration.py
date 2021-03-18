# Copyright (C) 2021 - TODAY Marcel Savegnago - Escodoo (https://www.escodoo.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade

_columns_rename = {
    'res_company': [
        ('contract_fiscal_operation_id', 'contract_sale_fiscal_operation_id')],
}


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    if openupgrade.column_exists(env.cr, 'res_company', 'contract_fiscal_operation_id'):
        openupgrade.rename_columns(env.cr, _columns_rename)
