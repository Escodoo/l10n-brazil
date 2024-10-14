# Copyright 2024 - TODAY, Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "NFS-e (DSF)",
    "summary": """
        Emissão de NFS-e pelo provedor DSF""",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Escodoo, Odoo Community Association (OCA)",
    "maintainers": ["marcelsavegnago", "kaynnan"],
    "website": "https://github.com/OCA/l10n-brazil",
    "development_status": "Beta",
    "external_dependencies": {
        "python": [
            "erpbrasil.edoc>=2.5.2",
            "erpbrasil.assinatura>=1.7.0",
            "erpbrasil.transmissao>=1.1.0",
            "erpbrasil.base>=2.3.0",
            "nfselib",
        ],
    },
    "depends": [
        "l10n_br_nfse",
    ],
}
