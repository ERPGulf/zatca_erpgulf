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
            method: "zatca_erpgulf.zatca_erpgulf.sign_invoice_first.production_csid",
            args: {
                "zatca_doc": {
                    "doctype": frm.doc.doctype,
                    "name": frm.doc.name
                },
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
            method: "zatca_erpgulf.zatca_erpgulf.sign_invoice_first.create_csid",
            args: {
                "zatca_doc": {
                    "doctype": frm.doc.doctype, // Pass the doctype dynamically
                    "name": frm.doc.name       // Pass the document name dynamically
                },
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
            method: "zatca_erpgulf.zatca_erpgulf.sign_invoice_first.create_csr",
            args: {
                "zatca_doc": {
                    "doctype": frm.doc.doctype, // Pass the doctype dynamically
                    "name": frm.doc.name       // Pass the document name dynamically
                },
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
            method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.zatca_call_compliance",
            args: {
                "invoice_number": frm.doc.custom_sample_invoice_number_to_test,
                "compliance_type": "1",
                "company_abbr": frm.doc.abbr
            },
            callback: function (r) {
                if (!r.exc) {
                    // frm.save();
                }
            },
        });

    }
});
