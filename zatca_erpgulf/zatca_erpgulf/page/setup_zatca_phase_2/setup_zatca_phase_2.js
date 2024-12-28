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
			links: ["https://docs.claudion.com/Field"],
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
			links: ["https://docs.claudion.com/Field"],
		},
		{
			fieldname: "vat_number",
			context: "dialog",
			text: "Provide the VAT number for your company.",
			links: ["https://docs.claudion.com/Field"],
		},
		{
			fieldname: "building",
			context: "dialog",
			text: "Enter the building number or name.",
			links: ["https://docs.claudion.com/Field"],
		},
		{
			fieldname: "city",
			context: "dialog",
			text: "Enter the city name where the business is located.",
			links: ["https://docs.claudion.com/Field"],
		},
		{
			fieldname: "zip",
			context: "dialog",
			text: "Provide the ZIP or postal code.",
			links: ["https://docs.claudion.com/Field"],
		},
		{
			fieldname: "business_category",
			context: "dialog",
			text: "Select the business category for your company.",
			links: ["https://docs.claudion.com/Field"],
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
	let new_dialog = null;
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
			primary_action(values) {
				if (!values.integration_type) {
					frappe.msgprint({
						title: __("Mandatory Field Missing"),
						indicator: "red",
						message: __("Please select an Integration Type to proceed."),
					});
					return;
				}

				// Your logic for moving to the next slide goes here
				console.log("Selected Integration Type:", values.integration_type);
			},

		},
		//   {
		// 	name: "select_company",
		// 	title: __("Select Company"),
		// 	fields: [
		// 	  {
		// 		fieldname: "company",
		// 		label: __("Select Company"),
		// 		fieldtype: "Link",
		// 		options: "Company",
		// 		change: function () {
		// 		  const company = this.get_value("company");
		// 		  if (company) {
		// 			selected_company = company;
		// 		  }
		// 		},
		// 	  },
		// 	],
		// 	primary_action_label: __("Next"),
		//   },
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

							// Prevent multiple triggers by checking a global flag
							if (window.confirmationDialogShownFor === company) {
								return; // Dialog already shown for this company
							}

							// Check for existing ZATCA setup in the selected company
							frappe.call({
								method: "frappe.client.get",
								args: {
									doctype: "Company",
									name: selected_company,
								},
								callback: function (res) {
									if (res && res.message) {
										const zatcaSetup = res.message.custom_basic_auth_from_production;
										console.log(zatcaSetup)
										if (zatcaSetup) {
											// Show confirmation dialog
											frappe.confirm(
												__(
													"ZATCA setup already exists for this company. Do you want to override the existing setup?"
												),
												function () {
													// User selected "Yes"
													frappe.msgprint(
														__("Proceeding to the next step.")
													);
												},
												function () {
													// User selected "No"
													frappe.msgprint(
														__("Setup canceled. Please select another company or exit the wizard.")
													);
													selected_company = null;
													current_dialog.hide();
												}
											);
											// Mark this company as having shown the dialog
											window.confirmationDialogShownFor = company;
										}
									}
								},
							});
						}
					},
				},
				{
					fieldname: "is_offline_pos",
					label: __("Is Offline POS?"),
					fieldtype: "Check",
					onchange: function (e) {
						// Ensure fields_dict is accessible and the field exists
						const selectMachineField = this.layout.fields_dict.select_machine;
		
						if (selectMachineField) {
							const isOffline = this.get_value(); // Get checkbox value
							selectMachineField.df.hidden = !isOffline; // Toggle hidden property
							selectMachineField.refresh(); // Apply changes
						} else {
							console.error("Field 'select_machine' not found.");
						}
					},
				},
				{
					fieldname: "select_machine",
					label: __("Select Machine"),
					fieldtype: "Link",
					options: "Zatca Multiple Setting",
					hidden: true, // Initially hidden
				},
			],
			primary_action_label: __("Next"),
			primary_action(values) {
				if (!selected_company) {
					frappe.msgprint(
						__("Please select a company before proceeding.")
					);
					return;
				}
				slideData[slides_settings[current_slide_index].name] = values;
				current_slide_index++;
				current_dialog.hide();
				render_slide(slides_settings[current_slide_index]);
			},
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
						const selectcompanySlide = slides_settings.find(
							(slide) => slide.name === "select_compay"
						);
						const isOfflinePOSField = selectcompanySlide?.fields.find(
							(field) => field.fieldname === "is_offline_pos"
						);
						const isOfflinePOS = isOfflinePOSField?.value; // Assuming value is stored here
						if (isOfflinePOS) {
							const selectMachineField = integrationSlide?.fields.find(
								(field) => field.fieldname === "select_machine"
							);
							selectedMachine = selectMachineField?.value;
						
							if (!selectedMachine) {
								frappe.msgprint(__("Please select a machine for offline POS."));
								return;
							}
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
										const doctype = isOfflinePOS
											? "Zatca Multiple Setting"
											: "Company";
										const name = isOfflinePOS
											? selectedMachine
											: selected_company;

										frappe.call({
											method: "zatca_erpgulf.zatca_erpgulf.sign_invoice_first.create_csr",
											args: {  
												zatca_doc: {
													doctype: doctype,
													name: name,
												},portal_type, company_abbr },
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
						const selectcompanySlide = slides_settings.find(
							(slide) => slide.name === "select_compay"
						);
						const isOfflinePOSField = selectcompanySlide?.fields.find(
							(field) => field.fieldname === "is_offline_pos"
						);
						const isOfflinePOS = isOfflinePOSField?.value; // Assuming value is stored here
						if (isOfflinePOS) {
							const selectMachineField = integrationSlide?.fields.find(
								(field) => field.fieldname === "select_machine"
							);
							selectedMachine = selectMachineField?.value;
						
							if (!selectedMachine) {
								frappe.msgprint(__("Please select a machine for offline POS."));
								return;
							}
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
													const doctype = isOfflinePOS
													? "Zatca Multiple Setting"
													: "Company";
												const name = isOfflinePOS
													? selectedMachine
													: selected_company;
													// Step 3: Generate CSID
													frappe.call({
														method: "zatca_erpgulf.zatca_erpgulf.sign_invoice_first.create_csid",
														args: { zatca_doc: {
															doctype: doctype,
															name: name,
														},portal_type, company_abbr },
														callback: function (response) {
															if (response && response.message) {
																// console.log("Response: " + JSON.stringify(response, null, 2));

																// Use the response as a JSON string
																const encodedString = response.message.trim();
																// console.log("Response: " + JSON.stringify(response, null, 2))
																// const encodedString = response.message.trim();
																// frappe.msgprint(__("CSID generated successfully."));
																if (current_dialog) {
																	current_dialog.set_value("basic_auth_from_csid", encodedString);
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

				{
					fieldname: "check_compliance",
					label: __("Check Compliance"),
					fieldtype: "Button",
					click: function () {
						const invoiceValue = current_dialog.get_value("invoice_number");
						if (!invoiceValue || invoiceValue.trim() === "") {
							frappe.msgprint(__("Please enter the invoice number before proceeding."));
							return;
						}

						if (!selected_company) {
							frappe.msgprint(__("Please select a company before running compliance checks."));
							return;
						}

						// Fetch company abbreviation
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

									const processConditionSequentially = async () => {
										for (let condition of conditions) {
											try {
												await frappe.call({
													method: "frappe.client.set_value",
													args: {
														doctype: "Company",
														name: selected_company,
														fieldname: "custom_validation_type",
														value: condition.label,
													},
												});
												// Call compliance API for each condition
												const response = await frappe.call({
													method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.zatca_call_compliance",
													args: {
														invoice_number: invoiceValue,
														complianceType: condition.complianceType,
														company_abbr: company_abbr,
													},

												});


												if (response && response.message) {
													const {
														validationResults = {},
														reportingStatus = "Not Reported",
														clearanceStatus = "Not Cleared",
													} = response.message;

													const validationStatus = validationResults?.status || "PASS";
													const infoMessages = validationResults?.infoMessages || [];
													const detailedInfo = infoMessages
														.map(
															(msg) =>
																`${msg.category}: ${msg.message} (Code: ${msg.code}, Status: ${msg.status})`
														)
														.join("\n");

													const statusMessage = [
														`${condition.label}:`,
														`Validation Status: ${validationStatus}`,
														`Reporting Status: ${reportingStatus}`,
														`Clearance Status: ${clearanceStatus}`,
														`Details:\n${detailedInfo || "No additional details."}`,
													]
														.filter(Boolean)
														.join("\n");

													// Display message for each condition
													// frappe.msgprint(__(statusMessage));
													frappe.msgprint(__(`${condition.label}:${JSON.stringify(response.message, 4)}`));

													// Update checkbox value
													current_dialog.set_value(
														condition.fieldname,
														validationStatus === "PASS" ? 1 : 0
													);
												} else {
													frappe.msgprint(
														__(`${condition.label}: No response or unknown error from the API.`)
													);
													current_dialog.set_value(condition.fieldname, 0);
												}
											} catch (error) {
												frappe.msgprint(__(`${condition.label}: Failed due to API Error.`));
												console.error("API Error:", error);
												current_dialog.set_value(condition.fieldname, 0);
											}
										}

										frappe.msgprint(__("Compliance checks completed."));
									};

									// Start sequential processing of conditions
									processConditionSequentially();
								} else {
									frappe.msgprint(__("Failed to fetch company abbreviation."));
								}
							},
						});
					},
				}




			],
			primary_action_label: __("Next"),
		},
		{
			name: "final_csid_generation",
			title: __("Final CSID Generation"),
			fields: [

				{
					fieldname: "final_csid",
					label: __("Generate Final CSIDs"),
					fieldtype: "Button",
					click: function () {
						if (!selected_company) {
							frappe.msgprint(__("Please select a company before creating CSR."));
							return;
						}
						const selectcompanySlide = slides_settings.find(
							(slide) => slide.name === "select_compay"
						);
						const isOfflinePOSField = selectcompanySlide?.fields.find(
							(field) => field.fieldname === "is_offline_pos"
						);
						const isOfflinePOS = isOfflinePOSField?.value; // Assuming value is stored here
						if (isOfflinePOS) {
							const selectMachineField = integrationSlide?.fields.find(
								(field) => field.fieldname === "select_machine"
							);
							selectedMachine = selectMachineField?.value;
						
							if (!selectedMachine) {
								frappe.msgprint(__("Please select a machine for offline POS."));
								return;
							}
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



									if (company_abbr) {
										const doctype = isOfflinePOS
										? "Zatca Multiple Setting"
										: "Company";
									const name = isOfflinePOS
										? selectedMachine
										: selected_company;

										frappe.call({
											method: "zatca_erpgulf.zatca_erpgulf.sign_invoice_first.production_csid",
											args: { zatca_doc: {
												doctype: doctype,
												name: name,
											},company_abbr },
											callback: function (response) {
												if (response && response.message) {
													// console.log("CSR Response:", response.message);

													const encodedString = response.message.trim();
													// console.log(encodedString)
													// frappe.msgprint(encodedString)
													if (current_dialog) {
														current_dialog.set_value("final_auth_csid", encodedString);
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
					fieldname: "final_auth_csid",
					label: __("Final Auth CSID"),
					fieldtype: "Long Text",
				},
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
				if (slide.name === "integration_type") {
					if (!values.integration_type) {
						frappe.msgprint({
							title: __("Mandatory Field Missing"),
							indicator: "red",
							message: __("Please select an Integration Type to proceed."),
						});
						return;
					}
				}
				if (slide.name === "select_company") {
					if (!values.company) {
						frappe.msgprint({
							title: __("Mandatory Field Missing"),
							indicator: "red",
							message: __("Please select a Company to proceed."),
						});
						return;
					}
					fetch_company_details(values.company);
				}
				if (slide.name === "company_details") {
					if (!values.vat_number || !values.city || !values.business_category) {
						let missing_fields = [];

						if (!values.vat_number) {
							missing_fields.push("VAT Number");
						}
						if (!values.city) {
							missing_fields.push("City");
						}
						if (!values.business_category) {
							missing_fields.push("Business Category");
						}

						frappe.msgprint({
							title: __("Mandatory Fields Missing"),
							indicator: "red",
							message: __(`The following field(s) are required: ${missing_fields.join(", ")}. Please fill them to proceed.`),
						});

						return;
					}

					generate_csr_config(values);
				}


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
					args: {
						doctype: "Address",
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
