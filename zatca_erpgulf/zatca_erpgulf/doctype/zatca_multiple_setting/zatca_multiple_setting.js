// // Copyright (c) 2024, ERPGulf and contributors
// // For license information, please see license.txt

// // frappe.ui.form.on("ZATCA Multiple Setting", {
// // 	refresh(frm) {

// // 	},
// // });
// frappe.ui.form.on("ZATCA Multiple Setting", {
//     refresh(frm) {
//         // Refresh logic if any
//     },
//     custom_generate_production_csids: function (frm) {
        
//         frappe.call({
//             method: "zatca_erpgulf.zatca_erpgulf.sign_invoice_first.production_csid",
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
//             method: "zatca_erpgulf.zatca_erpgulf.sign_invoice_first.create_csid",
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
//     custom_create_csr: function (frm) {
        
//         frappe.call({
//             method: "zatca_erpgulf.zatca_erpgulf.sign_invoice_first.create_csr",
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
//             method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.zatca_call_compliance",
//             args: {
//                 "invoice_number": frm.doc.custom_sample_invoice_number_to_test,
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
frappe.ui.form.on("ZATCA Multiple Setting", {
    refresh(frm) {
        // Refresh logic if any
    },
    custom_generate_final_csids: function (frm) {
        if (!frm.doc.custom_linked_doctype) {
            frappe.msgprint(__('Please select a linked doctype.'));
            return;
        }

        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Company",
                name: frm.doc.custom_linked_doctype
            },
            callback: function (data) {
                if (data.message) {
                    frappe.call({
                        method: "zatca_erpgulf.zatca_erpgulf.sign_invoice_first.production_csid",
                        args: {
                                "zatca_doc": {
                                    "doctype": frm.doc.doctype,
                                    "name": frm.doc.name
                                },
                            "company_abbr": data.message.abbr
                        },
                        callback: function (r) {
                            if (!r.exc) {
                                frm.save();
                            }
                        },
                    });
                }
            }
        });
    },
    custom_generate_compliance_csid: function (frm) {
        if (!frm.doc.custom_linked_doctype) {
            frappe.msgprint(__('Please select a linked doctype.'));
            return;
        }

        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Company",
                name: frm.doc.custom_linked_doctype
            },
            callback: function (data) {
                if (data.message) {
                    frappe.call({
                        method: "zatca_erpgulf.zatca_erpgulf.sign_invoice_first.create_csid",
                        args: {
                            "zatca_doc": {
                                "doctype": frm.doc.doctype,
                                "name": frm.doc.name
                            },
                            "portal_type": data.message.custom_select,
                            "company_abbr": data.message.abbr
                        },
                        callback: function (r) {
                            if (!r.exc) {
                                frm.save();
                            }
                        },
                    });
                }
            }
        });
    },
    custom_create_csr: function (frm) {
        console.log("Custom CSR button clicked");
        if (!frm.doc.custom_linked_doctype) {
            frappe.msgprint(__('Please select a linked doctype.'));
            return;
        }
    
        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Company",
                name: frm.doc.custom_linked_doctype
            },
            callback: function (data) {
                console.log("Fetched company data:", data);
                if (data.message) {
                    frappe.call({
                        method: "zatca_erpgulf.zatca_erpgulf.sign_invoice_first.create_csr",
                        args: {
                            "zatca_doc": {
                                "doctype": frm.doc.doctype,
                                "name": frm.doc.name
                            },
                            "portal_type": data.message.custom_select,
                            "company_abbr": data.message.abbr
                        },
                        callback: function (r) {
                            console.log("CSR creation response:", r);
                            if (!r.exc) {
                                frappe.msgprint(__('CSR created successfully.'));
                                frm.save();
                            }
                        },
                    });
                } else {
                    frappe.msgprint(__('No company data found.'));
                }
            },
            error: function (error) {
                console.log("Error fetching company data:", error);
            }
        });
    } ,
    custom_check_compliance: function (frm) {
        if (!frm.doc.custom_linked_doctype) {
            frappe.msgprint(__('Please select a linked doctype.'));
            return;
        }

        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Company",
                name: frm.doc.custom_linked_doctype
            },
            callback: function (data) {
                if (data.message) {
                    frappe.call({
                        method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.zatca_call_compliance",
                        args: {
                            "invoice_number": frm.doc.custom_sample_invoice_number_to_test,
                            "compliance_type": "1",
                            "company_abbr": data.message.abbr,
                            "source_doc": frm.doc,
                        },
                        callback: function (r) {
                            if (!r.exc) {
                                frm.save();
                            }
                        },
                    });
                }
            }
        });
    }
});
