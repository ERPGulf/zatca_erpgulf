function applyTooltips(context, fieldsWithTooltips) {
    fieldsWithTooltips.forEach((field) => {
        let fieldContainer;
        if (context.fields_dict && context.fields_dict[field.fieldname]) {
            fieldContainer = context.fields_dict[field.fieldname];
        }
        else if (context.dialog && context.dialog.fields_dict && context.dialog.fields_dict[field.fieldname]) {
            fieldContainer = context.dialog.fields_dict[field.fieldname];
        }
        else if (context.page) {
            fieldContainer = $(context.page).find(`[data-fieldname="${field.fieldname}"]`).closest('.frappe-control');
        }
        if (!fieldContainer) {
            console.error(`Field '${field.fieldname}' not found in the provided context.`);
            return;
        }
        const fieldWrapper = fieldContainer.$wrapper || $(fieldContainer); // Handle both Doctype/Dialog and Page contexts
        if (!fieldWrapper || fieldWrapper.length === 0) {
            console.error(`Field wrapper for '${field.fieldname}' not found.`);
            return;
        }
        let labelElement;
        if (fieldWrapper.find('label').length > 0) {
            labelElement = fieldWrapper.find('label').first();
        } else if (fieldWrapper.find('.control-label').length > 0) {
            labelElement = fieldWrapper.find('.control-label').first();
        }
        if (!labelElement && (context.dialog || context.page)) {
            labelElement = fieldWrapper.find('.form-control').first();
        }

        if (!labelElement || labelElement.length === 0) {
            console.error(`Label for field '${field.fieldname}' not found.`);
            return;
        }
        const tooltipContainer = labelElement.next('.tooltip-container');
        if (tooltipContainer.length === 0) {
            const tooltip = new Tooltip({
                containerClass: "tooltip-container",
                tooltipClass: "custom-tooltip",
                iconClass: "info-icon",
                text: field.text,
                links: field.links,
            });
            tooltip.renderTooltip(labelElement[0]);
        }
    });
}
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
        const fieldsWithTooltips = [
            {
                fieldname: "custom_zatca_third_party_invoice",
                text: `
                    An external party such as an accounting firm can issue invoices on behalf of the seller after fulfilling specific requirements as mentioned in the VAT legislation.
                `,
                links: [
                    "https://example.com/view-inventory",
                    "https://cloud.erpgulf.com/blog/news/zatca-sdk-v334-release-notes",
                ],
            },
            {
                fieldname: "custom_zatca_nominal_invoice",
                text: `
                    A taxable person provides goods or services to a customer at no cost or at a reduced price, typically as part of a promotional activity.
                `,
                links: [
                    "https://example.com/view-inventory",
                    "https://cloud.erpgulf.com/blog/news/zatca-sdk-v334-release-notes",
                ],
            },
            {
                fieldname: "custom_zatca_export_invoice",
                text: `
                    The supplier and customer both intend that the goods are transported outside the GCC territory as a consequence of that supply.
                `,
                links: [
                    "https://example.com/view-inventory",
                    "https://cloud.erpgulf.com/blog/news/zatca-sdk-v334-release-notes",
                ],
            },
            {
                fieldname: "custom_summary_invoice",
                text: `
                    Summary tax invoices are issued where there is more than one supply of goods or services.
                `,
                links: [
                    "https://example.com/view-inventory",
                    "https://cloud.erpgulf.com/blog/news/zatca-sdk-v334-release-notes",
                ],
            },
            {
                fieldname: "custom_self_billed_invoice",
                text: `
                    Self-billing is a case where the buyer raises a tax invoice for the goods and services received on behalf of the vendor.
                `,
                links: [
                    "https://example.com/view-inventory",
                    "https://cloud.erpgulf.com/blog/news/zatca-sdk-v334-release-notes",
                ],
            },
        ];
        applyTooltips(frm, fieldsWithTooltips);
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
        
    }
});

