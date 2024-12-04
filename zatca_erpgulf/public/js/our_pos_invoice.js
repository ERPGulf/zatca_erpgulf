frappe.realtime.on('hide_gif', () => {
    $('#custom-gif-overlay').remove();
});

frappe.realtime.on('show_gif', (data) => {
    const gifHtml = `
        <div id="custom-gif-overlay" style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255, 255, 255, 0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1050;">
            <img src="${data.gif_url}" alt="Loading..." style="width: 100px; height: 100px;">
        </div>`;
    $('body').append(gifHtml);
});


// frappe.ui.form.on("POS Invoice", {
//     refresh: function(frm) {
//         if (frm.doc.docstatus === 1 && !["CLEARED", "REPORTED"].includes(frm.doc.custom_zatca_status)) {
//                 frm.add_custom_button(__("Send invoice to Zatca"), function() {
//                     frm.call({
//                         method:"zatca_erpgulf.zatca_erpgulf.pos_sign.zatca_Background",
//                         args: {
//                             "invoice_number": frm.doc.name
                            
//                         },
//                         callback: function(response) {
//                             if (response.message) {  
//                                 frappe.msgprint(response.message);
//                                 frm.reload_doc();
        
//                             }
//                             frm.reload_doc();
//                         }
                        
                    
//                     });
//                     frm.reload_doc();
//                 }, __("Zatca Phase-2"));
//         }   

//         // frm.add_custom_button(__("Check invoice Validity"), function() {
//         //     frm.call({
//         //         method:"zatca2024.zatca2024.validation_inside_invoice.zatca_Call_compliance_inside",
//         //         args: {
//         //             "invoice_number": frm.doc.name
//         //         },
//         //         callback: function(response) {
//         //             if (response.message) {  
//         //                 frappe.msgprint(response.message);
//         //                 frm.reload_doc();
  
//         //             }
//         //             frm.reload_doc();
//         //         }
                
            
//         //     });
//         //     frm.reload_doc();
//         // }, __("Zatca Phase-2"));
//     }
// });
// frappe.ui.form.on("POS Invoice", {
//     refresh: function(frm) {
//         if (frm.doc.docstatus === 1 && !["CLEARED", "REPORTED"].includes(frm.doc.custom_zatca_status)) {
//             frm.page.clear_menu(); // Clear the default buttons

//             frm.page.add_menu_item(__("Send invoice to Zatca"), function() {
//                 frm.call({
//                     method: "zatca_erpgulf.zatca_erpgulf.pos_sign.zatca_Background",
//                     args: {
//                         "invoice_number": frm.doc.name
//                     },
//                     callback: function(response) {
//                         if (response.message) {
//                             frappe.msgprint(response.message);
//                             frm.reload_doc();
//                         }
//                     }
//                 });
//             }, __("Zatca Phase-2"));

//             // Add back the default "Create" button or any other buttons you want
//             frm.page.add_menu_item(__("Create"), function() {
//                 frappe.new_doc('POS Invoice'); // Example action
//             });
//         }
//     }
// });


// frappe.ui.form.on("POS Invoice", {
//     refresh: function(frm) {
//         if (frm.doc.docstatus === 1 && !["CLEARED", "REPORTED"].includes(frm.doc.custom_zatca_status)) {
//             // Check if the custom button already exists to avoid adding it multiple times
//             if (!frm.custom_buttons || !frm.custom_buttons["Send invoice to Zatca"]) {
//                 frm.add_custom_button(__("Send invoice to Zatca"), function() {
//                     frm.call({
//                         method: "zatca_erpgulf.zatca_erpgulf.pos_sign.zatca_Background",
//                         args: {
//                             "invoice_number": frm.doc.name
//                         },
//                         callback: function(response) {
//                             if (response.message) {
//                                 frappe.msgprint(response.message);
//                                 frm.reload_doc();
//                             }
//                         }
//                     });
//                 }, __("Zatca Phase-2"));
//             }
//         }
//     }
// });

