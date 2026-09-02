frappe.ui.form.on("Sales Invoice Item", {
    item_tax_template: function (frm, cdt, cdn) {

        let row = locals[cdt][cdn];

        if (!row.item_tax_template) {
            frappe.model.set_value(
                cdt,
                cdn,
                "custom_exemption_reason_code",
                ""
            );

            frappe.model.set_value(
                cdt,
                cdn,
                "custom_tax_exemption_reason",
                ""
            );

            return;
        }

        frappe.db.get_value(
            "Item Tax Template",
            row.item_tax_template,
            [
                "custom_exemption_reason_code",
                "custom_tax_exemption_reason"
            ]
        ).then(function (r) {

            console.log("Template:", row.item_tax_template);
            console.log("Response:", r);

            let reason_code = "";
            let reason = "";

            if (r.message) {
                reason_code =
                    r.message.custom_exemption_reason_code || "";

                reason =
                    r.message.custom_tax_exemption_reason || "";
            }

            frappe.model.set_value(
                cdt,
                cdn,
                "custom_exemption_reason_code",
                reason_code
            );

            frappe.model.set_value(
                cdt,
                cdn,
                "custom_tax_exemption_reason",
                reason
            );
        });
    }
});

frappe.ui.form.on("POS Invoice Item", {
    item_tax_template: function (frm, cdt, cdn) {

        let row = locals[cdt][cdn];

        if (!row.item_tax_template) {
            frappe.model.set_value(
                cdt,
                cdn,
                "custom_tax_exemption_reason",
                ""
            );
            return;
        }

        frappe.db.get_value(
            "Item Tax Template",
            row.item_tax_template,
            "custom_tax_exemption_reason"
        ).then(function (r) {

            console.log("Template:", row.item_tax_template);
            console.log("Response:", r);

            let value = "";

            if (
                r.message &&
                r.message.custom_tax_exemption_reason
            ) {
                value = r.message.custom_tax_exemption_reason;
            }

            frappe.model.set_value(
                cdt,
                cdn,
                "custom_tax_exemption_reason",
                value
            );
        });
    }
});