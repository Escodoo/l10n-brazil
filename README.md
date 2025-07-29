
[![Runboat](https://img.shields.io/badge/runboat-Try%20me-875A7B.png)](https://runboat.odoo-community.org/builds?repo=OCA/l10n-brazil&target_branch=16.0)
[![Pre-commit Status](https://github.com/OCA/l10n-brazil/actions/workflows/pre-commit.yml/badge.svg?branch=16.0)](https://github.com/OCA/l10n-brazil/actions/workflows/pre-commit.yml?query=branch%3A16.0)
[![Build Status](https://github.com/OCA/l10n-brazil/actions/workflows/test.yml/badge.svg?branch=16.0)](https://github.com/OCA/l10n-brazil/actions/workflows/test.yml?query=branch%3A16.0)
[![codecov](https://codecov.io/gh/OCA/l10n-brazil/branch/16.0/graph/badge.svg)](https://codecov.io/gh/OCA/l10n-brazil)
[![Translation Status](https://translation.odoo-community.org/widgets/l10n-brazil-16-0/-/svg-badge.svg)](https://translation.odoo-community.org/engage/l10n-brazil-16-0/?utm_source=widget)

<!-- /!\ do not modify above this line -->

# Odoo Brazilian Localization / Localização Brasileira do Odoo

A localização brasileira do Odoo, criada pela comunidade Open Source da Odoo Community Association (OCA), inclui um conjunto de módulos detalhados para atender às normas fiscais e legais do Brasil. Esta localização aprimora o Odoo com funcionalidades para:

- **Documentos fiscais:** Suporte abrangente a documentações conforme legislação nacional.
- **Tributos específicos:** Gestão de ICMS, IPI, ISS, PIS, COFINS, CSLL, IRPJ, e outros, incluindo substituição tributária e retenção de impostos.
- **Emissão de notas fiscais eletrônicas:** Compatível com NF-e, NFS-e e mais.
- **Integrações bancárias:** Ferramentas para importação de extratos OFX e geração de CNAB 240 e 400.

## Começando com a Localização

Instale o módulo `l10n_br_base` para configurar as bases da localização brasileira no Odoo. Adicione o `l10n_br_fiscal` para expandir a emissão e gestão de documentos fiscais eletrônicos.

## :arrow_forward: **Teste a Localização Agora!**

Não perca a chance de ver a localização em ação:

1. Clique no botão abaixo para iniciar um container no ambiente Runboat:

   [![Runboat](https://img.shields.io/badge/runboat-Try%20me-875A7B.png)](https://runboat.odoo-community.org/builds?repo=OCA/l10n-brazil&target_branch=16.0)

2. Aguarde até o container ficar disponível (indicador verde).
3. Clique em **Live** para acessar o Odoo.
4. Entre com `admin/admin`.
5. Escolha a empresa demo com o regime tributário de seu interesse, seja Simples Nacional ou Lucro Presumido, e explore um ambiente rico em detalhes e funcionalidades.

<!-- /!\ do not modify below this line -->

<!-- prettier-ignore-start -->

[//]: # (addons)

Available addons
----------------
addon | version | maintainers | summary
--- | --- | --- | ---
[l10n_br_account_due_list](l10n_br_account_due_list/) | 16.0.1.0.0 | [![renatonlima](https://github.com/renatonlima.png?size=30px)](https://github.com/renatonlima) [![rvalyi](https://github.com/rvalyi.png?size=30px)](https://github.com/rvalyi) | Brazilian Account Due List
[l10n_br_base](l10n_br_base/) | 16.0.1.5.1 | [![renatonlima](https://github.com/renatonlima.png?size=30px)](https://github.com/renatonlima) [![rvalyi](https://github.com/rvalyi.png?size=30px)](https://github.com/rvalyi) | Customization of base module for implementations in Brazil.
[l10n_br_coa](l10n_br_coa/) | 16.0.2.0.0 | [![renatonlima](https://github.com/renatonlima.png?size=30px)](https://github.com/renatonlima) [![mileo](https://github.com/mileo.png?size=30px)](https://github.com/mileo) | Base do Planos de Contas brasileiros
[l10n_br_coa_generic](l10n_br_coa_generic/) | 16.0.2.0.0 | [![mileo](https://github.com/mileo.png?size=30px)](https://github.com/mileo) | Plano de Contas para empresas do Regime normal (Micro e pequenas empresas)
[l10n_br_coa_simple](l10n_br_coa_simple/) | 16.0.1.3.0 | [![renatonlima](https://github.com/renatonlima.png?size=30px)](https://github.com/renatonlima) | Plano de Contas ITG 1000 para Microempresas e Empresa de Pequeno Porte
[l10n_br_crm](l10n_br_crm/) | 16.0.1.1.0 | [![renatonlima](https://github.com/renatonlima.png?size=30px)](https://github.com/renatonlima) [![rvalyi](https://github.com/rvalyi.png?size=30px)](https://github.com/rvalyi) [![mbcosta](https://github.com/mbcosta.png?size=30px)](https://github.com/mbcosta) | Brazilian Localization CRM
[l10n_br_currency_rate_update](l10n_br_currency_rate_update/) | 16.0.1.1.0 | [![renatonlima](https://github.com/renatonlima.png?size=30px)](https://github.com/renatonlima) | Update exchange rates using OCA modules for Brazil
[l10n_br_fiscal](l10n_br_fiscal/) | 16.0.1.5.4 | [![renatonlima](https://github.com/renatonlima.png?size=30px)](https://github.com/renatonlima) | Brazilian fiscal core module.
[l10n_br_fiscal_certificate](l10n_br_fiscal_certificate/) | 16.0.1.0.0 | [![renatonlima](https://github.com/renatonlima.png?size=30px)](https://github.com/renatonlima) | A1 fiscal certificate management for Brazil
[l10n_br_fiscal_dfe](l10n_br_fiscal_dfe/) | 16.0.1.0.0 |  | Distribuição de documentos fiscais
[l10n_br_nfse](l10n_br_nfse/) | 16.0.1.0.0 | [![mileo](https://github.com/mileo.png?size=30px)](https://github.com/mileo) [![luismalta](https://github.com/luismalta.png?size=30px)](https://github.com/luismalta) [![marcelsavegnago](https://github.com/marcelsavegnago.png?size=30px)](https://github.com/marcelsavegnago) | NFS-e
[l10n_br_nfse_focus](l10n_br_nfse_focus/) | 16.0.1.1.0 | [![AndreMarcos](https://github.com/AndreMarcos.png?size=30px)](https://github.com/AndreMarcos) [![mileo](https://github.com/mileo.png?size=30px)](https://github.com/mileo) [![ygcarvalh](https://github.com/ygcarvalh.png?size=30px)](https://github.com/ygcarvalh) [![marcelsavegnago](https://github.com/marcelsavegnago.png?size=30px)](https://github.com/marcelsavegnago) | NFS-e (FocusNFE)
[l10n_br_resource](l10n_br_resource/) | 16.0.1.0.1 | [![mileo](https://github.com/mileo.png?size=30px)](https://github.com/mileo) [![lfdivino](https://github.com/lfdivino.png?size=30px)](https://github.com/lfdivino) | This module extend core resource to create important brazilian informations. Define a Brazilian calendar and some tools to compute dates used in financial and payroll modules
[l10n_br_setup_tests](l10n_br_setup_tests/) | 16.0.1.0.0 | [![antoniospneto](https://github.com/antoniospneto.png?size=30px)](https://github.com/antoniospneto) | Modules for Odoo's Brazil-focused usability with integration tests.
[l10n_br_stock](l10n_br_stock/) | 16.0.1.0.1 |  | Brazilian Localization Warehouse
[l10n_br_zip](l10n_br_zip/) | 16.0.2.1.0 | [![renatonlima](https://github.com/renatonlima.png?size=30px)](https://github.com/renatonlima) | Brazilian Localisation ZIP Codes

[//]: # (end addons)

<!-- prettier-ignore-end -->

## Licenses

This repository is licensed under [AGPL-3.0](LICENSE).

However, each module can have a totally different license, as long as they adhere to Odoo Community Association (OCA)
policy. Consult each module's `__manifest__.py` file, which contains a `license` key
that explains its license.

----
OCA, or the [Odoo Community Association](http://odoo-community.org/), is a nonprofit
organization whose mission is to support the collaborative development of Odoo features
and promote its widespread use.
