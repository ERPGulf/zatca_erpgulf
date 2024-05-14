import frappe

def zatca_done_or_not(doc, method=None):
        if doc.custom_zatca_status != "REPORTED" and doc.custom_zatca_status != "CLEARED":
                frappe.throw("Please send this invoice to ZATCA, before submitting")
                
def before_save(doc, method=None):
        if doc.custom_zatca_status in ("REPORTED", "CLEARED"):
                frappe.throw("This invoice is already submitted to ZATCA. You cannot edit, cancel or save it.")

def duplicating_invoice(doc, method=None):
            # required on version 13  as no-copy settings on fields not available
            # frappe.msgprint(frappe.__version__)
            # frappe.msgprint(int(frappe.__version__.split('.')[0]))
            if int(frappe.__version__.split('.')[0]) == 13:
                    frappe.msgprint("duplicating invoice")
                    doc.custom_uuid = "Not submitted"
                    doc.custom_zatca_status = "Not Submitted"
                    doc.save()

def test_save_validate(doc, method=None):
        # frappe.msgprint("test save validate")
        frappe.msgprint("test save validated and stopped it here")
