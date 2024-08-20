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

    @api.onchange("product_id")
    def _onchange_product_id_fiscal(self):
        result = super()._onchange_product_id_fiscal()
        if self.product_id and self.product_id.fiscal_deductions_value:
            self.fiscal_deductions_value = self.product_id.fiscal_deductions_value
        return result

    def _compute_taxes(self, taxes, cst=None):
        discount_value = self.discount_value
        self.discount_value += self.fiscal_deductions_value
        res = super()._compute_taxes(taxes, cst)
        self.discount_value = discount_value
        return res

    def inject_fiscal_fields(
        self, 
        view_arch, 
        view_ref="l10n_br_fiscal.document_fiscal_line_mixin_form", 
        xpath_mappings=None
    ):
        for field in view_arch.xpath("//field[@name='issqn_wh_value']"):
            parent = field.getparent()
            parent.insert(
                parent.index(field) + 1,
                etree.XML('<field name="other_retentions_value"/>'),
            )
        return super().inject_fiscal_fields(view_arch, view_ref, xpath_mappings)

    def prepare_line_servico(self):
        return {
            "valor_servicos": round(self.price_gross, 2),
            "valor_deducoes": round(self.fiscal_deductions_value, 2),
            "valor_pis": round(self.pis_value, 2) or round(self.pis_wh_value, 2),
            "valor_pis_retido": round(self.pis_wh_value, 2),
            "valor_cofins": round(self.cofins_value, 2)
            or round(self.cofins_wh_value, 2),
            "valor_cofins_retido": round(self.cofins_wh_value, 2),
            "valor_inss": round(self.inss_value, 2) or round(self.inss_wh_value, 2),
            "valor_inss_retido": round(self.inss_wh_value, 2),
            "valor_ir": round(self.irpj_value, 2) or round(self.irpj_wh_value, 2),
            "valor_ir_retido": round(self.irpj_wh_value, 2),
            "valor_csll": round(self.csll_value, 2) or round(self.csll_wh_value, 2),
            "valor_csll_retido": round(self.csll_wh_value, 2),
            "iss_retido": "1" if self.issqn_wh_percent else "2",
            "valor_iss": round(self.issqn_value, 2),
            "valor_iss_retido": round(self.issqn_wh_value, 2),
            "outras_retencoes": round(self.other_retentions_value, 2),
            "base_calculo": round(self.issqn_base, 2) or round(self.issqn_wh_base, 2),
            "aliquota": (self.issqn_percent / 100) or (self.issqn_wh_percent / 100),
            "valor_liquido_nfse": round(self.amount_taxed, 2),
            "item_lista_servico": self.service_type_id.code
            and self.service_type_id.code.replace(".", ""),
            "codigo_tributacao_municipio": self.city_taxation_code_id.code or "",
            "municipio_prestacao_servico": self.issqn_fg_city_id.ibge_code or "",
            "discriminacao": self.prepare_line_service_description(),
            "codigo_cnae": misc.punctuation_rm(self.cnae_id.code) or None,
            "valor_desconto_incondicionado": round(self.discount_value, 2),
        }

    def prepare_line_service_description(self):
        description = str(self.name[:2000] or "") + (
            "|%s|" % self.additional_data.replace("\n", "|")
            if self.additional_data
            else ""
        )
        return description
