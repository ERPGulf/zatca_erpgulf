frappe.query_reports["Zatca Status Report"] = {
    "filters": [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1
        },
        {
            fieldname: "dt_from",
            label: __("From"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -12)
        },
        {
            fieldname: "dt_to",
            label: __("To"),
            fieldtype: "Date",
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nReported\nCleared\n503 Service Unavailable\nIntra-company transfer\nNot Submitted",
            default: "Reported"
        }
    ],

    onload: function(report) {
        // onload code if needed
    }
};
