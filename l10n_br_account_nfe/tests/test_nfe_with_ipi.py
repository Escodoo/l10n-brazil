from erpbrasil.assinatura import misc

from odoo.tests import tagged

from odoo.addons.l10n_br_account.tests.common import AccountMoveBRCommon


def prepare_fake_certificate_vals(
    valid=True,
    passwd="123456",
    issuer="EMISSOR A TESTE",
    country="BR",
    subject="CERTIFICADO VALIDO TESTE",
    cert_type="nf-e",
):
    return {
        "type": cert_type,
        "subtype": "a1",
        "password": passwd,
        "file": misc.create_fake_certificate_file(
            valid, passwd, issuer, country, subject
        ),
    }


@tagged("post_install", "-at_install")
class TestAccountAccount(AccountMoveBRCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref)

        cls.env.user.groups_id |= cls.env.ref("l10n_br_nfe.group_manager")

        cls.move_out_venda = cls.init_invoice(
            move_type="out_invoice",
            products=[cls.product_b],  # Product with IPI
            document_type=cls.env.ref("l10n_br_fiscal.document_55"),
            document_serie_id=cls.empresa_lc_document_55_serie_1,
            fiscal_operation=cls.env.ref("l10n_br_fiscal.fo_venda"),
            fiscal_operation_lines=[cls.env.ref("l10n_br_fiscal.fo_venda_venda")],
            post=True,
        )

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        l10n_br_fiscal_certificate_id = cls.env["l10n_br_fiscal.certificate"]
        if company_name == "company_1_data":
            company_name = "empresa 1 Lucro Presumido"
            cnpj_cpf = "30.360.463/0001-25"
        else:
            company_name = "empresa 2 Lucro Presumido"
            cnpj_cpf = "18.751.708/0001-40"
        chart_template = cls.env.ref("l10n_br_coa_generic.l10n_br_coa_generic_template")
        res = super().setup_company_data(
            company_name,
            chart_template,
            tax_framework="3",
            is_industry=True,
            industry_type="00",
            profit_calculation="presumed",
            ripi=True,
            piscofins_id=cls.env.ref("l10n_br_fiscal.tax_pis_cofins_columativo").id,
            icms_regulation_id=cls.env.ref("l10n_br_fiscal.tax_icms_regulation").id,
            cnae_main_id=cls.env.ref("l10n_br_fiscal.cnae_3101200").id,
            document_type_id=cls.env.ref("l10n_br_fiscal.document_55").id,
            cnpj_cpf=cnpj_cpf,
            certificate_nfe_id=l10n_br_fiscal_certificate_id.sudo()
            .create(prepare_fake_certificate_vals())
            .id,
            **kwargs
        )
        res["company"].partner_id.state_id = cls.env.ref("base.state_br_sp").id
        chart_template.load_fiscal_taxes()
        return res

    def test_nfe_with_ipi(self):
        self.assertEqual(
            self.move_out_venda.invoice_line_ids[0].nfe40_vProd,
            1000.00,
        )
        self.assertEqual(self.move_out_venda.nfe40_vProd, 1000.00)
