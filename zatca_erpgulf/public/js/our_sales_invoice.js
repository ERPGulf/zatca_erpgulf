
frappe.ui.form.on("Sales Invoice", {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1 && !["CLEARED", "REPORTED"].includes(frm.doc.custom_zatca_status)) {
                frm.add_custom_button(__("Send invoice to Zatca"), function() {
                    frm.call({
                        method:"zatca_erpgulf.zatca_erpgulf.sign_invoice.zatca_Background",
                        args: {
                            "invoice_number": frm.doc.name
                        },
                        callback: function(response) {
                            if (response.message) {  
                                frappe.msgprint(response.message);
                                frm.reload_doc();
        
                            }
                            frm.reload_doc();
                        }
                        
                    
                    });
                    frm.reload_doc();
                }, __("Zatca Phase-2"));
        }   

        // frm.add_custom_button(__("Check invoice Validity"), function() {
        //     frm.call({
        //         method:"zatca2024.zatca2024.validation_inside_invoice.zatca_Call_compliance_inside",
        //         args: {
        //             "invoice_number": frm.doc.name
        //         },
        //         callback: function(response) {
        //             if (response.message) {  
        //                 frappe.msgprint(response.message);
        //                 frm.reload_doc();
  
        //             }
        //             frm.reload_doc();
        //         }
                
            
        //     });
        //     frm.reload_doc();
        // }, __("Zatca Phase-2"));
    }
});
