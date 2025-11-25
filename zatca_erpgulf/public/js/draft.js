frappe.ui.form.on('Sales Invoice', {
    refresh(frm) {
        // Optional: prevent multiple redirects
        if (!frm.__redirect_done && frm.doc.docstatus === 1) {
            frm.__redirect_done = true;

            // If frappe.response.redirect_to exists, use it
            if (frappe.response && frappe.response.redirect_to) {
                frappe.show_alert({
                    message: __('Redirecting to {0}', [frm.doc.name]),
                    indicator: 'green'
                });
                setTimeout(() => {
                    frappe.set_route('Form', 'Sales Invoice', frappe.response.redirect_to.split("/").pop());
                }, 300);
            }
        }
    }
});
