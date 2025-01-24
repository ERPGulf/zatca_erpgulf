"""this module contains functions that are used to validate tax information 
  in sales invoices."""

import frappe


def validate_sales_invoice_taxes(doc, event=None):
    """
    Validate that the sales invoice has at least one tax entry.
    Raises a validation error if taxes are missing.

    :param sales_invoice_doc: The sales invoice document object
    :return: None
    """

    for item in doc.items:
        # Check if the item has a valid Item Tax Template
        if item.item_tax_template:
            try:
                # Ensure the Item Tax Template exists
                frappe.get_doc("Item Tax Template", item.item_tax_template)
                continue  
            except frappe.DoesNotExistError:
                frappe.throw(
                    f"The Item Tax Template '{item.item_tax_template}' "
                    "for item '{item.item_code}' does not exist."
                )

        if not doc.taxes or len(doc.taxes) == 0:
            frappe.throw(
                "Tax information is missing from the Sales Invoice."
                " Either add an Item Tax Template for all items "
                "or include taxes in the invoice."
            )
