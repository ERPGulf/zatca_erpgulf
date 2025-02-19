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
frappe.ui.form.on('Sales Invoice', {
    refresh(frm) {
        console.log("Form refreshed!");
        frm.set_df_property('custom_zatca_status_notification', 'options', ' ');
        // Check if the custom_zatca_full_response field is not empty
        if (frm.doc.custom_zatca_full_response) {
            try {
                // Parse the response to JSON
                console.log("custom_zatca_full_response found:", frm.doc.custom_zatca_full_response);
                let ztcaresponse = frm.doc.custom_zatca_full_response;
                let zatcaResponse = JSON.parse(ztcaresponse.match(/Zatca Response: ({.*})/)[1]);
                // Extract relevant data for validation
                const validationResults = zatcaResponse.validationResults || {};
                const status = validationResults.status;
                const warnings = validationResults.warningMessages || [];
                console.log(validationResults)
                console.log(status)
                console.log(warnings)
                // Check for status 'PASS' and no warnings
                if (status === 'PASS' && warnings.length === 0) {
                    console.log('pass')
                    const tableHtml = '<img src="/private/files/z1.png" alt="ZATCA Valid" width="100" height="33" style="margin-top: -250px; margin-left: 200px; ">';
                    frm.set_df_property('custom_zatca_status_notification', 'options', tableHtml);
                }
                if (status === 'WARNING' && warnings.length > 0) {
                    console.log('warn')
                   const tableHtml = '<img src="/private/files/z-WARN.png" alt="ZATCA Valid" width="100" height="33" style="margin-top: -250px; margin-left: 200px; ">';
                    frm.set_df_property('custom_zatca_status_notification', 'options', tableHtml);
                }
            } catch (error) {
                console.error('Error parsing custom_zatca_full_response:', error);
                // Clear the image in case of an error
                frm.set_df_property('custom_zatca_status_notification', 'options', '');
            }
        } else {
            // Clear the image if custom_zatca_full_response is empty
            console.log('oth')
            frm.set_df_property('custom_zatca_status_notification', 'options', ' ');
            frm.refresh_field('custom_zatca_status_notification');
        }
        // Refresh the field
        frm.refresh_field('custom_zatca_status_notification');
    }
});