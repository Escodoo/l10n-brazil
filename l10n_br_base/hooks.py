# Copyright (C) 2019-2020 - Raphael Valyi Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import logging

_logger = logging.getLogger(__name__)


def pre_init_hook(env):
    """
    The objective of this hook is to ensure the Brazil country is
    translated as "Brasil" in pt_BR to get the NFe tests pass
    even if the pt_BR language pack is not installed.
    """
    env.ref("base.br").with_context(lang="pt_BR").name = "Brasil"