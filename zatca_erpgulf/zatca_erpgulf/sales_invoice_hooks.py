# sales_invoice_hooks.py

import frappe
from frappe.model.naming import make_autoname, revert_series_if_last

def set_draft_series(doc, method):
    """
    Set draft series for new invoices.
    Draft series format: DRAFT-.MM.YY.-.### (static, not dynamic)
    """
    if doc.docstatus == 0:  # Draft
        doc.naming_series = "DRAFT-.MM.YY.-"  # ERPNext will append auto-increment counter automatically


import frappe
from frappe.model.naming import make_autoname

# def rename_invoice_on_submit(doc, method):
#     # Skip if already renamed
#     if doc.name.startswith("ACC-SINV-"):
#         return

#     old_name = doc.name
#     new_name = make_autoname("ACC-SINV-.YYYY.-.#####")

#     # Rename immediately (safe because doc is still in memory)
#     frappe.rename_doc("Sales Invoice", old_name, new_name, force=True)

#     # Update doc object in memory so further hooks see the correct name
#     doc.name = new_name
#     # frappe.response["new_name"] = new_name
#     # frappe.response["redirect_to"] = new_name
    # frappe.response["redirect_to"] = f"/app/sales-invoice/{new_name}"

    
def rename_invoice_on_submit(doc, method):
    if doc.name.startswith("ACC-SINV-"):
        return

    old_name = doc.name
    new_name = make_autoname("ACC-SINV-.YYYY.-.#####")

    # Rename the document
    frappe.rename_doc("Sales Invoice", old_name, new_name, force=True)

    # Update doc object in memory
    doc.name = new_name

    # Send redirect info to the frontend (do NOT use db_set)
    frappe.response["redirect_to"] = f"/app/sales-invoice/{new_name}"
    # frappe.msgprint(f"Invoice renamed to <a href='/app/sales-invoice/{new_name}' target='_blank'>{new_name}</a>")

