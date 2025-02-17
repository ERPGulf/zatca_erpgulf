

// frappe.listview_settings["Sales Invoice"] = {
//     onload: function(listview) {
//         listview.page.add_action_item(__("Resubmit failed invoices"), () => {
//             const selected = listview.get_checked_items();
//             if (selected.length === 0) {
//                 frappe.msgprint(__('Please select at least one Sales Invoice.'));
//                 return;
//             }

//             frappe.call({
//                 method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.resubmit_invoices",
//                 args: {
//                     invoice_numbers: selected.map(invoice => invoice.name)
//                 },
//                 callback: function(response) {
//                     if (response.message) {
//                         // frappe.msgprint(__('Invoices have been resubmitted.'));
//                         listview.refresh();
//                         listview.check_all(false);
//                     } else {
//                         frappe.msgprint(__('Failed to resubmit some invoices. Please check logs for details.'));
//                     }
//                 }
//             });
//         });
//     }
// };
// Function to extend listview events dynamically
function extend_listview_event(doctype, event, callback) {
    if (!frappe.listview_settings[doctype]) {
        frappe.listview_settings[doctype] = {};
    }

    const old_event = frappe.listview_settings[doctype][event];
    frappe.listview_settings[doctype][event] = function (listview) {
        if (old_event) {
            old_event(listview); // Call the original event
        }
        callback(listview); // Call your custom callback
    };
}

// Extend the "onload" event for Sales Invoice
extend_listview_event("Sales Invoice", "onload", function (listview) {
    // Add the "Resubmit failed invoices" action to the menu
    listview.page.add_action_item(__("Send Invoices to Zatca"), () => {
        const selected = listview.get_checked_items();
        if (selected.length === 0) {
            frappe.msgprint(__('Please select at least one Sales Invoice.'));
            return;
        }

        frappe.call({
            method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.resubmit_invoices",
            args: {
                invoice_numbers: selected.map(invoice => invoice.name),
                bypass_background_check: true   // Bypass the background check
            },
            callback: function (response) {
                if (response.message) {
                    // Refresh the list view and uncheck all items
                    listview.refresh();
                    listview.check_all(false);
                } else {
                    frappe.msgprint(__('Failed to resubmit some invoices. Please check logs for details.'));
                }
            }
        });
    });

    // Log a message to confirm custom functionality is loaded
    console.log('Custom "Resubmit failed invoices" action added to Sales Invoice list view.');
});
