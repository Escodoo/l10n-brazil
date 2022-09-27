odoo.define("l10n_br_pos_cfe.OrderHeaderReceipt", function (require) {
    "use strict";

    const PosComponent = require("point_of_sale.PosComponent");
    const Registries = require("point_of_sale.Registries");

    class OrderHeaderReceipt extends PosComponent {
        get company() {
            return this.props.company;
        }

        // Getters //

        get name() {
            return this.company.name;
        }

        get legalName() {
            return this.company.legal_name;
        }

        get cnpj() {
            return this.company.cnpj;
        }

        get ie() {
            return this.company.ie;
        }

        get address() {
            return `${this.company.address.street_name} ${this.company.address.street_number} ${this.company.address.district} ${this.company.address.city} ${this.company.address.zip}`;
        }

        get im() {
            return this.company.inscr_mun;
        }
    }
    OrderHeaderReceipt.template = "OrderHeaderReceipt";

    Registries.Component.add(OrderHeaderReceipt);

    return OrderHeaderReceipt;
});
