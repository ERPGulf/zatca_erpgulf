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

frappe.ui.form.on('POS Invoice', {
    refresh(frm) {
        const response = frm.doc.custom_zatca_full_response;
        if (!response) return;

        try {
            // Find start and end of JSON
            const json_start = response.indexOf('{');
            const json_end = response.lastIndexOf('}');

            if (json_start === -1 || json_end === -1 || json_end <= json_start) {
                return; // no JSON detected
            }

            const json_string = response.slice(json_start, json_end + 1);
            const zatca = JSON.parse(json_string);  // Safe now

            let errors = Array.isArray(zatca?.validationResults?.errorMessages) ? zatca.validationResults.errorMessages : [];
            const warnings = Array.isArray(zatca?.validationResults?.warningMessages) ? zatca.validationResults.warningMessages : [];

            // 🔴 Special condition → ignore Duplicate-Invoice error
            errors = errors.filter(e => !(e.code === "Invoice-Errors" && e.category === "Duplicate-Invoice"));

            // If nothing remains, skip
            if (!errors.length && !warnings.length) return;

            let combined_html = "";

            if (errors.length) {
                combined_html += `<div style="color:#b71c1c; font-weight:bold;">Errors:</div>`;
                combined_html += `<div style="color:#b71c1c;">` + errors.map(e =>
                    `<div style="margin-left:10px;"><b>${e.code}</b>: ${e.message}</div>`
                ).join('') + `</div>`;
            }

            if (warnings.length) {
                combined_html += `<div style="color:#ef6c00; font-weight:bold; margin-top:10px;">Warnings:</div>`;
                combined_html += `<div style="color:#ef6c00;">` + warnings.map(w =>
                    `<div style="margin-left:10px;"><b>${w.code}</b>: ${w.message}</div>`
                ).join('') + `</div>`;
            }

            const alert_color = errors.length ? 'red' : 'orange';
            frm.dashboard.set_headline_alert(combined_html, alert_color);

        } catch (e) {
            frappe.msgprint("❌ Failed to parse ZATCA response JSON.<br><code>" + e.message + "</code>");
            console.error("ZATCA parse error:", e);
        }
    }
});


// frappe.ui.form.on('POS Invoice', {
//     refresh(frm) {
//         const response = frm.doc.custom_zatca_full_response;
//         if (!response) return;

//         try {
//             // Find start and end of JSON
//             const json_start = response.indexOf('{');
//             const json_end = response.lastIndexOf('}');

//             if (json_start === -1 || json_end === -1 || json_end <= json_start) {
//                 // frappe.msgprint("⚠️ ZATCA JSON not found in response.");
//                 return;
//             }

//             const json_string = response.slice(json_start, json_end + 1);
//             const zatca = JSON.parse(json_string);  // Safe now

//             const errors = zatca?.validationResults?.errorMessages || [];
//             const warnings = zatca?.validationResults?.warningMessages || [];

//             if (errors.length || warnings.length) {
//                 let combined_html = "";

//                 if (errors.length) {
//                     combined_html += `<div style="color:#b71c1c; font-weight:bold;">Errors:</div>`;
//                     combined_html += `<div style="color:#b71c1c;">` + errors.map(e =>
//                         `<div style="margin-left:10px;"><b>${e.code}</b>: ${e.message}</div>`
//                     ).join('') + `</div>`;
//                 }

//                 if (warnings.length) {
//                     combined_html += `<div style="color:#ef6c00; font-weight:bold; margin-top:10px;">Warnings:</div>`;
//                     combined_html += `<div style="color:#ef6c00;">` + warnings.map(w =>
//                         `<div style="margin-left:10px;"><b>${w.code}</b>: ${w.message}</div>`
//                     ).join('') + `</div>`;
//                 }

//                 const alert_color = errors.length ? 'red' : 'orange';
//                 frm.dashboard.set_headline_alert(combined_html, alert_color);
//             }

//         } catch (e) {
//             frappe.msgprint("❌ Failed to parse ZATCA response JSON.<br><code>" + e.message + "</code>");
//             console.error("ZATCA parse error:", e);
//         }
//     }
// });




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



// frappe.ui.form.on("POS Invoice", {
//     refresh: function (frm) {
//         // Load the company doctype to check phase setting
//         if (frm.doc.company) {
//             frappe.db.get_value("Company", frm.doc.company, "custom_phase_1_or_2")
//                 .then(value => {
//                     let phase = value.message.custom_phase_1_or_2;

//                     if (
//                         frm.doc.docstatus === 1 &&
//                         !["CLEARED", "REPORTED"].includes(frm.doc.custom_zatca_status) &&
//                         phase === "Phase-2"
//                     ) {
//                         frm.add_custom_button(
//                             __("Send invoice to ZATCA"),
//                             function () {
//                                 frm.call({
//                                     method: "zatca_erpgulf.zatca_erpgulf.pos_sign.zatca_background_",
//                                     args: {
//                                         invoice_number: frm.doc.name,
//                                         source_doc: frm.doc
//                                     },
//                                     callback: function (r) {
//                                         console.log(r.message);
//                                         frm.reload_doc();
//                                     }
//                                 });
//                             },
//                             __("ZATCA Phase-2")
//                         );
//                     }
//                 });
//         }
   

//         frm.page.add_menu_item(__('Print PDF-A3'), function () {
//             // Create a dialog box with fields for Print Format, Letterhead, and Language
//             const dialog = new frappe.ui.Dialog({
//                 title: __('Generate PDF-A3'),
//                 fields: [
//                     {
//                         fieldtype: 'Link',
//                         fieldname: 'print_format',
//                         label: __('Print Format'),
//                         options: 'Print Format',
//                         // default: 'Claudion Invoice Format', // Default print format if any
//                         reqd: 1,
//                         get_query: function () {
//                             return {
//                                 filters: {
//                                     doc_type: 'Sales Invoice' // Filters print formats related to Sales Invoice
//                                 }
//                             };
//                         }
//                     },
//                     {
//                         fieldtype: 'Link',
//                         fieldname: 'letterhead',
//                         label: __('Letterhead'),
//                         options: 'Letter Head', // Options should be the 'Letter Head' doctype
//                         reqd: 0
//                     },
//                     {
//                         fieldtype: 'Link',
//                         fieldname: 'language',
//                         label: __('Language'),
//                         options: 'Language', // Options should be the 'Language' doctype
//                         // default: 'en', // Default language
//                         reqd: 1
//                     }
//                 ],
//                 primary_action_label: __('Generate PDF-A3'),
//                 primary_action: function () {
//                     const values = dialog.get_values();
//                     frappe.call({
//                         method: 'zatca_erpgulf.zatca_erpgulf.pdf_a3.embed_file_in_pdf',
//                         args: {
//                             invoice_name: frm.doc.name,
//                             print_format: values.print_format,
//                             letterhead: values.letterhead,
//                             language: values.language
//                         },
//                         callback: function (r) {
//                             if (r.message) {
//                                 // Open the generated PDF in a new tab
//                                 console.log(r.message)
//                                 const pdf_url = r.message;
//                                 window.open(pdf_url, '_blank');
//                                 frm.reload_doc();

//                             } else {
//                                 frappe.msgprint(__('Failed to generate PDF-A3'));
//                             }
//                         }

//                     });
//                     dialog.hide();
//                 }
//             });
//             dialog.show();
//         });



//     }
// });


frappe.ui.form.on('POS Invoice', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            // Add menu item like Print PDF-A3
            frm.page.add_menu_item(__('Create XML for Debug'), function() {
                frappe.call({
                    method: "zatca_erpgulf.zatca_erpgulf.pos_debug_xml.debug_call",
                    args: {
                        invoice_number: frm.doc.name
                    },
                    freeze: true,
                    freeze_message: __("Generating Debug XML..."),
                    callback: function(r) {
                        if (r.message && r.message.status === "success") {
                            frappe.msgprint(__('✅ Debug XML attached successfully!'));
                            frm.reload_doc();
                        }
                    }
                });
            });
        }
    }
});
