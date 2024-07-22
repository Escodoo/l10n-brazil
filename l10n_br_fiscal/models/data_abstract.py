# Copyright (C) 2019  Renato Lima - Akretion <renato.lima@akretion.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import json

from erpbrasil.base import misc
from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.osv import expression


class DataAbstract(models.AbstractModel):
    _name = "l10n_br_fiscal.data.abstract"
    _description = "Fiscal Data Abstract"
    _order = "code"
    _rec_names_search = ["name", "code", "code_unmasked"]

    code = fields.Char(required=True, index=True)

    name = fields.Text(required=True, index=True)

    code_unmasked = fields.Char(
        string="Unmasked Code", compute="_compute_code_unmasked", store=True, index=True
    )

    active = fields.Boolean(default=True)

    def action_archive(self):
        if not self.env.user.has_group("l10n_br_fiscal.group_manager"):
            raise AccessError(_("You don't have permission to archive records."))
        return super().action_archive()

    def action_unarchive(self):
        if not self.env.user.has_group("l10n_br_fiscal.group_manager"):
            raise AccessError(_("You don't have permission to unarchive records."))
        return super().action_unarchive()

    @api.depends("code")
    def _compute_code_unmasked(self):
        for r in self:
            # TODO mask code and unmasck
            r.code_unmasked = misc.punctuation_rm(r.code)

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == "search":
            for node in arch.xpath("//field[@name='code']"):
                node.attrib["filter_domain"] = (
                    "['|', '|', ('code', 'ilike', self), "
                    "('code_unmasked', 'ilike', self + '%'),"
                    "('name', 'ilike', self + '%')]"
                )
        return arch, view

    @api.depends("name", "code")
    @api.depends_context("show_code_only")
    def _compute_display_name(self):
        def truncate_name(name):
            if len(name) > 60:
                name = "{}...".format(name[:60])
            return name
            
        for rec in self:
            if self._context.get("show_code_only"):
                rec.display_name = rec.code
            else:
                rec.display_name = "{} - {}".format(
                    rec.code, truncate_name(rec.name)
                )
