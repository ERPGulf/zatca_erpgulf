from frappe.utils import now_datetime
import frappe

def log_zatca_event(invoice_number, response_text, status, uuid=None, title=None):
    """new doctype for handing logs"""
    try:
        event_doc = frappe.get_doc({
            "doctype": "ZATCA ERPGulf Event Log",
            "title": title or f"ZATCA API Call for {invoice_number}",
            "invoice_number": invoice_number,
            "time": now_datetime(),  #
            "api_response": response_text,  # store the API response here
            "custom_uuid": uuid or "",
            "status": status  # e.g., "Success", "Failed", "Warning"
        })
        event_doc.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Failed to log ZATCA Event: {str(e)}", "ZATCA Event Log")
