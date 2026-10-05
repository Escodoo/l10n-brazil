# Copyright 2026 Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

# ADN distribution (tomador). Distinct from the Sefin Nacional emission API.
NFSE_ADN_BASE_URLS = {
    "producao": "https://adn.nfse.gov.br",
    "producao_restrita": "https://adn.producaorestrita.nfse.gov.br",
}

NFSE_ADN_DFE_PATH = "/contribuintes/DFe"
NFSE_ADN_NFSE_PATH = "/contribuintes/NFSe"

NFSE_LOTE_SIZE = 50
NFSE_MAX_PAGES = 20
NFSE_ACCESS_KEY_SIZE = 50

NFSE_NOTE_TYPES = {"NFSE", "NFS-E"}

# National event codes (tpEvento), with or without the leading "e".
NFSE_CANCEL_EVENT_CODES = {"101101", "105102", "305101"}

NFSE_STATE_AUTHORIZED = "1"
NFSE_STATE_CANCELLED = "3"

NFSE_STATE_LABELS = {
    NFSE_STATE_AUTHORIZED: "Authorized",
    NFSE_STATE_CANCELLED: "Cancelled",
}

NFSE_EVENT_LABELS = {
    "101101": "NFS-e Cancellation",
    "e101101": "NFS-e Cancellation",
    "105102": "NFS-e Cancellation by Substitution",
    "e105102": "NFS-e Cancellation by Substitution",
    "305101": "NFS-e Cancellation by the Tax Authority",
    "e305101": "NFS-e Cancellation by the Tax Authority",
}
