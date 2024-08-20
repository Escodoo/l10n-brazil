# Copyright (C) 2009 - TODAY Renato Lima - Akretion
# Copyright (C) 2019 - TODAY Raphaël Valyi - Akretion
# Copyright (C) 2024 - TODAY Ravi do Valle Luz - XippTech
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from contextlib import contextmanager

from odoo import _, api, fields, models

from .account_move import InheritsCheckMuteLogger

from odoo.addons.l10n_br_fiscal.constants.fiscal import FINAL_CUSTOMER_NO

# These fields have the same name in account.move.line
# and l10n_br_fiscal.document.line. So they wouldn't get updated
# by the _inherits system. An alternative would be changing their name
# in l10n_br_fiscal but that would make the code unreadable and fiscal mixin
# methods would fail to do what we expect from them in the Odoo objects
# where they are injected.
# Fields that are related in l10n_br_fiscal.document.line like partner_id or company_id
# don't need to be written through the account.move.line write.
SHADOWED_FIELDS = [
    "name",
    "product_id",
    "quantity",
    "price_unit",
]

ACCOUNTING_FIELDS = ("debit", "credit", "amount_currency")
BUSINESS_FIELDS = ("price_unit", "quantity", "discount", "tax_ids")


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = [_name, "l10n_br_fiscal.document.line.mixin.methods"]
    _inherits = {"l10n_br_fiscal.document.line": "fiscal_document_line_id"}

    fiscal_document_line_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document.line",
        string="Fiscal Document Line",
        copy=False,
        ondelete="cascade",
    )

    document_type_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document.type",
        related="move_id.document_type_id",
    )

    tax_framework = fields.Selection(
        related="move_id.company_id.tax_framework",
        string="Tax Framework",
    )

    cfop_destination = fields.Selection(
        related="cfop_id.destination", string="CFOP Destination"
    )

    partner_company_type = fields.Selection(related="partner_id.company_type")

    ind_final = fields.Selection(related="move_id.ind_final")

    fiscal_genre_code = fields.Char(
        related="fiscal_genre_id.code",
        string="Fiscal Product Genre Code",
    )

    # The following fields belong to the fiscal document line mixin
    # but they are redefined here to ensure they are recomputed in the
    # account.move.line views.
    icms_cst_code = fields.Char(
        related="icms_cst_id.code",
        string="ICMS CST Code",
    )

    ipi_cst_code = fields.Char(
        related="ipi_cst_id.code",
        string="IPI CST Code",
    )

    cofins_cst_code = fields.Char(
        related="cofins_cst_id.code",
        string="COFINS CST Code",
    )

    cofinsst_cst_code = fields.Char(
        related="cofinsst_cst_id.code",
        string="COFINS ST CST Code",
    )

    pis_cst_code = fields.Char(
        related="pis_cst_id.code",
        string="PIS CST Code",
    )

    pisst_cst_code = fields.Char(
        related="pisst_cst_id.code",
        string="PIS ST CST Code",
    )

    partner_is_public_entity = fields.Boolean(related="partner_id.is_public_entity")

    allow_csll_irpj = fields.Boolean(
        compute="_compute_allow_csll_irpj",
    )

    wh_move_line_id = fields.Many2one(
        comodel_name="account.move.line",
        string="WH Account Move Line",
        ondelete="restrict",
    )

    discount = fields.Float(
        compute="_compute_discounts",
        store=True,
    )

    # These fields are already inherited by _inherits, but there is some limitation of
    # the ORM that the values of these fields are zeroed when called by onchange. This
    # limitation directly affects the _get_amount_credit_debit method.
    amount_untaxed = fields.Monetary(compute="_compute_amounts")

    amount_total = fields.Monetary(compute="_compute_amounts")

    @api.depends(
        "quantity",
        "price_unit",
        "discount_value",
    )
    def _compute_discounts(self):
        for line in self:
            line.discount = 100 * line.discount_value / (
                line.quantity * line.price_unit or 1
            )

    @api.model
    def _inherits_check(self):
        """
        Overriden to avoid the super method to set the fiscal_document_line_id
        field as required.
        """
        with InheritsCheckMuteLogger("odoo.models"):  # mute spurious warnings
            res = super()._inherits_check()
        self._fields["fiscal_document_line_id"].required = False  
        return res

    @api.model
    def _get_optional_delegation_inherit_fields(self):
        return (
            super()._get_optional_delegation_inherit_fields()
            | set(["fiscal_document_line_id"])
        )

    @api.model
    def _shadowed_fields(self):
        """Return the list of shadowed fields that are synchronized
        from account.move.line."""
        return list(SHADOWED_FIELDS)

    @api.model
    def _inject_shadowed_fields(self, vals_list):
        for vals in vals_list:
            for field in self._shadowed_fields():
                if field in vals:
                    vals["fiscal_%s" % (field,)] = vals[field]
    
    def _compute_product_price(self):
        if not self.ensure_one().fiscal_operation_id:
            self._compute_price_unit()
        else:
            super()._compute_product_price()

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            move_id = self.env["account.move"].browse(values["move_id"])
            fiscal_doc_id = move_id.fiscal_document_id.id

            if not fiscal_doc_id or values.get("display_type") in ("payment_term", "tax"):
                continue

            values.update(
                self._update_fiscal_quantity(
                    values.get("product_id"),
                    values.get("price_unit"),
                    values.get("quantity"),
                    values.get("product_uom_id"),
                    values.get("uot_id"),
                )
            )
            values["uom_id"] = values.get("product_uom_id")
            values["document_id"] = fiscal_doc_id  # pass through the _inherits system

        self._inject_shadowed_fields(vals_list)
        recs = super(
            AccountMoveLine, self.with_context(create_from_move_line=True)
        ).create(vals_list)

        # Unfortunately when creating several aml there is no way to selectively avoid
        # the creation of l10n_br_fiscal.document.line as it would mess the association
        # of the remaining fiscal document lines with their proper aml. That's why we
        # remove the useless fiscal document lines here.
        recs.filtered(
            lambda r: (
                not r.move_id.fiscal_document_id 
                or r.display_type in ("payment_term", "tax")
            )
        ).fiscal_document_line_id.unlink()

        return recs

    def unlink(self):
        to_unlink = self.exists().fiscal_document_line_id
        result = super().unlink()
        to_unlink.unlink()

        return result

    @contextmanager
    def _sync_invoice(self, container):
        """
        Almost the same as the super method from the account module.
        Overriden only to change one line where country_id.code is compared with "BR"
        """
        if container["records"].env.context.get("skip_invoice_line_sync"):
            yield
            return  # avoid infinite recursion

        def existing():
            return {
                line: {
                    "amount_currency": line.currency_id.round(line.amount_currency),
                    "balance": line.company_id.currency_id.round(line.balance),
                    "currency_rate": line.currency_rate,
                    "price_subtotal": line.currency_id.round(line.price_subtotal),
                    "move_type": line.move_id.move_type,
                }
                for line in container["records"]
                .with_context(
                    skip_invoice_line_sync=True,
                )
                .filtered(lambda l: l.move_id.is_invoice(True))
            }

        def changed(fname):
            return line not in before or before[line][fname] != after[line][fname]

        before = existing()
        yield
        after = existing()
        for line in after:
            if (
                line.display_type == "product"
                and (not changed("amount_currency") or line not in before)
            ):
                amount_currency = line.move_id.direction_sign * line.currency_id.round(
                    line._get_balance_unsigned_for_invoice_type(
                        default=line.price_subtotal
                    )
                    # CHANGED
                )
                if line.amount_currency != amount_currency or line not in before:
                    line.amount_currency = amount_currency
                if line.currency_id == line.company_id.currency_id:
                    line.balance = amount_currency

        after = existing()
        for line in after:
            if (
                changed("amount_currency")
                or changed("currency_rate")
                or changed("move_type")
            ) and (not changed("balance") or (line not in before and not line.balance)):
                balance = line.company_id.currency_id.round(
                    line.amount_currency / line.currency_rate
                )
                line.balance = balance
        # Since this method is called during the sync, inside of `create`/`write`,
        # these fields
        # already have been computed and marked as so. But this method should
        # re-trigger it since
        # it changes the dependencies.
        self.env.add_to_compute(self._fields["debit"], container["records"])
        self.env.add_to_compute(self._fields["credit"], container["records"])

    @api.depends("icms_relief_value", "freight_value", "other_value", "insurance_value")
    def _compute_totals(self):
        """
        Overriden to pass all the Brazilian parameters we need
        to the account.tax#compute_all method.
        """
        result = super()._compute_totals()
        if not self.move_id.fiscal_operation_id:
            return result

        for line in self:
            if line.display_type != "product":
                continue  # handled in super method

            line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))

            if line.tax_ids:
                taxes_res = line.tax_ids._origin.with_context(
                    taxes_compute_origin_document_line_mixin=line,
                ).compute_all(
                    line_discount_price_unit,
                    currency=line.currency_id,
                    quantity=line.quantity,
                    product=line.product_id,
                    partner=line.partner_id,
                    is_refund=line.move_type in ("out_refund", "in_refund"),
                    handle_price_include=True,
                )

                line.price_subtotal = taxes_res["total_excluded"]
                line.price_total = taxes_res["total_included"]

            line.price_total += line._get_extras_amount()
        return result

    @api.depends()
    def _compute_all_tax(self):
        """
        Overriden to pass all the extra Brazilian parameters we need
        to the account.tax#compute_all method.
        """
        with_fiscal_op = self.filtered("move_id.fiscal_operation_id")
        super(AccountMoveLine, self - with_fiscal_op)._compute_all_tax()
        for rec in with_fiscal_op:
            super(
                AccountMoveLine, 
                rec.with_context(
                    taxes_compute_origin_document_line_mixin=rec,
                )
            )._compute_all_tax()

    @api.onchange("fiscal_document_line_id")
    def _onchange_fiscal_document_line_id(self):
        if self.fiscal_document_line_id:
            for field in self._shadowed_fields():
                self[field] = self.fiscal_document_line_id[field]
            # override the default product uom (set by the onchange):
            self.product_uom_id = self.fiscal_document_line_id.uom_id.id

    @api.onchange("fiscal_tax_ids")
    def _onchange_fiscal_tax_ids(self):
        """Ao alterar o campo fiscal_tax_ids que contém os impostos fiscais,
        são atualizados os impostos contábeis relacionados"""
        result = super()._onchange_fiscal_tax_ids()

        self.tax_ids = self._get_computed_taxes()

        return result
    
    def _get_computed_taxes(self):
        if not self.fiscal_operation_id:
            return super()._get_computed_taxes()
        user_type = (
            "sale" 
            if self.move_id.is_sale_document(include_receipts=True) 
            else "purchase"
        )
        return self.fiscal_tax_ids.account_taxes(
            user_type=user_type, fiscal_operation=self.fiscal_operation_id
        )

    def _get_balance_unsigned_for_invoice_type(self, default=None):
        self.ensure_one()
        if self._get_is_void_amount():
            return 0
        if not (fiscal_op := self.move_id.fiscal_operation_id):
            return default
        # Com certeza tem uma forma mais coesa de computar o balance
        # do que essa. É possível que a forma feita aqui seja
        # um bug para certas situações.
        amount_currency = self.amount_total + self.amount_tax_withholding
        if fiscal_op.deductible_taxes:
            return amount_currency 
        return (
            amount_currency 
            + self.amount_tax_withholding
            - self.amount_tax_included 
            - self.amount_tax_not_included
        )
    
    def _get_is_void_amount(self):
        return self.cfop_id and not self.cfop_id.finance_move
    
    def _get_extras_amount(self):
        return (
            self.freight_value
            + self.other_value
            + self.insurance_value
            - self.icms_relief_value
        )