# Copyright (C) 2009 - TODAY Renato Lima - Akretion
# Copyright (C) 2019 - TODAY Raphaël Valyi - Akretion
# Copyright (C) 2020 - TODAY Luis Felipe Mileo - KMEE
# Copyright (C) 2024 - TODAY Ravi do Valle Luz - XippTech
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.tests.common import Form
from odoo.exceptions import UserError
from odoo.tools import mute_logger

from odoo.addons.l10n_br_fiscal.constants.fiscal import (
    DOCUMENT_ISSUER_COMPANY,
    DOCUMENT_ISSUER_PARTNER,
    FISCAL_IN_OUT_ALL,
    FISCAL_OUT,
    MODELO_FISCAL_NFE,
    SITUACAO_EDOC_AUTORIZADA,
    SITUACAO_EDOC_CANCELADA,
    SITUACAO_EDOC_EM_DIGITACAO,
)

MOVE_TO_OPERATION = {
    "out_invoice": "out",
    "in_invoice": "in",
    "out_refund": "in",
    "in_refund": "out",
    "out_receipt": "out",
    "in_receipt": "in",
}

REFUND_TO_OPERATION = {
    "out_invoice": "in",
    "in_invoice": "out",
    "out_refund": "out",
    "in_refund": "in",
}

FISCAL_TYPE_REFUND = {
    "out": ["purchase_refund", "in_return"],
    "in": ["sale_refund", "out_return"],
}

MOVE_TAX_USER_TYPE = {
    "out_invoice": "sale",
    "in_invoice": "purchase",
    "out_refund": "sale",
    "in_refund": "purchase",
}

SHADOWED_FIELDS = ["company_id", "currency_id", "user_id", "partner_id"]


class InheritsCheckMuteLogger(mute_logger):
    """
    Mute the Model#_inherits_check warning
    because the _inherits field is not required.
    """

    def filter(self, record):
        msg = record.getMessage()
        if "Field definition for _inherits reference" in msg:
            return 0
        return super().filter(record)


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = [
        _name,
        "l10n_br_fiscal.document.move.mixin",
    ]
    _inherits = {"l10n_br_fiscal.document": "fiscal_document_id"}
    _order = "date DESC, name DESC"

    document_electronic = fields.Boolean(
        related="document_type_id.electronic",
        string="Electronic?",
    )

    fiscal_document_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document",
        string="Fiscal Document",
        copy=False,
        ondelete="cascade",
    )

    fiscal_document_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.document",
        string="Fiscal Documents",
        compute="_compute_fiscal_document_ids",
        help="""In some rare cases (NFS-e, CT-e...) a single account.move
        may have several different fiscal documents related to its account.move.lines.
        """,
    )

    fiscal_operation_type = fields.Selection(
        selection=FISCAL_IN_OUT_ALL,
        string="Fiscal Operation Type",
        related=None,
        compute="_compute_fiscal_operation_type",
    )

    @api.constrains("fiscal_document_id", "document_type_id")
    def _check_fiscal_document_type(self):
        for rec in self:
            if rec.document_type_id and not rec.fiscal_document_id:
                raise UserError(
                    _(
                        "You cannot set a document type when the move has no Fiscal Document!"
                    )
                )

    @api.depends("line_ids.document_id", "invoice_line_ids.document_id")
    def _compute_fiscal_document_ids(self):
        for move in self:
            move.fiscal_document_ids = move.invoice_line_ids.document_id

    def _compute_fiscal_operation_type(self):
        for inv in self:
            if inv.is_entry():
                # if it is a Journal Entry there is nothing to do.
                inv.fiscal_operation_type = False
                continue
            if inv.fiscal_operation_id:
                inv.fiscal_operation_type = (
                    inv.fiscal_operation_id.fiscal_operation_type
                )
            else:
                inv.fiscal_operation_type = MOVE_TO_OPERATION[inv.move_type]
    
    def _get_lines_field_name(self):
        return "invoice_line_ids"

    @api.model
    def _inherits_check(self):
        """
        Overriden to avoid the super method to set the fiscal_document_id
        field as required.
        """
        with InheritsCheckMuteLogger("odoo.models"):  # mute spurious warnings
            res = super()._inherits_check()
        # unset the required = True assignement
        self._fields["fiscal_document_id"].required = False  
        return res

    @api.model
    def _get_optional_delegation_inherit_fields(self):
        return (
            super()._get_optional_delegation_inherit_fields()
            | set(["fiscal_document_id"])
        )

    @api.model
    def _shadowed_fields(self):
        """Return the list of shadowed fields that are synchronized
        from account.move."""
        return SHADOWED_FIELDS

    @api.model
    def _inject_shadowed_fields(self, vals_list):
        for vals in vals_list:
            for field in self._shadowed_fields():
                if field in vals:
                    vals["fiscal_%s" % (field,)] = vals[field]

    def ensure_one_doc(self):
        self.ensure_one()
        if len(self.fiscal_document_ids) > 1:
            raise UserError(
                _(
                    "More than 1 fiscal document!"
                    "You should open the fiscal view"
                    "and perform the action on each document!"
                )
            )

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if self.env.company.country_id.code != "BR":
            return arch, view
        if view_type == "form":
            view = self.env["ir.ui.view"]

            if view_id == self.env.ref("l10n_br_account.fiscal_invoice_form").id:
                invoice_line_form_id = self.env.ref(
                    "l10n_br_account.fiscal_invoice_line_form"
                ).id
                sub_form_node, _sub_view = self.env["account.move.line"]._get_view(
                    view_id=invoice_line_form_id, view_type="form"
                )
                self.env["account.move.line"].inject_fiscal_fields(sub_form_node)

                for original_sub_form_node in arch.xpath(
                    "//field[@name='invoice_line_ids']/form"
                ):
                    parent = original_sub_form_node.parent
                    parent.remove(original_sub_form_node)
                    parent.append(sub_form_node)

            else:
                for sub_form_node in arch.xpath(
                    "//field[@name='invoice_line_ids']/form"
                ):
                    self.env["account.move.line"].inject_fiscal_fields(sub_form_node)
                for sub_form_node in arch.xpath("//field[@name='line_ids']/tree"):
                    self.env["account.move.line"].inject_fiscal_fields(sub_form_node)

        return arch, view

    @api.depends(
        "line_ids.amount_untaxed",
        "line_ids.amount_tax",
        "ind_final",
    )
    def _compute_amount(self):
        fiscal_br_invoices = self.filtered(
            lambda m: (
                m.fiscal_operation_id
                and not m.is_entry()
            )
        )
        super(AccountMove, self - fiscal_br_invoices)._compute_amount()

        lines_to_update = fiscal_br_invoices.filtered(
            lambda m: m.is_invoice(include_receipts=True)
        ).line_ids.filtered(lambda r: r.display_type == "product")
        lines_to_update._update_fiscal_taxes()

        super(AccountMove, fiscal_br_invoices)._compute_amount()

        for move in fiscal_br_invoices:
            sign = -move.direction_sign
            inv_line_ids = move.line_ids.filtered(lambda l: (
                (
                    l.display_type == "product"
                    or l.display_type == "rounding" and not l.tax_repartition_line_id
                )
            ))
            get_sum_of = lambda f: sum(inv_line_ids.mapped(f))
        
            move.amount_untaxed = get_sum_of("amount_untaxed")
            move.amount_tax = get_sum_of("amount_tax")
            move.amount_untaxed_signed = sign * get_sum_of("amount_untaxed")
            move.amount_tax_signed = sign * get_sum_of("amount_tax")

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        move_type = self.env.context.get("default_move_type", "out_invoice")
        if not move_type == "entry":
            if move_type in MOVE_TO_OPERATION:
                defaults["fiscal_operation_type"] = MOVE_TO_OPERATION[move_type]
            if "fiscal_operation_type" not in defaults:
                pass
            elif defaults["fiscal_operation_type"] == FISCAL_OUT:
                defaults["issuer"] = DOCUMENT_ISSUER_COMPANY
            else:
                defaults["issuer"] = DOCUMENT_ISSUER_PARTNER
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        self._inject_shadowed_fields(vals_list)

        for vals in vals_list:
            if not vals.get("document_type_id"):
                vals["fiscal_document_id"] = False
        
        return super(AccountMove, self.with_context(create_from_move=True)).create(
            vals_list
        )

    def write(self, values):
        self._inject_shadowed_fields([values])
        result = super().write(values)
        return result

    def unlink(self):
        """Allow to delete draft or cancelled invoices"""
        unlink_moves = self.env["account.move"]
        unlink_documents = self.env["l10n_br_fiscal.document"]
        for move in self:
            if not move.exists():
                continue
            if move.fiscal_document_id and move.fiscal_document_id:
                unlink_documents |= move.fiscal_document_id
            unlink_moves |= move
        result = super(AccountMove, unlink_moves).unlink()
        unlink_documents.unlink()
        self.env.registry.clear_cache()
        return result

    @api.depends("fiscal_operation_id")
    def _compute_invoice_payment_term_id(self):
        super()._compute_invoice_payment_term_id()
        self.filtered("fiscal_operation_id").invoice_payment_term_id = False

    @api.depends("document_number")
    def _compute_needed_terms(self):
        """Compute the dynamic payment term lines of the journal entry.
        overwritten this method to change aml's field name.
        """
        super()._compute_needed_terms()
        for invoice in self:
            if not (
                invoice.is_invoice(True) 
                and invoice.fiscal_document_id
                and invoice.invoice_line_ids 
                and invoice.invoice_payment_term_id
            ):
                continue
            name = invoice.fiscal_document_id.with_context(
                fiscal_document_no_company=True
            )._get_document_name()
            length = len(invoice.needed_terms)
            for idx, (_, term_values) in enumerate(sorted(
                invoice.needed_terms.items(), 
                key=lambda i: i[0]["date_maturity"]
            )):
                term_values["name"] = f"{name}/{idx + 1}-{length}"

    @api.onchange("fiscal_operation_id")
    def _onchange_fiscal_operation_id(self):
        result = super()._onchange_fiscal_operation_id()
        if self.fiscal_operation_id and self.fiscal_operation_id.journal_id:
            self.journal_id = self.fiscal_operation_id.journal_id
        return result

    def open_fiscal_document(self):
        if self.env.context.get("move_type", "") == "out_invoice":
            xmlid = "l10n_br_account.fiscal_invoice_out_action"
        elif self.env.context.get("move_type", "") == "in_invoice":
            xmlid = "l10n_br_account.fiscal_invoice_in_action"
        else:
            xmlid = "l10n_br_account.fiscal_invoice_all_action"
        action = self.env["ir.actions.act_window"]._for_xml_id(xmlid)
        form_view = [(self.env.ref("l10n_br_account.fiscal_invoice_form").id, "form")]
        if "views" in action:
            action["views"] = form_view + [
                (state, view) for state, view in action["views"] if view != "form"
            ]
        else:
            action["views"] = form_view
        action["res_id"] = self.id
        return action

    def button_draft(self):
        docs_to_back = self.fiscal_document_id.browse()
        for rec in self.filtered("document_type_id"):
            if (
                rec.state_edoc == SITUACAO_EDOC_CANCELADA 
                and rec.issuer == DOCUMENT_ISSUER_COMPANY
            ):
                raise UserError(
                    _(
                        "You can't set this document number: {} to draft "
                        "because this document is cancelled in SEFAZ"
                    ).format(rec.document_number)
                )
            if rec.state_edoc != SITUACAO_EDOC_EM_DIGITACAO:
                docs_to_back |= rec.fiscal_document_id
        docs_to_back.action_document_back2draft()
        return super().button_draft()

    def action_document_send(self):
        self.filtered("document_type_id").fiscal_document_id.action_document_send()
        # FIXME: na migração para a v14 foi permitido o post antes do envio
        #  para destravar a migração, mas poderia ser cogitado de obrigar a
        #  transmissão antes do post novamente como na v12.
        # for invoice in invoices:
        #     invoice.move_id.post(invoice=invoice)

    def action_document_cancel(self):
        self.ensure_one()
        if self.document_type_id:
            self.ensure_one_doc()
            return self.fiscal_document_id.action_document_cancel()

    def action_document_correction(self):
        self.ensure_one()
        if self.document_type_id:
            self.ensure_one_doc()
            return self.fiscal_document_id.action_document_correction()

    def action_document_invalidate(self):
        self.ensure_one()
        if self.document_type_id:
            self.ensure_one_doc()
            return self.fiscal_document_id.action_document_invalidate()

    def action_document_back2draft(self):
        """Sets fiscal document to draft state and cancel and set to draft
        the related invoice for both documents remain equivalent state."""
        recs = self.filtered("document_type_id")
        recs.button_cancel()
        recs.button_draft()

    def action_post(self):
        res = super().action_post()

        for doc in self.filtered("document_type_id").fiscal_document_id:
            doc.action_document_confirm()
            doc.action_document_send()

        self.filtered(lambda r: (
            r.is_sale_document(include_receipts=True)
            and r.document_type_id
            and r.document_electronic
            and r.issuer == DOCUMENT_ISSUER_COMPANY
            and r.state_edoc != SITUACAO_EDOC_AUTORIZADA
        )).button_cancel()
        return res

    def view_xml(self):
        self.ensure_one_doc()
        return self.fiscal_document_id.view_xml()

    def view_pdf(self):
        self.ensure_one_doc()
        return self.fiscal_document_id.view_pdf()

    def action_send_email(self):
        self.ensure_one_doc()
        return self.fiscal_document_id.action_send_email()

    @api.onchange("document_type_id")
    def _onchange_document_type_id(self):
        # We need to ensure that invoices without a fiscal document have the
        # document_number blank, as all invoices without a fiscal document share this
        # same field, they are linked to the same dummy fiscal document.
        # Otherwise, in the tree view, this field will be displayed with the same value
        # for all these invoices.
        if not self.document_type_id:
            self.document_number = ""

    def _reverse_moves(self, default_values_list=None, cancel=False):
        new_moves = super()._reverse_moves(
            default_values_list=default_values_list, cancel=cancel
        )
        force_fiscal_operation_id = False
        if self.env.context.get("force_fiscal_operation_id"):
            force_fiscal_operation_id = self.env["l10n_br_fiscal.operation"].browse(
                self.env.context.get("force_fiscal_operation_id")
            )
        for record in new_moves.filtered(lambda i: i.document_type_id):
            if (
                not force_fiscal_operation_id
                and not record.fiscal_operation_id.return_fiscal_operation_id
            ):
                raise UserError(
                    _("""Document without Return Fiscal Operation! \n Force one!""")
                )

            record.fiscal_operation_id = (
                force_fiscal_operation_id
                or record.fiscal_operation_id.return_fiscal_operation_id
            )
            record._onchange_fiscal_operation_id()

            for line in record.invoice_line_ids:
                if (
                    not force_fiscal_operation_id
                    and not line.fiscal_operation_id.return_fiscal_operation_id
                ):
                    raise UserError(
                        _(
                            """Line without Return Fiscal Operation! \n
                            Please force one! \n%(name)s""",
                            name=line.name,
                        )
                    )

                line.fiscal_operation_id = (
                    force_fiscal_operation_id
                    or line.fiscal_operation_id.return_fiscal_operation_id
                )
                line._onchange_fiscal_operation_id()

            # Adds the related document to the NF-e.
            # this is required for correct xml validation
            if record.document_type_id and record.document_type_id.code in (
                MODELO_FISCAL_NFE
            ):
                record.fiscal_document_id._document_reference(
                    record.reversed_entry_id.fiscal_document_id
                )

        return new_moves

    def _prepare_wh_invoice(self, move_line):
        fiscal_group = move_line.tax_line_id.tax_group_id.fiscal_tax_group_id
        wh_date_invoice = move_line.move_id.date
        wh_due_invoice = wh_date_invoice.replace(day=fiscal_group.wh_due_day)
        return {
            "partner_id": fiscal_group.partner_id.id,
            "date": wh_date_invoice,
            "date_due": wh_due_invoice + relativedelta(months=1),
            "type": "in_invoice",
            "account_id": fiscal_group.partner_id.property_account_payable_id.id,
            "journal_id": move_line.journal_id.id,
            "origin": move_line.move_id.name,
            "line_ids": [(0, 0, self._prepare_wh_invoice_line(move_line))]
        }

    def _prepare_wh_invoice_line(self, move_line):
        return {
            "name": move_line.name,
            "quantity": move_line.quantity,
            "uom_id": move_line.product_uom_id,
            "price_unit": abs(move_line.balance),
            "account_id": move_line.account_id.id,
            "wh_move_line_id": move_line.id,
            "account_analytic_id": move_line.analytic_account_id.id,
        }

    def _finalize_invoices(self):
        # Esse método está desatualizado, nenhuma dos métodos chamados 
        # aqui existem pelo menos desde a v14
        for invoice in self:
            invoice.compute_taxes()
            for line in invoice.line_ids:
                # Use additional field helper function (for account extensions)
                line._set_additional_fields(invoice)
            invoice._onchange_cash_rounding()

    def create_wh_invoices(self):
        # Create Wh Invoice only for supplier invoice
        lines = self.filtered(
            lambda r: r.type == "in_invoice"
        ).line_ids.filtered(
            lambda r: r.tax_line_id.tax_group_id.fiscal_tax_group_id.tax_withholding
        )
        invoices = self.env["account.move"].create([
            self._prepare_wh_invoice(line) for line in lines
        ])

        invoices._finalize_invoices()
        invoices.action_post()

    def _withholding_validate(self):
        if not (lines := self.line_ids):
            return
        invoices = self.env["account.move.line"].search([
            ("wh_move_line_id", "in", lines.ids)
        ]).move_id
        invoices.filtered(lambda i: i.state == "open").button_cancel()
        invoices.filtered(lambda i: i.state == "cancel").button_draft()
        invoices.invalidate_recordset()
        invoices.filtered(lambda i: i.state == "draft").unlink()

    def button_cancel(self):
        for doc in self.filtered("document_type_id").fiscal_document_id:
            doc.action_document_cancel()
        # Esse método é responsavel por verificar se há alguma fatura de impostos
        # retidos associada a essa fatura e cancela-las também.
        self._withholding_validate()
        return super().button_cancel()

    # TODO: Por ora esta solução contorna o problema
    #  AttributeError: 'Boolean' object has no attribute 'depends_context'
    #  Este erro está relacionado com o campo active implementado via localização
    #  nos modelos account.move.line e l10n_br_fiscal.document.line
    #  Este problema começou após este commit:
    #  https://github.com/oca/ocb/commit/1dcd071b27779e7d6d8f536c7dce7002d27212ba
    def _get_integrity_hash_fields_and_subfields(self):
        return self._get_integrity_hash_fields() + [
            f"line_ids.{subfield}"
            for subfield in self.env["account.move.line"]._get_integrity_hash_fields()
        ]

    def button_import_fiscal_document(self):
        """
        Import move fields and invoice lines from
        the fiscal_document_id record if there is any new line
        to import.
        You can typically set fiscal_document_id to some l10n_br_fiscal.document
        record that was imported previously and import its lines into the
        current move.
        """
        for move in self:
            if move.state != "draft":
                raise UserError(_("Cannot import in non draft Account Move!"))
            elif (
                move.partner_id
                and move.partner_id != move.fiscal_document_id.partner_id
            ):
                raise UserError(_("Partner mismatch!"))
            elif (
                MOVE_TO_OPERATION[move.move_type]
                != move.fiscal_document_id.fiscal_operation_type
            ):
                raise UserError(_("Fiscal Operation Type mismatch!"))
            elif move.company_id != move.fiscal_document_id.company_id:
                raise UserError(_("Company mismatch!"))

            move_fiscal_lines = set(
                move.invoice_line_ids.mapped("fiscal_document_line_id")
            )
            fiscal_doc_lines = set(move.fiscal_document_id.fiscal_line_ids)
            if move_fiscal_lines == fiscal_doc_lines:
                raise UserError(_("No new Fiscal Document Line to import!"))

            self.import_fiscal_document(move.fiscal_document_id, move_id=move.id)

    @api.model
    def import_fiscal_document(
        self,
        fiscal_document,
        move_id=None,
        move_type="in_invoice",
    ):
        """
        Import the data from an existing fiscal document into a new
        invoice or into an existing invoice.
        First it transfers the "shadowed" fields and fill the other
        mandatory invoice fields.
        The account.move onchanges of these fields are properly
        triggered as if the invoice was filled manually.
        Then it creates each account.move.line and fill them using
        their fiscal_document_id onchange.
        """
        move = self.env["account.move"].browse(move_id)
        move_form = Form(
            move.with_context(
                default_move_type=move_type,
                account_predictive_bills_disable_prediction=True,
            )
        )
        if not move_id or not move.fiscal_document_id:
            move_form.invoice_date = fiscal_document.document_date
            move_form.date = fiscal_document.document_date
            for field in self._shadowed_fields():
                if field in ("company_id", "user_id"):  # (readonly fields)
                    continue
                if not move_form._view["fields"].get(field):
                    continue
                setattr(move_form, field, getattr(fiscal_document, field))
            move_form.document_type_id = fiscal_document.document_type_id
            move_form.fiscal_document_id = fiscal_document
            move_form.fiscal_operation_id = fiscal_document.fiscal_operation_id

        for line in fiscal_document.fiscal_line_ids:
            with move_form.invoice_line_ids.new() as line_form:
                line_form.cfop_id = (
                    line.cfop_id
                )  # required if we disable some fiscal tax updates
                line_form.fiscal_operation_id = self.fiscal_operation_id
                line_form.fiscal_document_line_id = line
        move_form.save()
        return move_form
