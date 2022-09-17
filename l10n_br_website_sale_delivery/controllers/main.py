# Copyright 2020 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleDelivery(WebsiteSale):
    def _update_website_sale_delivery_return(self, order, **post):
        Monetary = request.env["ir.qweb.field.monetary"]
        carrier_id = int(post["carrier_id"])
        currency = order.currency_id
        if order:
            return {
                "status": order.delivery_rating_success,
                "error_message": order.delivery_message,
                "carrier_id": carrier_id,
                "new_amount_delivery": Monetary.value_to_html(
                    order.amount_delivery, {"display_currency": currency}
                ),
                "new_amount_untaxed": Monetary.value_to_html(
                    order.amount_untaxed, {"display_currency": currency}
                ),
                "new_amount_tax": Monetary.value_to_html(
                    order.amount_tax, {"display_currency": currency}
                ),
                "new_amount_total": Monetary.value_to_html(
                    order.amount_total, {"display_currency": currency}
                ),
            }
        return {}
