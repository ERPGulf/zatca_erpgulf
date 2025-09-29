// Copyright (c) 2025, ERPGulf and contributors
// For license information, please see license.txt

frappe.query_reports["ZATCA VAT on Sales and Purchase Report"] = {
	"filters": [{
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 0,  // now optional
            "default": frappe.defaults.get_default("company") || null
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "reqd": 0,
            "default": frappe.datetime.month_start()
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "reqd": 0,
            "default": frappe.datetime.month_end()
        }

	]
};
