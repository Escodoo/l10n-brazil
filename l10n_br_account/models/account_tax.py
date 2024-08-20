# Copyright (C) 2009 - TODAY Renato Lima - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import Command, api, fields, models

from odoo.addons.l10n_br_fiscal.constants.fiscal import FINAL_CUSTOMER_NO


class AccountTax(models.Model):
    _inherit = "account.tax"

    fiscal_tax_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.tax",
        relation="fiscal_account_tax_rel",
        column1="account_tax_id",
        column2="fiscal_tax_id",
        string="Fiscal Taxes",
    )

    def compute_all(
        self,
        price_unit,
        currency=None,
        quantity=1.0,
        product=None,
        partner=None,
        is_refund=False,
        handle_price_include=True,
        include_caba_tags=False,
        fixed_multiplicator=1,
    ):
        """Returns all information required to apply taxes
            (in self + their children in case of a tax goup).
            We consider the sequence of the parent for group of taxes.
                Eg. considering letters as taxes and alphabetic order
                as sequence :
                [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]
        RETURN: {
            'total_excluded': 0.0,    # Total without taxes
            'total_included': 0.0,    # Total with taxes
            'taxes': [{               # One dict for each tax in self
                                      # and their children
                'id': int,
                'name': str,
                'amount': float,
                'sequence': int,
                'account_id': int,
                'refund_account_id': int,
                'analytic': boolean,
            }]
        }"""

        taxes_results = super().compute_all(
            price_unit,
            currency,
            quantity,
            product,
            partner,
            is_refund,
            handle_price_include,
            include_caba_tags,
            fixed_multiplicator,
        )

        line = self._context.get(
            "taxes_compute_origin_document_line_mixin", 
            self.env["l10n_br_fiscal.document.line.mixin"]
        )
        # line may be any model with fiscal properties, 
        # like account.move.line, sale.order.line, etc
        if "fiscal_tax_ids" not in line._fields:
            return taxes_results
        product = product or self.env["product.product"]

        if len(self) == 0:
            company = self.env.company
            if self.env.context.get("default_company_id") or self.env.context.get(
                "allowed_company_ids"
            ):
                company = self.env["res.company"].browse(
                    self.env.context.get("default_company_id")
                    or self.env.context.get("allowed_company_ids")[0]
                )
        else:
            company = self[0].company_id

        extra_vals = dict(
            line._get_compute_taxes_extra_kwargs(product, quantity, price_unit),
            **line._get_br_manual_tax_vals(),
        )
        fiscal_taxes_results = line.fiscal_tax_ids.compute_taxes(
            company=company,
            partner=partner,
            product=product,
            price_unit=price_unit,
            quantity=quantity,
            uom_id=product.uom_id,
            **extra_vals,
        )

        taxes_results["amount_tax_included"] = fiscal_taxes_results["amount_included"]
        taxes_results["amount_tax_not_included"] = fiscal_taxes_results[
            "amount_not_included"
        ]
        taxes_results["amount_tax_withholding"] = fiscal_taxes_results[
            "amount_withholding"
        ]
        taxes_results["amount_estimate_tax"] = fiscal_taxes_results["estimate_tax"]

        account_taxes_by_domain = {}

        sign = -1 if fixed_multiplicator < 0 else 1

        for tax in self:
            tax_domain = tax.tax_group_id.fiscal_tax_group_id.tax_domain
            account_taxes_by_domain.update({tax.id: tax_domain})

        for account_tax in taxes_results["taxes"]:
            tax = self.filtered(lambda t: t.id == account_tax.get("id"))
            fiscal_tax = fiscal_taxes_results["taxes"].get(
                account_taxes_by_domain.get(tax.id)
            )

            account_tax.update(
                {
                    "tax_group_id": tax.tax_group_id.id,
                    "deductible": tax.deductible,
                }
            )

            tax_repartition_lines = (
                is_refund
                and tax.refund_repartition_line_ids
                or tax.invoice_repartition_line_ids
            ).filtered(lambda x: x.repartition_type == "tax")

            sum_repartition_factor = sum(tax_repartition_lines.mapped("factor"))

            if fiscal_tax:
                if fiscal_tax.get("base") < 0:
                    sign = -1
                    fiscal_tax["base"] = -fiscal_tax.get("base")

                if not fiscal_tax.get("tax_include") and not tax.deductible:
                    taxes_results["total_included"] += fiscal_tax.get("tax_value")

                tax_amount = fiscal_tax.get("tax_value", 0.0) * sum_repartition_factor
                tax_base = fiscal_tax.get("base") * sum_repartition_factor

                fiscal_group = tax.tax_group_id.fiscal_tax_group_id
                account_tax.update(
                    {
                        "id": account_tax.get("id"),
                        "name": fiscal_group.name,
                        "fiscal_name": fiscal_tax.get("name"),
                        "base": tax_base * sign,
                        "tax_include": fiscal_tax.get("tax_include"),
                        "amount": tax_amount * sign,
                        "fiscal_tax_id": fiscal_tax.get("fiscal_tax_id"),
                        "tax_withholding": fiscal_group.tax_withholding,
                    }
                )

        return taxes_results

    @api.model
    def _compute_taxes_for_single_line(self, base_line, **kwargs):
        line = base_line.get("record")
        base_line["extra_context"]["taxes_compute_origin_document_line_mixin"] = line
        return super()._compute_taxes_for_single_line(base_line, **kwargs)
