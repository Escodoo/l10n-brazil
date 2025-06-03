// Copyright 2025 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
// License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

odoo.define("payment_asaas.asaas_tokenize_card", function (require) {
    "use strict";

    var core = require("web.core");
    var rpc = require("web.rpc");
    var PaymentForm = require("payment.payment_form");

    var _t = core._t;

    PaymentForm.include({
        willStart: function () {
            return this._super.apply(this, arguments).then(function () {
                return Promise.resolve();
            });
        },

        _createAsaasToken: function (ev, $checkedRadio) {
            var self = this;
            let button = ev.target;
            if (ev.type === "submit") {
                button = $(ev.target).find('*[type="submit"]')[0];
            }
            this.disableButton(button);
            if (this.options.partnerId === undefined) {
                console.warn(
                    "payment_form: unset partner_id when adding new token; things could go wrong"
                );
            }

            var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
            var acquirerForm = this.$("#o_payment_add_token_acq_" + acquirerID);
            var ds = $('input[name="data_set"]', acquirerForm)[0];
            var inputsForm = $("input", acquirerForm);
            var formData = this.getFormData(inputsForm);
            console.log(formData);
            rpc.query({
                route: "/payment/asaas/tokenize_card",
                params: {
                    acquirer_id: acquirerID,
                    cc_holder_name: formData.cc_holder_name,
                    cc_number: formData.cc_number.replace(/\s+/g, ""),
                    cc_expiry: formData.cc_expiry,
                    cc_cvc: formData.cc_cvc,
                    partner_id: formData.partner_id,
                },
            })
                .then(function (result) {
                    if (result && result.cc_token) {
                        formData.cc_token = result.cc_token;
                        _.extend(formData, {
                            cc_number: "",
                            cc_expiry: "",
                            cc_cvc: "",
                            data_set: ds.dataset.createRoute,
                        });
                        return rpc.query({
                            route: formData.data_set,
                            params: formData,
                        });
                    }
                    self.enableButton(button);
                    self.displayError(
                        _t("Tokenization error"),
                        _t("Could not tokenize your card. Please try again.")
                    );
                })
                .then(function (result) {
                    if (result) {
                        $checkedRadio.val(result.id);
                        self.el.submit();
                    }
                })
                .catch(function () {
                    self.enableButton(button);
                    self.displayError(
                        _t("Error info"),
                        _t("We are not able to add your payment method at the moment. ")
                    );
                });
        },
        payEvent: function (ev) {
            ev.preventDefault();
            var $checkedRadio = this.$('input[type="radio"]:checked');
            if (
                $checkedRadio.length === 1 &&
                $checkedRadio.data("provider") === "asaas" &&
                this.isNewPaymentRadio($checkedRadio)
            ) {
                return this._createAsaasToken(ev, $checkedRadio);
            }
            return this._super.apply(this, arguments);
        },
    });
});
