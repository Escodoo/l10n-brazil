# Copyright 2020 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from erpbrasil.base import misc
from lxml import etree

from odoo import api, fields, models


class DocumentLine(models.Model):
    _inherit = "l10n_br_fiscal.document.line"

    fiscal_deductions_value = fields.Monetary(
        string="Fiscal Deductions",
        default=0.00,
    )
    other_retentions_value = fields.Monetary(
        string="Other Retentions",
        default=0.00,
    )

    cnae_main_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.cnae",
        related="company_id.cnae_main_id",
        string="Main CNAE",
    )

    cnae_secondary_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.cnae",
        related="company_id.cnae_secondary_ids",
        string="Secondary CNAE",
    )

    cnae_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.cnae",
        string="CNAE Code",
        domain="['|', "
        "('id', 'in', cnae_secondary_ids), "
        "('id', '=', cnae_main_id)]",
    )

    @api.onchange("product_id")
    def _onchange_product_id_fiscal(self):
        super(DocumentLine, self)._onchange_product_id_fiscal()
        if self.product_id and self.product_id.fiscal_deductions_value:
            self.fiscal_deductions_value = self.product_id.fiscal_deductions_value

    def _compute_taxes(self, taxes, cst=None):
        discount_value = self.discount_value
        self.discount_value += self.fiscal_deductions_value
        res = super(DocumentLine, self)._compute_taxes(taxes, cst)
        self.discount_value = discount_value
        return res

    @api.model
    def fields_view_get(
        self, view_id=None, view_type="form", toolbar=False, submenu=False
    ):
        model_view = super(DocumentLine, self).fields_view_get(
            view_id, view_type, toolbar, submenu
        )

        if view_type == "form":
            try:
                doc = etree.fromstring(model_view.get("arch"))
                field = doc.xpath("//field[@name='issqn_wh_value']")[0]
                parent = field.getparent()
                parent.insert(
                    parent.index(field) + 1,
                    etree.XML('<field name="other_retentions_value"/>'),
                )

                model_view["arch"] = etree.tostring(doc, encoding="unicode")
            except Exception:
                return model_view

        View = self.env["ir.ui.view"]
        # Override context for postprocessing
        if view_id and model_view.get("base_model", self._name) != self._name:
            View = View.with_context(base_model_name=model_view["base_model"])

        # Apply post processing, groups and modifiers etc...
        xarch, xfields = View.postprocess_and_fields(
            self._name, etree.fromstring(model_view["arch"]), view_id
        )
        model_view["arch"] = xarch
        model_view["fields"] = xfields
        return model_view

    def prepare_line_servico(self):
        valor_servicos = 0
        valor_deducoes = 0
        valor_pis = 0
        valor_pis_retido = 0
        valor_cofins = 0
        valor_cofins_retido = 0
        valor_inss = 0
        valor_inss_retido = 0
        valor_ir = 0
        valor_ir_retido = 0
        valor_csll = 0
        valor_csll_retido = 0
        valor_iss = 0
        valor_iss_retido = 0
        outras_retencoes = 0
        base_calculo = 0
        valor_liquido_nfse = 0
        valor_desconto_incondicionado = 0

        for rec in self:
            valor_servicos += rec.fiscal_price
            valor_deducoes += rec.fiscal_deductions_value
            valor_pis += round(rec.pis_value, 2) or round(rec.pis_wh_value, 2)
            valor_pis_retido += round(rec.pis_wh_value, 2)
            valor_cofins += round(rec.cofins_value, 2) or round(rec.cofins_wh_value, 2)
            valor_cofins_retido += round(rec.cofins_wh_value, 2)
            valor_inss += round(rec.inss_value, 2) or round(rec.inss_wh_value, 2)
            valor_inss_retido += round(rec.inss_wh_value, 2)
            valor_ir += round(rec.irpj_value, 2) or round(rec.irpj_wh_value, 2)
            valor_ir_retido += round(rec.irpj_wh_value, 2)
            valor_csll += round(rec.csll_value, 2) or round(rec.csll_wh_value, 2)
            valor_csll_retido += round(rec.csll_wh_value, 2)
            valor_iss += round(rec.issqn_value, 2)
            valor_iss_retido += round(rec.issqn_wh_value, 2)
            outras_retencoes += rec.other_retentions_value
            base_calculo += rec.issqn_base or rec.issqn_wh_base
            valor_liquido_nfse += round(rec.amount_taxed, 2)
            valor_desconto_incondicionado += round(rec.discount_value, 2)

        return {
            "valor_servicos": valor_servicos,
            "valor_deducoes": valor_deducoes,
            "valor_pis": round(valor_pis, 2) or round(valor_pis_retido, 2),
            "valor_pis_retido": round(valor_pis_retido, 2),
            "valor_cofins": round(valor_cofins, 2) or round(valor_cofins_retido, 2),
            "valor_cofins_retido": round(valor_cofins_retido, 2),
            "valor_inss": round(valor_inss, 2) or round(valor_inss_retido, 2),
            "valor_inss_retido": round(valor_inss_retido, 2),
            "valor_ir": round(valor_ir, 2) or round(valor_ir_retido, 2),
            "valor_ir_retido": round(valor_ir_retido, 2),
            "valor_csll": round(valor_csll, 2) or round(valor_csll_retido, 2),
            "valor_csll_retido": round(valor_csll_retido, 2),
            "iss_retido": "1" if self[0].issqn_wh_value else "2",
            "valor_iss": round(valor_iss, 2),
            "valor_iss_retido": round(valor_iss_retido, 2),
            "outras_retencoes": round(outras_retencoes, 2),
            "base_calculo": round(base_calculo, 2),
            "aliquota": (self[0].issqn_percent / 100) or (self[0].issqn_wh_percent / 100),
            "valor_liquido_nfse": round(valor_liquido_nfse, 2),
            "item_lista_servico": self[0].service_type_id.code
            and self[0].service_type_id.code.replace(".", ""),
            "codigo_tributacao_municipio": self[0].city_taxation_code_id.code or "",
            "discriminacao": str(self[0].name[:2000] or ""),
            "codigo_cnae": misc.punctuation_rm(self[0].cnae_id.code) or None,
            "valor_desconto_incondicionado" : round(valor_desconto_incondicionado, 2),
        }
