# Copyright 2023 - TODAY, Akretion - Raphael Valyi <raphael.valyi@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.en.html).

from os import path

from odoo.tests import common

from odoo.addons import l10n_br_sped_ecd


class SpedTest(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.demo_path = path.join(l10n_br_sped_ecd.__path__[0], "demo")

    def test_import_ecd(self):
        self.env["l10n_br_sped.mixin"].flush_registers("ecd")
        file_path = path.join(self.demo_path, "demo_ecd.txt")
        sped_mixin = self.env["l10n_br_sped.mixin"]
        declaration = sped_mixin.import_file(file_path, "ecd")
        sped = declaration.generate_sped_text()
        with open(file_path) as f:
            target_content = f.read()
            # print(sped)
            self.assertEqual(sped.strip(), target_content.strip())
