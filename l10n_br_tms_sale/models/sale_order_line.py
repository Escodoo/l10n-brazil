# Copyright 2024 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from pytz import timezone

import odoo
from odoo import models, tools
from odoo.tools.float_utils import float_compare
from odoo.tools.safe_eval import safe_eval


class SaleOrderLine(models.Model):

    _inherit = "sale.order.line"

    def _get_eval_context(self, rule=None):
        """Prepare the context used when evaluating python code, like the
        python formulas or code server actions.

        :param rule: the current price rule
        :type rule: browse record
        :returns: dict -- evaluation context given to (safe_)safe_eval"""

        def log(message, level="info"):
            with self.pool.cursor() as cr:
                cr.execute(
                    """
                    INSERT INTO ir_logging(create_date, create_uid, type, dbname, name, level,
                    message, path, line, func)
                    VALUES (NOW() at time zone 'UTC', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        self.env.uid,
                        "server",
                        self._cr.dbname,
                        __name__,
                        level,
                        message,
                        "rule",
                        rule.id,
                        rule.name,
                    ),
                )

        eval_context = {
            "uid": self._uid,
            "user": self.env.user,
            "time": tools.safe_eval.time,
            "datetime": tools.safe_eval.datetime,
            "dateutil": tools.safe_eval.dateutil,
            "timezone": timezone,
            "float_compare": float_compare,
            "b64encode": base64.b64encode,
            "b64decode": base64.b64decode,
        }

        model_name = self._name
        model = self.env[model_name]
        record = self
        records = None
        if self._context.get("active_model") == model_name and self._context.get(
            "active_id"
        ):
            record = model.browse(self._context["active_id"])
        if self._context.get("active_model") == model_name and self._context.get(
            "active_ids"
        ):
            records = model.browse(self._context["active_ids"])
        if self._context.get("onchange_self"):
            record = self._context["onchange_self"]
        eval_context.update(
            {
                # orm
                "env": self.env,
                "model": model,
                # Exceptions
                "Warning": odoo.exceptions.Warning,
                "UserError": odoo.exceptions.UserError,
                # record
                "record": record,
                "records": records,
                # helpers
                "log": log,
            }
        )
        return eval_context

    def _get_display_price(self, product):
        result = super()._get_display_price(product)
        if not product:
            return result

        product_context = dict(
            self.env.context,
            partner_id=self.order_id.partner_id.id,
            date=self.order_id.date_order,
            uom=self.product_uom.id,
        )
        final_price, rule_id = self.order_id.pricelist_id.with_context(
            product_context
        ).get_product_price_rule(
            product or self.product_id,
            self.product_uom_qty or 1.0,
            self.order_id.partner_id,
        )
        rule = self.env["product.pricelist.item"].browse(rule_id)
        if rule.compute_price == "python":
            eval_context = self._get_eval_context(rule=rule)
            code = rule.code.strip()
            safe_eval(code, eval_context, mode="exec", nocopy=True)
            if eval_context.get("result"):
                result = eval_context.get("result")
        return result
