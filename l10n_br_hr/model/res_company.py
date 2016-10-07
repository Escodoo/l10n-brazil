# -*- coding: utf-8 -*-
# (c) 2014 Kmee - Rafael da Silva Lima <rafael.lima@kmee.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from openerp import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    check_benefits = fields.Boolean(u'Vale Refeição e Vale Alimentação',
                                    required=False)
