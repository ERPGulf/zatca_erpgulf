// frappe.ui.form.on('Sales Invoice', {
//     refresh(frm) {
//         // Clear previous content
//         frm.set_df_property('custom_zatca_status_notification', 'options', ' ');

//         // Handle different statuses
//         if (frm.doc.custom_zatca_status) {
//             let status = frm.doc.custom_zatca_status;
//             let badgeHtml = '';

//             if (status === 'Not Submitted') {
//                 // Do nothing
//                 return;
//             } else if (status === 'Cleared') {
//                 badgeHtml = '<span class="badge badge-success">Cleared</span>';
//             } else if (status === 'Reported') {
//                 badgeHtml = '<span class="badge badge-primary">Reported</span>';
//             } else if (status === 'Cleared with Warnings') {
//                 badgeHtml = '<span class="badge badge-warning">Cleared with Warnings</span>';
//             } else if (status === 'Reported with Warnings') {
//                 badgeHtml = '<span class="badge badge-danger">Reported with Warnings</span>';
//             }

//             frm.set_df_property('custom_zatca_status_notification', 'options', badgeHtml);
//         }

//         // Check if the custom_zatca_full_response field is not empty
//         if (frm.doc.custom_zatca_full_response) {
//             try {
//                 let ztcaresponse = frm.doc.custom_zatca_full_response;
//                 let zatcaResponse = JSON.parse(ztcaresponse.match(/Zatca Response: ({.*})/)[1]);

//                 const validationResults = zatcaResponse.validationResults || {};
//                 const status = validationResults.status;
//                 const warnings = validationResults.warningMessages || [];

//                 console.log(validationResults);
//                 console.log(status);
//                 console.log(warnings);

//                 // Display images based on validation results
//                 if (status === 'PASS' && warnings.length === 0) {
//                     console.log('Pass');
//                     frm.set_df_property('custom_zatca_status_notification', 'options', 
//                         '<img src="/private/files/z1.png" alt="ZATCA Valid" width="100" height="33" style="margin-top: -250px; margin-left: 200px;">');
//                 }
//                 if (status === 'WARNING' && warnings.length > 0) {
//                     console.log('Warning');
//                     frm.set_df_property('custom_zatca_status_notification', 'options', 
//                         '<img src="/private/files/z-WARN.png" alt="ZATCA Warning" width="100" height="33" style="margin-top: -250px; margin-left: 200px;">');
//                 }
//             } catch (error) {
//                 console.error('Error parsing custom_zatca_full_response:', error);
//                 frm.set_df_property('custom_zatca_status_notification', 'options', '');
//             }
//         } else {
//             console.log('No response');
//             frm.set_df_property('custom_zatca_status_notification', 'options', ' ');
//         }

//         // Refresh the field
//         frm.refresh_field('custom_zatca_status_notification');
//     }
// });
// frappe.ui.form.on('Sales Invoice', {
//     refresh(frm) {
//         console.log("Form refreshed!");
//         frm.set_df_property('custom_zatca_status_notification', 'options', ' ');
//         // Check if the custom_zatca_full_response field is not empty
//         if (frm.doc.custom_zatca_full_response) {
//             try {
//                 // Parse the response to JSON
//                 console.log("custom_zatca_full_response found:", frm.doc.custom_zatca_full_response);
//                 let ztcaresponse = frm.doc.custom_zatca_full_response;
//                 let zatcaResponse = JSON.parse(ztcaresponse.match(/Zatca Response: ({.*})/)[1]);
//                 // Extract relevant data for validation
//                 const validationResults = zatcaResponse.validationResults || {};
//                 const status = validationResults.status;
//                 const warnings = validationResults.warningMessages || [];
//                 console.log(validationResults)
//                 console.log(status)
//                 console.log(warnings)
//                 // Check for status 'PASS' and no warnings
//                 if (status === 'PASS' && warnings.length === 0) {
//                     console.log('pass')
//                     const tableHtml = '<img src="/private/files/z1.png" alt="ZATCA Valid" width="100" height="33" style="margin-top: -250px; margin-left: 200px; ">';
//                     frm.set_df_property('custom_zatca_status_notification', 'options', tableHtml);
//                 }
//                 if (status === 'WARNING' && warnings.length > 0) {
//                     console.log('warn')
//                    const tableHtml = '<img src="/private/files/z-WARN.png" alt="ZATCA Valid" width="100" height="33" style="margin-top: -250px; margin-left: 200px; ">';
//                     frm.set_df_property('custom_zatca_status_notification', 'options', tableHtml);
//                 }
//             } catch (error) {
//                 console.error('Error parsing custom_zatca_full_response:', error);
//                 // Clear the image in case of an error
//                 frm.set_df_property('custom_zatca_status_notification', 'options', '');
//             }
//         } else {
//             // Clear the image if custom_zatca_full_response is empty
//             console.log('oth')
//             frm.set_df_property('custom_zatca_status_notification', 'options', ' ');
//             frm.refresh_field('custom_zatca_status_notification');
//         }
//         // Refresh the field
//         frm.refresh_field('custom_zatca_status_notification');
//     }
// });
frappe.ui.form.on('Sales Invoice', {
    refresh(frm) {
        console.log("Form refreshed!");
        frm.set_df_property('custom_zatca_status_notification', 'options', ' ');

        if (frm.doc.custom_zatca_full_response) {
            try {
                console.log("custom_zatca_full_response found:", frm.doc.custom_zatca_full_response);
                let ztcaresponse = frm.doc.custom_zatca_full_response;

        // ✅ Check if the response starts with "Error"
                if (ztcaresponse.trim().toUpperCase().startsWith("ERROR")) {
                    console.log("Error detected in ZATCA response. Displaying Failed badge.");
                    let badgeHtml = '<div class="zatca-badge-container"><img src="/private/files/zatca-failed.png" alt="Failed" class="zatca-badge" width="110" height="36" style="margin-top: -5px; margin-left: 215px;"></div>';
                    frm.set_df_property('custom_zatca_status_notification', 'options', badgeHtml);
                    frm.refresh_field('custom_zatca_status_notification');
                    return; // Exit since it's an error
                }
            
                let zatcaResponse = JSON.parse(ztcaresponse.match(/Zatca Response: ({.*})/)[1]);

                const validationResults = zatcaResponse.validationResults || {};
                const status = validationResults.status; // PASS/WARNINGAILED

                // Use reporting status from custom_zatca_status field
                const reportingStatus = frm.doc.custom_zatca_status || ''; // Cleared/Reported
                const warnings = validationResults.warningMessages || [];

                console.log("Validation Status:", status);
                console.log("Reporting Status (from custom_zatca_status):", reportingStatus);
                console.log("Warnings:", warnings);

                let badgeHtml = ''; // Placeholder for image HTML

                // 🟢 PASS Conditions
                if (status === 'PASS') {
                    if (reportingStatus === 'CLEARED') {
                        console.log('PASS - Cleared');
                        badgeHtml = '<div class="zatca-badge-container"><img src="/assets/zatca_erpgulf/js/badges/zatca-cleared.png" alt="Cleared" class="zatca-badge" width="110" height="36" style="margin-top: -5px; margin-left: 215px;"></div>';

                    } else if (reportingStatus === 'REPORTED') {
                        console.log('PASS - Reported');
                        badgeHtml = '<div class="zatca-badge-container"><img src="/assets/zatca_erpgulf/js/badges/zatca-reported.png" alt="Reported" class="zatca-badge" width="110" height="36" style="margin-top: -5px; margin-left: 215px;"></div>';
                    }
                }

                // 🟡 WARNING Conditions
                else if (status === 'WARNING') {
                    if (reportingStatus === 'CLEARED') {
                        console.log('WARNING - Cleared with Warning');
                        badgeHtml = '<div class="zatca-badge-container"><img src="/assets/zatca_erpgulf/js/badges/zatca-cleared-warning.png" alt="Cleared with Warning" class="zatca-badge" width="110" height="36" style="margin-top: -5px; margin-left: 215px;"></div>';
                    } else if (reportingStatus === 'REPORTED') {
                        console.log('WARNING - Reported with Warning');
                        badgeHtml = '<div class="zatca-badge-container"><img src="/assets/zatca_erpgulf/js/badges/zatca-reported-warning.png" alt="Reported with Warning" class="zatca-badge" width="110" height="36" style="margin-top: -5px; margin-left: 215px;"></div>';
                    }
                }

                // 🔴 FAILED Condition
                else {
                    console.log('FAILED');
                    badgeHtml = '<div class="zatca-badge-container"><img src="/assets/zatca_erpgulf/js/badges/zatca-failed.png" alt="Failed" class="zatca-badge" width="110" height="36" style="margin-top: -5px; margin-left: 215px;"></div>';
                }

                // Set Badge or Clear if None
                if (badgeHtml) {
                    frm.set_df_property('custom_zatca_status_notification', 'options', badgeHtml);
                } else {
                    console.log('No matching condition. Clearing badge.');
                    frm.set_df_property('custom_zatca_status_notification', 'options', '');
                }

            } catch (error) {
                console.error('Error parsing custom_zatca_full_response:', error);
                frm.set_df_property('custom_zatca_status_notification', 'options', '');
            }
        } else {
            console.log('No custom_zatca_full_response found.');
            frm.set_df_property('custom_zatca_status_notification', 'options', ' ');
        }

        frm.refresh_field('custom_zatca_status_notification');

        // Add custom CSS for side placement
        // frappe.utils.add_custom_styles(`
        //     <style>
        //         .zatca-badge-container {
        //             position: absolute;
        //             top: 5px; /* Adjusted for smaller size */
        //             right: -15px; /* Fine-tuned positioning */
        //             transform: rotate(45deg);
        //             z-index: 9999;
        //         }
        //         .zatca-badge {
        //             width: 50px !important; /* Force reduced size */
        //             max-width: 50px !important; /* Limit width */
        //             height: auto !important; /* Maintain aspect ratio */
        //             box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        //         }
        //     </style>
        // `);
    
        
    }
});
