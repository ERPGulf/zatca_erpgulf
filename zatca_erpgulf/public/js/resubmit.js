

frappe.listview_settings["Sales Invoice"] = {
    onload: function(listview) {
        listview.page.add_action_item(__("Resubmit failed invoices"), () => {
            const selected = listview.get_checked_items();
            if (selected.length === 0) {
                frappe.msgprint(__('Please select at least one Sales Invoice.'));
                return;
            }

            frappe.call({
                method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.resubmit_invoices",
                args: {
                    invoice_numbers: selected.map(invoice => invoice.name)
                },
                callback: function(response) {
                    if (response.message) {
                        // frappe.msgprint(__('Invoices have been resubmitted.'));
                        listview.refresh();
                        listview.check_all(false);
                    } else {
                        frappe.msgprint(__('Failed to resubmit some invoices. Please check logs for details.'));
                    }
                }
            });
        });
    }
};
