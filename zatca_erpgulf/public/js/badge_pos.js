frappe.ui.form.on('POS Invoice', {
    refresh(frm) {
        console.log("POS Invoice Form refreshed!");
        frm.set_df_property('custom_zatca_status_notification', 'options', ' ');

        if (!frm.doc.custom_zatca_full_response) {
            console.log('No ZATCA response found.');
            return;
        }

        try {
            let responseText = frm.doc.custom_zatca_full_response;
            console.log("custom_zatca_full_response:", responseText);

            // ✅ Case 1: Plain text "NOT SUBMITTED"
            if (responseText.trim().toUpperCase() === "NOT SUBMITTED") {
                console.log("Detected NOT SUBMITTED → Show Failed badge");
                let badgeHtml = `
                    <div class="zatca-badge-container">
                        <img src="/assets/zatca_erpgulf/js/badges/zatca-failed.png"
                             alt="Failed" class="zatca-badge" width="110" height="36"
                             style="margin-top: -5px; margin-left: 380px;">
                    </div>`;
                frm.set_df_property('custom_zatca_status_notification', 'options', badgeHtml);
                frm.refresh_field('custom_zatca_status_notification');
                return;
            }

            // ✅ Case 2: Response contains "Error"
            if (responseText.trim().toUpperCase().startsWith("ERROR")) {
                console.log("Detected ERROR response → Show Failed badge");
                let badgeHtml = `
                    <div class="zatca-badge-container">
                        <img src="/assets/zatca_erpgulf/js/badges/zatca-failed.png"
                             alt="Failed" class="zatca-badge" width="110" height="36"
                             style="margin-top: -5px; margin-left: 380px;">
                    </div>`;
                frm.set_df_property('custom_zatca_status_notification', 'options', badgeHtml);
                frm.refresh_field('custom_zatca_status_notification');
                return;
            }

            // ✅ Case 3: Parse JSON response
            let jsonMatch = responseText.match(/ZATCA Response: ({.*})/);
            if (!jsonMatch) throw "No JSON found in ZATCA response!";
            let zatcaResponse = JSON.parse(jsonMatch[1]);

            const validationResults = zatcaResponse.validationResults || {};
            let errors = Array.isArray(validationResults.errorMessages) ? validationResults.errorMessages : [];
            const warnings = Array.isArray(validationResults.warningMessages) ? validationResults.warningMessages : [];
            const reportingStatus = frm.doc.custom_zatca_status || ''; // CLEARED / REPORTED

            // Filter duplicate-invoice errors (not critical)
            errors = errors.filter(e => !(e.code === "Invoice-Errors" && e.category === "Duplicate-Invoice"));

            console.log("Errors:", errors);
            console.log("Warnings:", warnings);
            console.log("Reporting Status:", reportingStatus);

            // ✅ Decide final status manually
            let finalStatus = 'PASS';
            if (errors.length > 0) {
                finalStatus = 'FAILED';
            } else if (warnings.length > 0) {
                finalStatus = 'WARNING';
            }

            console.log("Final Status decided:", finalStatus);

            let badgeHtml = '';

            // 🔴 FAILED Badge
            if (finalStatus === 'FAILED') {
                badgeHtml = `
                    <div class="zatca-badge-container">
                        <img src="/assets/zatca_erpgulf/js/badges/zatca-failed.png"
                             alt="Failed" class="zatca-badge" width="110" height="36"
                             style="margin-top: -5px; margin-left: 380px;">
                    </div>`;
            }

            // 🟡 WARNING Badge
            else if (finalStatus === 'WARNING') {
                if (reportingStatus === 'CLEARED') {
                    badgeHtml = `
                        <div class="zatca-badge-container">
                            <img src="/assets/zatca_erpgulf/js/badges/zatca-cleared-warning.png"
                                 alt="Cleared with Warning" class="zatca-badge" width="110" height="36"
                                 style="margin-top: -5px; margin-left: 380px;">
                        </div>`;
                } else if (reportingStatus === 'REPORTED') {
                    badgeHtml = `
                        <div class="zatca-badge-container">
                            <img src="/assets/zatca_erpgulf/js/badges/zatca-reported-warning.png"
                                 alt="Reported with Warning" class="zatca-badge" width="110" height="36"
                                 style="margin-top: -5px; margin-left: 380px;">
                        </div>`;
                }
            }

            // 🟢 PASS Badge
            else if (finalStatus === 'PASS') {
                if (reportingStatus === 'CLEARED') {
                    badgeHtml = `
                        <div class="zatca-badge-container">
                            <img src="/assets/zatca_erpgulf/js/badges/zatca-cleared.png"
                                 alt="Cleared" class="zatca-badge" width="110" height="36"
                                 style="margin-top: -5px; margin-left: 380px;">
                        </div>`;
                } else if (reportingStatus === 'REPORTED') {
                    badgeHtml = `
                        <div class="zatca-badge-container">
                            <img src="/assets/zatca_erpgulf/js/badges/zatca-reported.png"
                                 alt="Reported" class="zatca-badge" width="110" height="36"
                                 style="margin-top: -5px; margin-left: 380px;">
                        </div>`;
                }
            }

            frm.set_df_property('custom_zatca_status_notification', 'options', badgeHtml);
            frm.refresh_field('custom_zatca_status_notification');

        } catch (error) {
            console.error("Error handling ZATCA response:", error);
            frm.set_df_property('custom_zatca_status_notification', 'options', '');
            frm.refresh_field('custom_zatca_status_notification');
        }
    }
});



// frappe.ui.form.on('POS Invoice', {
//     refresh(frm) {
//         console.log("Form refreshed!");
//         frm.set_df_property('custom_zatca_status_notification', 'options', ' ');

//         if (frm.doc.custom_zatca_full_response) {
//             try {
//                 console.log("custom_zatca_full_response found:", frm.doc.custom_zatca_full_response);
//                 let ztcaresponse = frm.doc.custom_zatca_full_response;

//         // ✅ Check if the response starts with "Error"
//                 if (ztcaresponse.trim().toUpperCase() === "NOT SUBMITTED") {
//                     console.log("Error detected in ZATCA response. Displaying Failed badge.");
//                     let badgeHtml = '<div class="zatca-badge-container"><img src="/assets/zatca_erpgulf/js/badges/zatca-failed.png" alt="Failed" class="zatca-badge" width="110" height="36" style="margin-top: -5px; margin-left: 380px;"></div>';
//                     frm.set_df_property('custom_zatca_status_notification', 'options', badgeHtml);
//                     frm.refresh_field('custom_zatca_status_notification');
//                     return; // Exit since it's an error
//                 }
            
//                 let zatcaResponse = JSON.parse(ztcaresponse.match(/ZATCA Response: ({.*})/)[1]);

//                 const validationResults = zatcaResponse.validationResults || {};
//                 const status = validationResults.status; // PASS/WARNINGAILED

//                 // Use reporting status from custom_zatca_status field
//                 const reportingStatus = frm.doc.custom_zatca_status || ''; // Cleared/Reported
//                 const warnings = validationResults.warningMessages || [];

//                 console.log("Validation Status:", status);
//                 console.log("Reporting Status (from custom_zatca_status):", reportingStatus);
//                 console.log("Warnings:", warnings);

//                 let badgeHtml = ''; // Placeholder for image HTML

//                 // 🟢 PASS Conditions
//                 if (status === 'PASS') {
//                     if (reportingStatus === 'CLEARED') {
//                         console.log('PASS - Cleared');
//                         badgeHtml = '<div class="zatca-badge-container"><img src="/assets/zatca_erpgulf/js/badges/zatca-cleared.png" alt="Cleared" class="zatca-badge" width="110" height="36" style="margin-top: -5px; margin-left: 380px;"></div>';

//                     } else if (reportingStatus === 'REPORTED') {
//                         console.log('PASS - Reported');
//                         badgeHtml = '<div class="zatca-badge-container"><img src="/assets/zatca_erpgulf/js/badges/zatca-reported.png" alt="Reported" class="zatca-badge" width="110" height="36" style="margin-top: -5px; margin-left: 380px;"></div>';
//                     }
//                 }

//                 // 🟡 WARNING Conditions
//                 else if (status === 'WARNING') {
//                     if (reportingStatus === 'CLEARED') {
//                         console.log('WARNING - Cleared with Warning');
//                         badgeHtml = '<div class="zatca-badge-container"><img src="/assets/zatca_erpgulf/js/badges/zatca-cleared-warning.png" alt="Cleared with Warning" class="zatca-badge" width="110" height="36" style="margin-top: -5px; margin-left: 380px;"></div>';
//                     } else if (reportingStatus === 'REPORTED') {
//                         console.log('WARNING - Reported with Warning');
//                         badgeHtml = '<div class="zatca-badge-container"><img src="/assets/zatca_erpgulf/js/badges/zatca-reported-warning.png" alt="Reported with Warning" class="zatca-badge" width="110" height="36" style="margin-top: -5px; margin-left: 380px;"></div>';
//                     }
//                 }

//                 // 🔴 FAILED Condition
//                 else {
//                     console.log('FAILED');
//                     badgeHtml = '<div class="zatca-badge-container"><img src="/assets/zatca_erpgulf/js/badges/zatca-failed.png" alt="Failed" class="zatca-badge" width="110" height="36" style="margin-top: -5px; margin-left: 250px;"></div>';
//                 }

//                 // Set Badge or Clear if None
//                 if (badgeHtml) {
//                     frm.set_df_property('custom_zatca_status_notification', 'options', badgeHtml);
//                 } else {
//                     console.log('No matching condition. Clearing badge.');
//                     frm.set_df_property('custom_zatca_status_notification', 'options', '');
//                 }

//             } catch (error) {
//                 console.error('Error parsing custom_zatca_full_response:', error);
//                 frm.set_df_property('custom_zatca_status_notification', 'options', '');
//             }
//         } else {
//             console.log('No custom_zatca_full_response found.');
//             frm.set_df_property('custom_zatca_status_notification', 'options', ' ');
//         }

//         frm.refresh_field('custom_zatca_status_notification');

//         // Add custom CSS for side placement
//         // frappe.utils.add_custom_styles(`
//         //     <style>
//         //         .zatca-badge-container {
//         //             position: absolute;
//         //             top: 5px; /* Adjusted for smaller size */
//         //             right: -15px; /* Fine-tuned positioning */
//         //             transform: rotate(45deg);
//         //             z-index: 9999;
//         //         }
//         //         .zatca-badge {
//         //             width: 50px !important; /* Force reduced size */
//         //             max-width: 50px !important; /* Limit width */
//         //             height: auto !important; /* Maintain aspect ratio */
//         //             box-shadow: 0 2px 4px rgba(0,0,0,0.3);
//         //         }
//         //     </style>
//         // `);
    
        
//     }
// });
