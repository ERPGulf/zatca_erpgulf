frappe.ui.form.on('Sales Invoice', {
    after_submit(frm) {
        // run only when doc is saved and not dirty
        if (!frm.is_new() && !frm.doc.__unsaved) {
            const name = frm.doc.name;
            frappe.show_alert({
                message: __('Redirecting to {0}', [name]),
                indicator: 'green'
            });
            setTimeout(() => {
                frappe.set_route('Form', 'Sales Invoice', frm.doc.name);
            }, 300);
        }
    }
});