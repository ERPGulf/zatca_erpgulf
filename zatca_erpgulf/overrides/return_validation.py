import frappe
from erpnext.controllers import sales_and_purchase_return as spr


_original_validate_returned_items = spr.validate_returned_items


def custom_validate_returned_items(doc):
    if (
        doc.doctype == "Sales Invoice"
        and doc.is_return
        and doc.get("custom_skip_validation_for_credit_note")
    ):
        return

    return _original_validate_returned_items(doc)


spr.validate_returned_items = custom_validate_returned_items