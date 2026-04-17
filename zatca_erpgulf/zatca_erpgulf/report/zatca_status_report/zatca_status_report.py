import frappe
from frappe import _

def get_columns():
    return [
        {'fieldname': 'name', 'label': _('Inv.Number'), 'fieldtype': 'Link', 'options': 'Sales Invoice', 'width': 220},
        {'fieldname': 'posting_date', 'label': _('Date'), 'fieldtype': 'Date', 'width': 160},
        {'fieldname': 'customer_name', 'label': _('Customer'), 'fieldtype': 'Data', 'width': 220},
        {'fieldname': 'grand_total', 'label': _('Total'), 'fieldtype': 'Currency', 'width': 160},
        {'fieldname': 'custom_zatca_status', 'label': _('Status'), 'fieldtype': 'Data', 'width': 180}
    ]


def get_data_and_chart(filters):
    dt_from = filters.get('dt_from')
    dt_to = filters.get('dt_to')
    status = filters.get('status')
    company = filters.get('company')

    conditions = ["1=1"]
    values = {}

    if company:
        conditions.append("company = %(company)s")
        values['company'] = company

    if dt_from and dt_to:
        conditions.append("posting_date BETWEEN %(dt_from)s AND %(dt_to)s")
        values['dt_from'] = dt_from
        values['dt_to'] = dt_to
    elif dt_from:
        conditions.append("posting_date >= %(dt_from)s")
        values['dt_from'] = dt_from
    elif dt_to:
        conditions.append("posting_date <= %(dt_to)s")
        values['dt_to'] = dt_to

    if status and status != "Not Submitted":
        conditions.append("custom_zatca_status = %(status)s")
        values['status'] = status

    where_clause = " AND ".join(conditions)
    # nosemgrep: frappe-semgrep-rules.rules.security.frappe-sql-format-injection
    query = f"""
        SELECT 
            name,
            customer_name,
            posting_date,
            grand_total,
            custom_zatca_status,
            docstatus
        FROM `tabSales Invoice`
        WHERE {where_clause}
        ORDER BY posting_date DESC
    """

    invoices = frappe.db.sql(query, values, as_dict=True)

    # Apply 'Not Submitted' filter
    if status == "Not Submitted":
        invoices = [inv for inv in invoices if inv.get("docstatus") == 0 or not inv.get("custom_zatca_status")]

    return invoices


def execute(filters=None):
    columns = get_columns()
    data = get_data_and_chart(filters)
    return columns, data
