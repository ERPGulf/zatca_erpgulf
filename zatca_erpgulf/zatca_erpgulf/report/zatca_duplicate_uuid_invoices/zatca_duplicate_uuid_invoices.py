import frappe
from frappe import _

def execute(filters=None):
    filters = filters or {}

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    conditions = []
    values = []

    if from_date:
        conditions.append("posting_date >= %s")
        values.append(from_date)

    if to_date:
        conditions.append("posting_date <= %s")
        values.append(to_date)

    condition_sql = " AND ".join(conditions)
    if condition_sql:
        condition_sql = " AND " + condition_sql

    data = frappe.db.sql(f"""
		SELECT *
		FROM (
			SELECT
				name,
				custom_uuid,
				posting_date,
				customer,
				grand_total,
				COUNT(*) OVER (PARTITION BY custom_uuid) AS uuid_count
			FROM `tabSales Invoice`
			WHERE docstatus = 1
			AND custom_uuid IS NOT NULL
			AND custom_uuid != ''
			AND custom_uuid != 'Not Submitted'   -- ✅ FIX
			{condition_sql}
		) t
		WHERE uuid_count > 1
		ORDER BY custom_uuid, name
	""", values, as_dict=True)


    columns = [
        {
            "label": _("Sales Invoice"),
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 210,
        },
        {
            "label": _("UUID"),
            "fieldname": "custom_uuid",
            "fieldtype": "Data",
            "width": 300,
        },
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 200,
        },
        {
            "label": _("Grand Total"),
            "fieldname": "grand_total",
            "fieldtype": "Currency",
            "width": 180,
        },
        
    ]

    return columns, data
