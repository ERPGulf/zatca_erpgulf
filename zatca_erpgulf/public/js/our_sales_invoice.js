
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

// Listen for the event to hide the GIF
frappe.realtime.on('hide_gif', () => {
    $('#custom-gif-overlay').remove();
});

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

    }
});

frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        const css = `
            .popover-content {
                font-family: Arial, sans-serif;
                background-color: #f9f9f9;
                color: #007bff; /* Blue text */
                border: 1px solid #cfe2f3;
                border-radius: 8px;
                padding: 15px;
                max-width: 300px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }

            .popover-title {
                font-size: 16px;
                font-weight: bold;
                color: #0056b3; /* Darker blue for the title */
                margin-bottom: 10px;
            }

            .popover-body {
                font-size: 14px;
                line-height: 1.6;
                color: #007bff;
            }
        `;
        $('<style>').text(css).appendTo('head'); // Add the CSS dynamically

        // Attach popover to the "subject" field
        const attachPopover = (fieldname, title, body) => {
            setTimeout(() => {
                $(`[data-fieldname="${fieldname}"]`).popover({
                    trigger: 'hover',
                    placement: 'top',
                    content: `
                        <div class="popover-content">
                            <h4 class="popover-title">${title}</h4>
                            <p class="popover-body">${body}</p>
                        </div>
                    `,
                    html: true
                });
            }, 500);
        };

        // Attach popovers to specific fields
        attachPopover(
            "custom_zatca_third_party_invoice",
            "Zatca 3rd Party Invoice",
            "An external party such as an accounting firm can issue invoices on behalf of the seller after fulfilling specific requirements as mentioned in the VAT legislation."
        );

        attachPopover(
            "custom_zatca_nominal_invoice",
            "Zatca NOMINAL Invoice",
            "A taxable person provides goods or services to a customer at no cost or at a reduced price, typically as part of a promotional activity."
        );
        attachPopover(
            "custom_zatca_export_invoice",
            "Zatca EXPORT Invoice",
            "The supplier and customer both intend that the goods are transported outside the GCC territory as a consequence of that supply."
        );
        attachPopover(
            "custom_summary_invoice",
            "Zatca SUMMARY Invoice",
            "Summary tax invoices are issued where there is more than one supply of goods or services."
        );
        attachPopover(
            "custom_self_billed_invoice",
            "Zatca SELF-BILLED Invoice",
            "Self-billing is a case where the buyer raises a tax invoice for the goods and services received on behalf of the vendor."
        );

    }
});

