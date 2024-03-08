/* eslint no-unused-vars: "off", no-undef: "off" */

odoo.define("l10n_br_website_sale.l10n_br_address", function (require) {
    "use strict";

    require("web.dom_ready");
    var ajax = require("web.ajax");

    var $checkout_autoformat_selector = $(".checkout_autoformat");

    if (!$checkout_autoformat_selector.length) {
        return $.Deferred().reject("DOM doesn't contain '.checkout_autoformat'");
    }

    function formatCpfCnpj(inputValue) {
        // Remove non-numeric characters
        let value = inputValue.replace(/\D/g, "");

        // Truncate the value to 11 digits if it's more than 11 and less than 14
        if (value.length > 11 && value.length < 14) {
            value = value.substring(0, 11);
        }
        // Truncate the value to 14 digits if it's 14 or more
        else if (value.length >= 14) {
            value = value.substring(0, 14);
        }

        if (value.length <= 11) {
            // Format as CPF
            value = value.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4");
        } else {
            // Format as CNPJ
            value = value.replace(
                /(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/,
                "$1.$2.$3/$4-$5"
            );
        }

        return value;
    }

    $("#input_cnpj_cpf").on("blur", function () {
        var value = $(this).val();
        var formattedValue = formatCpfCnpj(value);
        $(this).val(formattedValue);
    });

    var zip_cleave = new Cleave(".input-zipcode", {
        blocks: [5, 3],
        delimiter: "-",
        numericOnly: true,
    });

    if ($checkout_autoformat_selector.length) {
        $checkout_autoformat_selector.on(
            "change",
            "select[name='country_id']",
            function () {
                var country_id = $("select[name='country_id']") || false;
                if (country_id) {
                    if (country_id.val() === "31") {
                        $("input[name='city']").parent("div").hide();
                        $("select[name='city_id']").parent("div").show();
                    } else {
                        $("select[name='city_id']").parent("div").hide();
                        $("input[name='city']").parent("div").show();
                    }
                }
            }
        );
        $checkout_autoformat_selector.on(
            "change",
            "select[name='state_id']",
            function () {
                var state_id_selector = $("#state_id");
                if (!state_id_selector.val()) {
                    return;
                }
                ajax.jsonRpc(
                    "/shop/state_infos/" + state_id_selector.val(),
                    "call"
                ).then(function (data) {
                    // Populate states and display
                    var city_id_selector = $("select[name='city_id']");
                    var selectCities = city_id_selector;
                    var zip_city = city_id_selector[0].val;
                    // Dont reload state at first loading (done in qweb)
                    if (
                        selectCities.data("init") === 0 ||
                        selectCities.find("option").length === 1
                    ) {
                        if (data.cities.length) {
                            _.each(data.cities, function (x) {
                                var opt = $("<option>")
                                    .text(x[1])
                                    .attr("value", x[0])
                                    .attr("data-code", x[2]);
                                selectCities.append(opt);
                            });
                            selectCities.parent("div").show();
                            $("input[name='city']").parent("div").hide();
                            city_id_selector.val(zip_city);
                        } else {
                            selectCities.val("").parent("div").hide();
                            $("input[name='city']").parent("div").show();
                        }
                        selectCities.data("init", 0);
                    } else {
                        selectCities.data("init", 0);
                    }
                });
            }
        );
        $checkout_autoformat_selector.on("change", "input[name='zip']", function () {
            var vals = {zipcode: $('input[name="zip"]').val()};
            console.log("Changing ZIP");
            $('a:contains("Next")').attr("display: none !important;");
            ajax.jsonRpc("/l10n_br/zip_search_public", "call", vals).then(function (
                data
            ) {
                if (data.error) {
                    // Todo: Retornar nos campos error e error_message
                    console.log("Falha ao consultar cep");
                } else {
                    var city_id_selector = $('select[name="city_id"]');
                    var state_id_selector = $('select[name="state_id"]');
                    $('input[name="district"]').val(data.district);
                    $('input[name="street_name"]').val(data.street_name);
                    city_id_selector.val(data.city_id);
                    city_id_selector.change();
                    city_id_selector[0].val = data.city_id;
                    state_id_selector.val(data.state_id);
                    state_id_selector.change();
                    $('a:contains("Next")').attr("display: block !important;");
                }
            });
        });
    }
});
