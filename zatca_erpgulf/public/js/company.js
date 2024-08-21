// frappe.ui.form.on("Company", {
//     refresh(frm) {
//         // Refresh logic if any
//     },
//     custom_generate_production_csids: function (frm) {
//         frappe.call({
//             method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.production_CSID",
//             args: {
//                 "company_abbr": frm.doc.abbr
//             },
//             callback: function (r) {
//                 if (!r.exc) {
//                     frm.save();
//                 }
//             },
//         });
//     },
//     custom_generate_compliance_csid: function (frm) {
//         frappe.call({
//             method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.create_CSID",
//             args: {
//                 "company_abbr": frm.doc.abbr
//             },
//             callback: function (r) {
//                 if (!r.exc) {
//                     frm.save();
//                 }
//             },
//         });
//     },
//     custom_create_csr: function (frm) {
//         frappe.call({
//             method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.create_csr",
//             args: {
//                 "portal_type": frm.doc.custom_select,
//                 "company_abbr": frm.doc.abbr
//             },
//             callback: function (r) {
//                 if (!r.exc) {
//                     frm.save();
//                 }
//             },
//         });
//     },
//     custom_check_compliance: function (frm) {
//         frappe.call({
//             method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.zatca_Call_compliance",
//             args: {
//                 "invoice_number": frm.doc.custom_sample_invoice_to_test,
//                 "compliance_type": "1",
//                 "company_abbr": frm.doc.abbr
//             },
//             callback: function (r) {
//                 if (!r.exc) {
//                     frm.save();
//                 }
//             },
//         });
//     }
// });
frappe.ui.form.on("Company", {
    refresh(frm) {
        // Refresh logic if any
    },
    custom_generate_production_csids: function (frm) {
        
        frappe.call({
            method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.production_CSID",
            args: {
                "company_abbr": frm.doc.abbr
            },
            callback: function (r) {
                if (!r.exc) {
                    frm.save();
                }
            },
        });
    },
    custom_generate_compliance_csid: function (frm) {
        
        frappe.call({
            method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.create_CSID",
            args: {
                "portal_type": frm.doc.custom_select,
                "company_abbr": frm.doc.abbr
            },
            callback: function (r) {
                if (!r.exc) {
                    frm.save();
                }
            },
        });
    },
    custom_create_csr: function (frm) {
        
        frappe.call({
            method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.create_csr",
            args: {
                "portal_type": frm.doc.custom_select,
                "company_abbr": frm.doc.abbr
            },
            callback: function (r) {
                if (!r.exc) {
                    frm.save();
                }
            },
        });
    },
    custom_check_compliance: function (frm) {

        frappe.call({
            method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.zatca_Call_compliance",
            args: {
                "invoice_number": frm.doc.custom_sample_invoice_number_to_test,
                "compliance_type": "1",
                "company_abbr": frm.doc.abbr
            },
            callback: function (r) {
                if (!r.exc) {
                    frm.save();
                }
            },
        });
    }
});
