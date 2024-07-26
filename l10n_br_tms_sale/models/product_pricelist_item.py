# Copyright 2024 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import test_python_expr

DEFAULT_PYTHON_CODE = """# Available variables:
#  - env: Odoo Environment on which the sqi profile is triggered
#  - model: Odoo Model of the record on which the sqi profile is triggered; is a void recordset
#  - record: record on which the sqi profile is triggered; may be void
#  - records: recordset on which the sqi profile is triggered in multi-mode; may be void
#  - time, datetime, dateutil, timezone: useful Python libraries
#  - float_compare: Odoo function to compare floats based on specific precisions
#  - log: log(message, level='info'): logging function to record information in ir.logging table
#  - UserError: Warning Exception to use with raise
# To return an result, assign: result = value or 0 \n\n\n\n"""


class ProductPricelistItem(models.Model):

    _inherit = "product.pricelist.item"

    # Python code
    code = fields.Text(
        string="Python Code",
        groups="base.group_system",
        required=True,
        default=DEFAULT_PYTHON_CODE,
        help="Write Python code that the sqi profile will execute. Some variables are "
        "available for use; help about python expression is given in the help tab.",
    )

    compute_price = fields.Selection(
        selection_add=[("python", "Python Code")], ondelete={"python": "cascade"}
    )

    @api.constrains("code")
    def _check_python_code(self):
        for profile in self.sudo().filtered("code"):
            msg = test_python_expr(expr=profile.code.strip(), mode="exec")
            if msg:
                raise ValidationError(msg)
