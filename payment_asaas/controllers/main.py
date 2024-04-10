# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import http
from odoo.http import request


class AsaasController(http.Controller):
    @http.route(
        ["/payment/asaas/s2s/create_json_3ds"], type="json", auth="public", csrf=False
    )
    def asaas_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
        if not kwargs.get("partner_id"):
            kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)

        token = (
            request.env["payment.acquirer"]
            .browse(int(kwargs.get("acquirer_id")))
            .s2s_process(kwargs)
        )

        if not token:
            res = {
                "result": False,
            }
        else:
            res = {
                "result": True,
                "id": token.id,
                "short_name": token.short_name,
                "3d_secure": False,
                "verified": False,
            }

            if verify_validity:
                token.validate()
                res["verified"] = token.verified

        return res
