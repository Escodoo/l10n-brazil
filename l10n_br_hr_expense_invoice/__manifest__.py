# Copyright 2021 - TODAY, Escodoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'L10n Br Hr Expense Invoice',
    'summary': """
        Localização módulo hr_expense_invoice""",
    'version': '12.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Escodoo,Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/l10n-brazil',
    'depends': [
        'l10n_br_account',
        'hr_expense_invoice',
    ],
    'data': [
        'data/company.xml',
        'views/res_company.xml',
        # 'views/hr_expense.xml',
    ],
    'demo': [
        'demo/res_company.xml',
    ],
}
