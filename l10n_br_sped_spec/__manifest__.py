# -*- coding: utf-8 -*-
# Copyright 2018 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'SPED Spec',
    'description': """
        Tabelas do SPED (ECD, ECF, EFD e FCI), geridas a partir da lib python-sped""",
    'version': '14.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Akretion',
    'website': 'www.akretion.com',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/sped_base.xml',
        'views/sped_ecd.xml',
        'views/sped_ecf.xml',
        'views/sped_efd_icms_ipi.xml',
        'views/sped_efd_pis_cofins.xml',
#        'views/fci.xml',
    ],
    'demo': [
    ],
}
