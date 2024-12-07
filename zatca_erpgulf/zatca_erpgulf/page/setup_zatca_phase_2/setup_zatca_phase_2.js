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
frappe.pages["setup-zatca-phase-2"].on_page_load = function (wrapper) {
	const unifiedTooltips = [
		{
			fieldname: "company_name",
			context: "dialog",
			text: "Your registered company name.",
			links: ["https://example.com/company-help"],
		},
		{
			fieldname: "otp",
			context: "dialog",
			text: "Enter the OTP received for verification.",
			links: ["https://example.com/otp-help"],
		},
		{
			fieldname: "integration_type",
			context: "dialog",
			text: "Provide your basic auth credentials here.",
			links: ["https://example.com/auth-help"],
		},
		{
			fieldname: "company",
			context: "dialog",
			text: "Enter the company information.",
			links: ["https://example.com/company-help"],
		},
		{
			fieldname: "vat_number",
			context: "dialog",
			text: "Provide the VAT number for your company.",
			links: ["https://example.com/vat-help"],
		},
		{
			fieldname: "building",
			context: "dialog",
			text: "Enter the building number or name.",
			links: ["https://example.com/building-help"],
		},
		{
			fieldname: "city",
			context: "dialog",
			text: "Enter the city name where the business is located.",
			links: ["https://example.com/city-help"],
		},
		{
			fieldname: "zip",
			context: "dialog",
			text: "Provide the ZIP or postal code.",
			links: ["https://example.com/zip-help"],
		},
		{
			fieldname: "business_category",
			context: "dialog",
			text: "Select the business category for your company.",
			links: ["https://example.com/business-category-help"],
		},
		{
			fieldname: "csr_config_box",
			context: "dialog",
			text: "Configure the CSR details in this box.",
			links: ["https://example.com/csr-config-help"],
		},
		
		{
			fieldname: "created_csr_config",
			context: "dialog",
			text: "View or manage your created CSR configurations.",
			links: ["https://example.com/created-csr-config-help"],
		},
		
		{
			fieldname: "basic_auth_from_csid",
			context: "dialog",
			text: "Provide the basic authentication credentials from your CSID.",
			links: ["https://example.com/basic-auth-from-csid-help"],
		},
		{
			fieldname: "invoice_number",
			context: "dialog",
			text: "Enter the invoice number for tracking purposes.",
			links: ["https://example.com/invoice-number-help"],
		},
		
	];
	

	var page = frappe.ui.make_app_page({
	  parent: wrapper,
	  title: "Setup Zatca Phase-2",
	  single_column: true,
	});
  
	let current_slide_index = 0;
	let selected_company = null;
	let current_dialog = null; 
	let new_dialog = null ;
	let slideData = {};

	const slides_settings = [
	  {
		name: "welcome",
		title: __("Zatca Phase 2 Wizard (ERPGulf)"),
		fields: [
		  {
			fieldtype: "HTML",
			options: `
			  <div style="text-align: center;">
				<img src="/assets/zatca_erpgulf/images/ERPGulf.png" alt="ERPGulf" style="max-width: 120px;">
				<h2>Zatca Phase 2 Wizard</h2>
				<p>Fill out the form carefully for successful Zatca Phase 2 Integration</p>
			  </div>
			`,
		  },
		],
		primary_action_label: __("Start"),
	  },
	  {
		name: "integration_type",
		title: __("Zatca Integration Type"),
		fields: [
		  {
			fieldname: "integration_type",
			label: __("Integration Type"),
			fieldtype: "Select",
			options: ["Simulation", "Sandbox", "Production"],
		  },
		],
		primary_action_label: __("Next"),
	  },
	  {
		name: "select_company",
		title: __("Select Company"),
		fields: [
		  {
			fieldname: "company",
			label: __("Select Company"),
			fieldtype: "Link",
			options: "Company",
			change: function () {
			  const company = this.get_value("company");
			  if (company) {
				selected_company = company;
			  }
			},
		  },
		],
		primary_action_label: __("Next"),
	  },
	  {
		name: "company_details",
		title: __("Company Details"),
		fields: [
		  {
			fieldname: "company_name",
			label: __("Company Name"),
			fieldtype: "Data",
			read_only: 1,
		  },
		  {
			fieldname: "vat_number",
			label: __("VAT Registration No"),
			fieldtype: "Data",
		  },
		  {
			fieldname: "building",
			label: __("Building Number"),
			fieldtype: "Data",
			read_only: 0,
		  },
		  { fieldname: "city", label: __("City"), fieldtype: "Data" },
		  { fieldname: "zip", label: __("ZIP Code"), fieldtype: "Data" },
		  {
			fieldname: "business_category",
			label: __("Select Business Category"),
			fieldtype: "Data",
			
		  },
		],
		primary_action_label: __("Next"),
	  },

	  
	  {
		name: "create_csr",
		title: __("Create CSR"),
		fields: [
			{
				fieldname: "csr_config_box",
				label: __("CSR Config"),
				fieldtype: "Small Text",
				read_only: 1,
			},
			{
				fieldname: "activate_csr",
				label: __("Create CSR"),
				fieldtype: "Button",
				click: function () {
					if (!selected_company) {
						frappe.msgprint(__("Please select a company before creating CSR."));
						return;
					}
			
					frappe.call({
						method: "frappe.client.get_value",
						args: {
							doctype: "Company",
							filters: { name: selected_company },
							fieldname: ["abbr"],
						},
						callback: function (res) {
							if (res && res.message) {
								const company_abbr = res.message.abbr;
			
								const integrationSlide = slides_settings.find(
									(slide) => slide.name === "integration_type"
								);
								const integrationField = integrationSlide?.fields.find(
									(field) => field.fieldname === "integration_type"
								);
								const portal_type = integrationField?.options
									? integrationField.options[0]
									: null;
			
								if (portal_type && company_abbr) {
									
									frappe.call({
										method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.create_csr",
										args: { portal_type, company_abbr },
										callback: function (response) {
											if (response && response.message) {
												// console.log("CSR Response:", response.message);
												
												const encodedString = response.message.trim();
												// console.log(encodedString)
												// frappe.msgprint(encodedString)
												if (current_dialog) {
														current_dialog.set_value("created_csr_config", encodedString);
														current_dialog.refresh();
														// frappe.msgprint(__("CSR data successfully updated in the field"));
													} else {
														frappe.msgprint(__("Dialog reference not found."));
													}

												} else {
												frappe.msgprint(__("Failed to create CSR. Please check the logs."));
											}
										},
									});
								} else {
									frappe.msgprint(__("Invalid portal type or company abbreviation."));
								}
							} else {
								frappe.msgprint(__("Failed to fetch company abbreviation."));
							}
						},
					});
				},
			},
			{
				fieldname: "created_csr_config",
				label: __("Generated CSR Data"),
				fieldtype: "Small Text",
			},
			
			  

		],
		primary_action_label: __("Next"),
		// Added primary action label
	}
	,
	  {
		name: "enter_otp",
		title: __("Enter OTP"),
		fields: [
		  {
			fieldname: "otp",
			label: __("OTP"),
			fieldtype: "Data",
		  },
		
		{
			fieldname: "activate_csid",
			label: __("Activate Compliance CSID"),
			fieldtype: "Button",
			click: function () {
				const otpValue = current_dialog.get_value("otp"); // Get the OTP value from the dialog
				if (!otpValue || otpValue.trim() === "") {
					frappe.msgprint(__("Please enter the OTP before proceeding."));
					return;
				}
		
				if (!selected_company) {
					frappe.msgprint(__("Please select a company before activating CSID."));
					return;
				}
		
				// Step 1: Save the OTP in the company document
				frappe.call({
					method: "frappe.client.set_value",
					args: {
						doctype: "Company",
						name: selected_company,
						fieldname: "custom_otp",
						value: otpValue.trim(),
					},
					callback: function (response) {
						if (response && response.message) {
							// frappe.msgprint(__("OTP saved successfully in the company document."));
		
							// Step 2: Fetch the company abbreviation
							frappe.call({
								method: "frappe.client.get_value",
								args: {
									doctype: "Company",
									filters: { name: selected_company },
									fieldname: ["abbr"],
								},
								callback: function (res) {
									if (res && res.message) {
										const company_abbr = res.message.abbr;
		
										// Safely fetch portal_type
										const integrationSlide = slides_settings.find(
											(slide) => slide.name === "integration_type"
										);
										const integrationField = integrationSlide?.fields.find(
											(field) => field.fieldname === "integration_type"
										);
										const portal_type = integrationField?.options
											? integrationField.options[0]
											: null;
		
										if (portal_type && company_abbr) {
											// Step 3: Generate CSID
											frappe.call({
												method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.create_CSID",
												args: { portal_type, company_abbr },
												callback: function (response) {
													if (response && response.message) {
														// console.log("Response: " + JSON.stringify(response, null, 2));
            
            // Use the response as a JSON string
            											const encodedString = response.message.trim();
														// console.log("Response: " + JSON.stringify(response, null, 2))
														// const encodedString = response.message.trim();
														// frappe.msgprint(__("CSID generated successfully."));
														if (current_dialog) {
															current_dialog.set_value("basic_auth_from_csid",encodedString);
															current_dialog.refresh();
														} else {
															frappe.msgprint(
																__("Dialog reference not found.")
															);
														}
													} else {
														frappe.msgprint(
															__("Failed to generate CSID. Please check the logs.")
														);
													}
												},
											});
										} else {
											frappe.msgprint(__("Invalid portal type or company abbreviation."));
										}
									} else {
										frappe.msgprint(__("Failed to fetch company abbreviation."));
									}
								},
							});
						} else {
							frappe.msgprint(__("Failed to save OTP. Please try again."));
						}
					},
				});
			},
		},
		
		  {
			fieldname: "basic_auth_from_csid",
			label: __("Basic Auth from CSID"),
			fieldtype: "Long Text",
		},
		],
		primary_action_label: __("Next"),
	  },
	  {
		name: "zatca_compliance_check",
		title: __("Zatca Compliance Check."),
		fields: [
			{
				fieldname: "invoice_number",
				label: __("Invoice Number"),
				fieldtype: "Data",
			},
			{
				fieldname: "simplified_invoice",
				label: __("Simplified Invoice"),
				fieldtype: "Check",
			},
			{
				fieldname: "standard_invoice",
				label: __("Standard Invoice"),
				fieldtype: "Check",
			},
			{
				fieldname: "simplified_credit_note",
				label: __("Simplified Credit Note"),
				fieldtype: "Check",
			},
			{
				fieldname: "standard_credit_note",
				label: __("Standard Credit Note"),
				fieldtype: "Check",
			},
			{
				fieldname: "simplified_debit_note",
				label: __("Simplified Debit Note"),
				fieldtype: "Check",
			},
			{
				fieldname: "standard_debit_note",
				label: __("Standard Debit Note"),
				fieldtype: "Check",
			},
			// {
			// 	fieldname: "check_compliance",
			// 	label: __("Check Compliance"),
			// 	fieldtype: "Button",
			// 	click: function () {
			// 		const invoiceValue = current_dialog.get_value("invoice_number"); // Get the OTP value from the dialog
			// 		if (!invoiceValue || invoiceValue.trim() === "") {
			// 			frappe.msgprint(__("Please enter the invoice number before proceeding."));
			// 			return;
			// 	}
			// 		if (!selected_company) {
			// 			frappe.msgprint(__("Please select a company before creating CSR."));
			// 			return;
			// 		}
			
			// 		// Fetch the company abbreviation
			// 		frappe.call({
			// 			method: "frappe.client.get_value",
			// 			args: {
			// 				doctype: "Company",
			// 				filters: { name: selected_company },
			// 				fieldname: ["abbr"],
			// 			},
			// 			callback: function (res) {
			// 				if (res && res.message) {
			// 					const company_abbr = res.message.abbr;
			// 					// Safely fetch portal_type
			// 					const complianceType = "1";
			// 					if (invoiceValue && company_abbr) {
			// 						// Create CSR
			// 						frappe.call({
			// 							method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.zatca_Call_compliance",
			// 							args: { invoice_number,complianceType, company_abbr },
			// 							callback: function (response) {
			// 								if (response && response.message) {
			// 									// console.log("CSR Response:", response.message);
			
			// 									const encodedString = response.message.trim();
			// 									frappe.msgprint(encodedString)
			// 									// Update the `created_csr_config` field in the dialog
												
			// 								} else {
			// 									frappe.msgprint(__("Failed to create CSID. Please check the logs."));
			// 								}
			// 							},
			// 						});
			// 					} else {
			// 						frappe.msgprint(__("Invalid portal type or company abbreviation."));
			// 					}
			// 				} else {
			// 					frappe.msgprint(__("Failed to fetch company abbreviation."));
			// 				}
			// 			},
			// 		});
			// 	},
				
			// },
			// {
			// 	fieldname: "check_compliance",
			// 	label: __("Check Compliance"),
			// 	fieldtype: "Button",
			// 	click: function () {
			// 		const invoiceValue = current_dialog.get_value("invoice_number"); // Get the invoice number
			// 		if (!invoiceValue || invoiceValue.trim() === "") {
			// 			frappe.msgprint(__("Please enter the invoice number before proceeding."));
			// 			return;
			// 		}
			
			// 		if (!selected_company) {
			// 			frappe.msgprint(__("Please select a company before running compliance checks."));
			// 			return;
			// 		}
			
			// 		// Fetch the company abbreviation
			// 		frappe.call({
			// 			method: "frappe.client.get_value",
			// 			args: {
			// 				doctype: "Company",
			// 				filters: { name: selected_company },
			// 				fieldname: ["abbr"],
			// 			},
			// 			callback: function (res) {
			// 				if (res && res.message) {
			// 					const company_abbr = res.message.abbr;
			
			// 					// Checkbox conditions to check one by one
			// 					const conditions = [
			// 						{ fieldname: "simplified_invoice", label: "Simplified Invoice", complianceType: "1" },
			// 						{ fieldname: "standard_invoice", label: "Standard Invoice", complianceType: "2" },
			// 						{ fieldname: "simplified_credit_note", label: "Simplified Credit Note", complianceType: "3" },
			// 						{ fieldname: "standard_credit_note", label: "Standard Credit Note", complianceType: "4" },
			// 						{ fieldname: "simplified_debit_note", label: "Simplified Debit Note", complianceType: "5" },
			// 						{ fieldname: "standard_debit_note", label: "Standard Debit Note", complianceType: "6" },
			// 					];
			
			// 					const processCondition = (index) => {
			// 						if (index >= conditions.length) {
			// 							frappe.msgprint(__("Compliance checks completed."));
			// 							return;
			// 						}
			
			// 						const condition = conditions[index];
			
			// 						// Call the API for the current condition
			// 						frappe.call({
			// 							method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.zatca_Call_compliance",
			// 							args: {
			// 								invoice_number: invoiceValue,
			// 								complianceType: condition.complianceType,
			// 								company_abbr: company_abbr,
			// 							},
			// 							callback: function (response) {
			// 								if (response && response.message ) {
			// 									// Condition passed
			// 									frappe.msgprint(__(`${condition.label} Passed.`));
			// 									current_dialog.set_value(condition.fieldname, 0); // Tick the checkbox
			// 								} else {
			// 									// Condition failed
			// 									frappe.msgprint(
			// 										__(`${condition.label} Not Passed. Reason: ${response.message || "Unknown error"}`)
			// 									);
			// 									current_dialog.set_value(condition.fieldname, 0); // Untick the checkbox
			// 								}
			// 								setTimeout(() => {
			// 									processCondition(index + 1); // Move to the next condition after the delay
			// 								}, 1000);
			
			// 								// Move to the next condition
			// 								//processCondition(index + 1);
			// 							},
			// 							error: function () {
			// 								// Handle API error
			// 								frappe.msgprint(__(`${condition.label} Not Passed. Reason: API Error.`));
			// 								current_dialog.set_value(condition.fieldname, 0); // Untick the checkbox
			
			// 								// Move to the next condition
			// 								processCondition(index + 1);
			// 							},
			// 						});
			// 					};
			
			// 					// Start checking conditions one by one
			// 					processCondition(0);
			// 				} else {
			// 					frappe.msgprint(__("Failed to fetch company abbreviation."));
			// 				}
			// 			},
			// 		});
			// 	},
			// }
			{
				fieldname: "check_compliance",
label: __("Check Compliance"),
fieldtype: "Button",
click: function () {
	const invoiceValue = current_dialog.get_value("invoice_number"); // Get the invoice number
	if (!invoiceValue || invoiceValue.trim() === "") {
		frappe.msgprint(__("Please enter the invoice number before proceeding."));
		return;
	}

	if (!selected_company) {
		frappe.msgprint(__("Please select a company before running compliance checks."));
		return;
	}

	// Fetch the company abbreviation
	frappe.call({
		method: "frappe.client.get_value",
		args: {
			doctype: "Company",
			filters: { name: selected_company },
			fieldname: ["abbr"],
		},
		callback: function (res) {
			if (res && res.message) {
				const company_abbr = res.message.abbr;

				// Compliance conditions
				const conditions = [
					{ fieldname: "simplified_invoice", label: "Simplified Invoice", complianceType: "1" },
					{ fieldname: "standard_invoice", label: "Standard Invoice", complianceType: "2" },
					{ fieldname: "simplified_credit_note", label: "Simplified Credit Note", complianceType: "3" },
					{ fieldname: "standard_credit_note", label: "Standard Credit Note", complianceType: "4" },
					{ fieldname: "simplified_debit_note", label: "Simplified Debit Note", complianceType: "5" },
					{ fieldname: "standard_debit_note", label: "Standard Debit Note", complianceType: "6" },
				];

				// Process each condition
				const processCondition = (index) => {
					if (index >= conditions.length) {
						frappe.msgprint(__("Compliance checks completed for invoice: " + invoiceValue));
						return;
					}

					const condition = conditions[index];

					// Call the API for the current condition
					frappe.call({
						method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.zatca_Call_compliance",
						args: {
							invoice_number: invoiceValue,
							complianceType: condition.complianceType,
							company_abbr: company_abbr,
						},
						callback: function (response) {
							if (response && response.message) {
								let clearanceStatus = response.message.clearanceStatus;
								let reportingStatus = response.message.reportingStatus;

								// Check if clearanceStatus is "CLEARED" or reportingStatus is "REPORTED"
								if (clearanceStatus === "CLEARED" || reportingStatus === "REPORTED") {
									// Condition passed, tick the checkbox
									frappe.msgprint(__(`${condition.label} Passed for invoice: ${invoiceValue}`));
									current_dialog.set_value(condition.fieldname, 1); // Tick the checkbox (1 = ticked, 0 = unticked)
								} else {
									// Condition failed
									frappe.msgprint(
										__(`${condition.label} Not Passed for invoice: ${invoiceValue}. ClearanceStatus: ${clearanceStatus || 'N/A'}, ReportingStatus: ${reportingStatus || 'N/A'}`)
									);
									current_dialog.set_value(condition.fieldname, 0); // Untick the checkbox
								}

								// Move to the next condition after a small delay
								setTimeout(() => {
									processCondition(index + 1); 
								}, 1000);
							} else {
								// Handle empty response or failed response
								frappe.msgprint(
									__(`${condition.label} Not Passed for invoice: ${invoiceValue}. Reason: ${response.message || "Unknown error"}`)
								);
								current_dialog.set_value(condition.fieldname, 0); // Untick the checkbox

								// Move to the next condition
								setTimeout(() => {
									processCondition(index + 1); 
								}, 1000);
							}
						},
						error: function () {
							// Handle API error
							frappe.msgprint(__(`${condition.label} Not Passed for invoice: ${invoiceValue}. Reason: API Error.`));
							current_dialog.set_value(condition.fieldname, 0); // Untick the checkbox

							// Move to the next condition
							setTimeout(() => {
								processCondition(index + 1); 
							}, 1000);
						},
					});
				};

				// Start checking conditions one by one
				processCondition(0);
			} else {
				frappe.msgprint(__("Failed to fetch company abbreviation."));
			}
		},
	});
}


			}
		],
		primary_action_label: __("Next"),
	},
	
	  {
		name: "steps_to_follow",
		title: __("Steps to Follow Next"),
		fields: [
		  {
			fieldname: "comments",
			label: __("Steps to Follow Next"),
			fieldtype: "Small Text",
		  },
		],
		primary_action_label: __("Submit"),
	  },
	];

	function render_slide(slide) {
	  const dialog = new frappe.ui.Dialog({
		title: slide.title,
		fields: slide.fields,
		primary_action_label: slide.primary_action_label,
		primary_action(values) {
			slideData[slides_settings[current_slide_index].name] = values;
		  if (slide.name === "select_company") {
			fetch_company_details(values.company);
		  }
		  if (slide.name === "company_details") {
			generate_csr_config(values);
		  }
		//   if (slide.name === "enter_otp") {
		// 	frappe.call({
		// 		method: "frappe.client.set_value",
		// 		args: {
		// 			doctype: "Company",
		// 			name: selected_company,
		// 			fieldname: "custom_otp",
		// 			value: values.otp,
		// 		},
		// 		callback: function (response) {
		// 			if (response && response.message) {
		// 				frappe.msgprint(__("OTP stored successfully in the company document."));
		// 			} else {
		// 				frappe.msgprint(__("Failed to store OTP. Please try again."));
		// 			}
		// 		},
		// 	});
		// }
  
		  
		  if (current_slide_index < slides_settings.length - 1) {
			current_slide_index++;
			dialog.hide();
			render_slide(slides_settings[current_slide_index]);
		  } else {
			submit_wizard(values);
			dialog.hide();
		  }
		},
		secondary_action_label: current_slide_index > 0 ? __("Previous") : null,
		secondary_action() {
		  if (current_slide_index > 0) {
			slideData[slides_settings[current_slide_index].name] = current_dialog.get_values();
			current_slide_index--;
			dialog.hide();
			render_slide(slides_settings[current_slide_index]);
		  }
		},
	  });
  
	  if (slide.name === "company_details") {
		// Pre-fill data when arriving at company_details slide
		if (selected_company) {
		  frappe.call({
			method: "frappe.client.get",
			args: { doctype: "Company", name: selected_company },
			callback: function (res) {
			  if (res && res.message) {
				dialog.set_value("company_name", res.message.company_name);
			  }
			},
		  });
  
		  frappe.call({
			method: "frappe.client.get_list",
			args: { doctype: "Address",
            filters: [],
            fields: [
              "custom_building_number",
              "city",
              "pincode",
              
            ],
          },
			callback: function (res) {
			  if (res && res.message.length > 0) {
				dialog.set_value("building", res.message[0].custom_building_number);
				dialog.set_value("city", res.message[1].city);
				dialog.set_value("zip", res.message[2].pincode);
			  } else {
				dialog.set_value("building", __("Not Found"));
			  }
			},
		  });
		}
	  }
	  
	  if (slideData[slide.name]) {
        dialog.set_values(slideData[slide.name]);
    }
	  current_dialog = dialog;
	
	  dialog.show();
	  dialog.$wrapper.on('shown.bs.modal', function () {
		applyTooltips({ dialog }, unifiedTooltips);
	});

	// Remove any tooltips from previous dialogs
	dialog.$wrapper.on('hidden.bs.modal', function () {
		removeTooltips();
	});
	  if (slide.name === "create_csr") {
		dialog.set_value("csr_config_box", csr_config.replace(/^\s+|\s+$/gm, ""));
		
		// dialog.set_value("created_csr_config",JSON.stringify(response, null, 2))
		
		
	  }
	  if (csr_config && selected_company) {
		frappe.call({
		  method: "frappe.client.set_value",
		  args: {
			doctype: "Company",
			name: selected_company,
			fieldname: "custom_csr_config",
			value: csr_config.replace(/^\s+|\s+$/gm, ""),
		  },
		  callback: function (response) {
			
		  },
		});
	  }
	  
	  

	  
	  
	}
  
	function fetch_company_details(company) {
	  if (!company) return;
	  selected_company = company;
	}
  
	function generate_csr_config(values) {
		const vat_number = values.vat_number || "";
		const city = values.city ? values.city.toUpperCase() : "N/A";
		const business_category = values.business_category || "N/A";
	
		const hexSegment = () => Math.random().toString(16).substr(2, 8);
	
		csr_config = `
		  csr.common.name=TST-886431145-${vat_number}
		  csr.serial.number=1-TST|2-TST|3-${hexSegment()}-${hexSegment().substr(0, 4)}-${hexSegment().substr(0, 4)}-${hexSegment().substr(0, 4)}-${hexSegment().substr(0, 12)}
		  csr.organization.identifier=${vat_number}
		  csr.organization.unit.name=${vat_number}
		  csr.organization.name=${values.company_name || "Your Company name"}
		  csr.country.name=SA
		  csr.invoice.type=1100
		  csr.location.address=${city}
		  csr.industry.business.category=${business_category}
		`.trim();
		
		// frappe.msgprint(csr_config.replace(/^\s+|\s+$/gm, ""));
	  }
	
	  function submit_wizard(values) {
		frappe.msgprint(__("Thank You! Successfully completed Zatca Phase 2 integration."));
	  }
	
	  render_slide(slides_settings[current_slide_index]);
	  function removeTooltips() {
        $('.tooltip-container').remove();
    }
	};
  