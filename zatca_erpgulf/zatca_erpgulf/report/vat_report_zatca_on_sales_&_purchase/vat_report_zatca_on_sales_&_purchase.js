

frappe.query_reports["VAT Report ZATCA on Sales & Purchase"] = {
    "filters": [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 0,  // optional
            default: frappe.defaults.get_user_default("Company")
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.month_end()
        }
    ]
};
