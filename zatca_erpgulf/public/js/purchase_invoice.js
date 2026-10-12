frappe.ui.form.on("Purchase Invoice", {
    setup(frm) {
        // Register the realtime listener only once per browser session
        if (!window.__pi_country_listener) {
            window.__pi_country_listener = true;
            frappe.realtime.on("company_country_changed", (data) => {
                if (
                    cur_frm &&
                    cur_frm.doctype === "Purchase Invoice" &&
                    cur_frm.doc.company === data.company
                ) {
                    pi_sync_country(cur_frm);
                }
            });
        }
    },

    refresh(frm) {
        pi_sync_country(frm);
    },

    company(frm) {
        pi_sync_country(frm);
    },
});

function pi_sync_country(frm) {
    if (!frm.doc.company) return;

    frappe.db.get_value("Company", frm.doc.company, "country").then((r) => {
        const country = (r.message && r.message.country) || "";
        if (frm.doc.custom_company_country === country) return;

        if (frm.doc.docstatus === 0) {
            // Draft: normal update, saved with the invoice
            frm.set_value("custom_company_country", country);
        } else {
            // Submitted/cancelled: update on screen only, then re-check Depends On
            frm.doc.custom_company_country = country;
            frm.refresh_fields();
        }
    });
}