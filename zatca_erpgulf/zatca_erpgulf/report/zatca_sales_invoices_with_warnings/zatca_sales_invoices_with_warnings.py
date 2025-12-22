import frappe
import json
import re


def extract_json(text):
    """
    Extract JSON object from mixed ZATCA response text
    (handles HTML + text + JSON)
    """
    if not text:
        return None

    match = re.search(r'({.*})', text, re.DOTALL)
    if match:
        return match.group(1)

    return None


def execute(filters=None):
    filters = filters or {}

    # -----------------------------
    # Columns
    # -----------------------------
    columns = [
        {
            "label": "Invoice No",
            "fieldname": "invoice",
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 180,
        },
        {
            "label": "Company",
            "fieldname": "company",
            "width": 200,
        },
        {
            "label": "Customer",
            "fieldname": "customer",
            "width": 200,
        },
        {
            "label": "Posting Date",
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": "ZATCA Status",
            "fieldname": "custom_zatca_status",
            "width": 180,
        },
        {
            "label": "Warning Code",
            "fieldname": "warning_code",
            "width": 160,
        },
        {
            "label": "Warning Message",
            "fieldname": "warning_message",
            "width": 500,
        },
    ]

    # -----------------------------
    # Build SQL conditions
    # -----------------------------
    conditions = ["si.docstatus = 1"]
    query_filters = {}

    if filters.get("company"):
        conditions.append("si.company = %(company)s")
        query_filters["company"] = filters["company"]

    if filters.get("from_date") and filters.get("to_date"):
        conditions.append(
            "si.posting_date BETWEEN %(from_date)s AND %(to_date)s"
        )
        query_filters["from_date"] = filters["from_date"]
        query_filters["to_date"] = filters["to_date"]

    elif filters.get("from_date"):
        conditions.append("si.posting_date >= %(from_date)s")
        query_filters["from_date"] = filters["from_date"]

    elif filters.get("to_date"):
        conditions.append("si.posting_date <= %(to_date)s")
        query_filters["to_date"] = filters["to_date"]

    where_clause = " AND ".join(conditions)

    # -----------------------------
    # Fetch invoices (ESCAPED %%)
    # -----------------------------
    invoices = frappe.db.sql(
        f"""
        SELECT
            si.name,
            si.company,
            si.customer,
            si.posting_date,
            si.custom_zatca_status,
            si.custom_zatca_full_response
        FROM `tabSales Invoice` si
        WHERE {where_clause}
          AND si.custom_zatca_full_response IS NOT NULL
          AND si.custom_zatca_full_response LIKE '%%"warningMessages"%%'
        """,
        query_filters,
        as_dict=True,
    )

    # -----------------------------
    # Parse warnings
    # -----------------------------
    data = []

    for inv in invoices:
        try:
            json_text = extract_json(inv.custom_zatca_full_response)
            if not json_text:
                continue

            response = json.loads(json_text)

            validation = response.get("validationResults", {})
            warnings = validation.get("warningMessages", [])

            if not warnings:
                continue

            for w in warnings:
                data.append({
                    "invoice": inv.name,
                    "company": inv.company,
                    "customer": inv.customer,
                    "posting_date": inv.posting_date,
                    "custom_zatca_status": inv.custom_zatca_status,
                    "warning_code": w.get("code"),
                    "warning_message": w.get("message"),
                })

        except Exception as e:
            frappe.log_error(
                title="ZATCA Sales Invoice Warning Report Error",
                message=f"Invoice: {inv.name}\n{str(e)}",
            )

    return columns, data
