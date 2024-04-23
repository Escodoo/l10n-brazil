# Copyright 2020 KMEE
# Copyright 2024 XippTech
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("br_oca_generic")
    def _get_br_oca_generic_template_data(self):
        return {
            'name': _(
                'Plano de Contas Genérico para Empresas do Regime normal'
            ),
            'parent': 'br_oca',
            'use_anglo_saxon': True,
            'property_account_receivable_id': 'coa_generic_112101',
            'property_account_payable_id': 'coa_generic_211101',
            'property_account_expense_categ_id': 'coa_generic_511101',
            'property_account_income_categ_id': 'coa_generic_611101',
        }

    @template("br_oca_generic", "res.company")
    def _get_br_oca_generic_res_company(self):
        return {
            self.env.company.id: {
                'account_default_pos_receivable_account_id':
                    'coa_generic_112102',
            },
        }

    def _get_tax_group_accounts(self, template_code):
        """
            Default invoice/refund accounts by tax group
            Data previously populated
            l10n_br_coa.account.tax.group.account.template
            in <v17, when CoA template models was used

            [tax_group_id xmlid (pseudo)]: {
                ded_account_id: xmlid
                ded_refund_account_id: xmlid
                account_id: xmlid
                refund_account_id: xmlid
            }
        """
        if template_code != 'br_oca_generic':
            return super()._get_tax_group_accounts(template_code)
        return {
            'tax_group_icms': {
                'account_id': 'coa_generic_217103',
                'refund_account_id': 'coa_generic_114102',
                'ded_account_id': 'coa_generic_611203',
                'ded_refund_account_id': 'coa_generic_611223'
            },
            'tax_group_ipi': {
                'account_id': 'coa_generic_217102',
                'refund_account_id': 'coa_generic_114101',
                'ded_account_id': 'coa_generic_611208',
                'ded_refund_account_id': 'coa_generic_611228',
            },
            'tax_group_pis': {
                'account_id': 'coa_generic_217105',
                'refund_account_id': 'coa_generic_114101',
                'ded_account_id': 'coa_generic_611206',
                'ded_refund_account_id': 'coa_generic_611226',
            },
            'tax_group_cofins': {
                'account_id': 'coa_generic_217104',
                'refund_account_id': 'coa_generic_114101',
                'ded_account_id': 'coa_generic_611205',
                'ded_refund_account_id': 'coa_generic_611225',
            }
        }
