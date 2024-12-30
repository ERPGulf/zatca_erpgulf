// frappe.listview_settings['Sales Invoice'] = {
//     onload: function (listview) {
//         listview.page.add_button(__('Resubmit Failed Invoices'), async function () {
//             const selectedInvoices = listview.get_checked_items();
            
//             if (selectedInvoices.length === 0) {
//                 frappe.msgprint(__('Please select at least one invoice.'));
//                 return;
//             }

//             const invoiceIDs = selectedInvoices.map((invoice) => invoice.name);

//             frappe.call({
//                 method: 'zatca_erpgulf.zatca_erpgulf.sign_invoice.zatca_background',
//                 args: { invoice_ids: invoiceIDs },
//                 callback: function (r) {
//                     if (r.message.success) {
//                         frappe.msgprint(`${r.message.success_count} invoices resubmitted successfully.`);
//                         listview.refresh();
//                     } else if (r.message.failed_count) {
//                         frappe.msgprint(`Failed to resubmit ${r.message.failed_count} invoices.`);
//                     }
//                 },
//                 freeze: true,
//                 freeze_message: __('Resubmitting failed invoices...')
//             });
//         });
//     }
// };
// frappe.listview_settings['Imported Sales Invoice'] = {
//     onload: function(listview) {
//         // Add a custom button to the list view toolbar
//         listview.page.add_inner_button(__('Import to Sales Invoice'), function() {
//             frappe.msgprint("hai")
//             // frappe.call({
//             //     method: "alw.alw.sales.copy_imported_invoices_to_sales_invoices",
//             //     args: {
//             //         // Add any arguments you need here
//             //     },
//             //     freeze: true,
//             //     freeze_message: __('<span style="display: block; text-align: center;">'
//             //         + '<img src="https://global.discourse-cdn.com/sitepoint/original/3X/e/3/e352b26bbfa8b233050087d6cb32667da3ff809c.gif" alt="Processing" style="width: 100px; height: 100px;"><br>'
//             //         + 'Please Wait...<br>Connecting to the remote server to retrieve data</span>'),
//             //     callback: function(response) {
//             //         if (!response.exc) {
//             //             frappe.msgprint(__('Sales invoices copied successfully.'));
//             //             listview.refresh(); // Refresh the list view
//             //         } else {
//             //             frappe.msgprint(__('Failed to copy sales invoices.'));
//             //         }
//             //     }
//             // });
//         });
//     }
// };
// frappe.listview_settings['Sales Invoice'] = {
//     refresh: function (listview) {
//         listview.page.add_button('Resubmit Sales Invoice', () => {
//             // Define the dialog to select the company
            
//         });
//     }
// };
// frappe.listview_settings['Sales Invoice'] = {
//     refresh: function (listview) {
//         listview.page.add_button('Resubmit Sales Invoice', () => {
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
//                 callback: function (response) {
//                     if (response.message) {
//                         frappe.msgprint(__('Invoices have been resubmitted.'));
//                         listview.refresh();
//                     } else {
//                         frappe.msgprint(__('Failed to resubmit some invoices. Please check logs for details.'));
//                     }
//                 }
//             });
//         });
//     }
// };

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
