
frappe.pages["setup-zatca-phase-2"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
	  parent: wrapper,
	  title: "Setup Zatca Phase-2",
	  single_column: true,
	});
  
	let current_slide_index = 0;
	let selected_company = null;
	let current_dialog = null; 

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
				if (!selected_company) {
					frappe.msgprint(__("Please select a company before creating CSR."));
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
								// Create CSR
								frappe.call({
									method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.create_CSID",
									args: { portal_type, company_abbr },
									callback: function (response) {
										if (response && response.message) {
											// console.log("CSR Response:", response.message);
		
											const encodedString = response.message.trim();
											frappe.msgprint(encodedString)
											// Update the `created_csr_config` field in the dialog
											
										} else {
											frappe.msgprint(__("Failed to create CSID. Please check the logs."));
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
					if (!selected_company) {
						frappe.msgprint(__("Please select a company before creating CSR."));
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
								// Safely fetch portal_type
								const ComplianceSlide = slides_settings.find(
									(slide) => slide.name === "zatca_compliance_check"
								);
								const invoiceField = ComplianceSlide?.fields.find(
									(field) => field.fieldname === "invoice_number"
								);
								const invoice_number = invoiceField.value
								const complianceType = "1";
								if (invoice_number && company_abbr) {
									// Create CSR
									frappe.call({
										method: "zatca_erpgulf.zatca_erpgulf.sign_invoice.zatca_Call_compliance",
										args: { invoice_number,complianceType, company_abbr },
										callback: function (response) {
											if (response && response.message) {
												// console.log("CSR Response:", response.message);
			
												const encodedString = response.message.trim();
												frappe.msgprint(encodedString)
												// Update the `created_csr_config` field in the dialog
												
											} else {
												frappe.msgprint(__("Failed to create CSID. Please check the logs."));
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
		  if (slide.name === "select_company") {
			fetch_company_details(values.company);
		  }
		  if (slide.name === "company_details") {
			generate_csr_config(values);
		  }
		  if (slide.name === "enter_otp") {
			frappe.call({
				method: "frappe.client.set_value",
				args: {
					doctype: "Company",
					name: selected_company,
					fieldname: "custom_otp",
					value: values.otp,
				},
				callback: function (response) {
					if (response && response.message) {
						frappe.msgprint(__("OTP stored successfully in the company document."));
					} else {
						frappe.msgprint(__("Failed to store OTP. Please try again."));
					}
				},
			});
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
	  current_dialog = dialog;
	  dialog.show();
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
	};
  