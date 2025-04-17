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
    is_gpos_installed = "gpos" in frappe.get_installed_apps()
    field_exists = frappe.get_meta(doc.doctype).has_field("custom_unique_id")

    if is_gpos_installed and field_exists:
        if doc.custom_unique_id and not doc.custom_zatca_pos_name:
            frappe.throw(
                "ZATCA POS Machine name is missing for invoice, Add Zatca POS machine name"
            )
    customer_doc = frappe.get_doc("Customer", doc.customer)
    # if customer_doc.custom_b2c != 1:
    #     frappe.throw("This customer should be B2C for Background")
    company_doc = frappe.get_doc("Company", doc.company)
    if (
        customer_doc.custom_b2c != 1
        and company_doc.custom_send_invoice_to_zatca == "Background"
    ):
        frappe.throw("This customer should be B2C for Background")

    # If the company requires cost centers, ensure the invoice has one
    if company_doc.custom_costcenter == 1:
        if not doc.cost_center:
            frappe.throw("This company requires a Cost Center")

        cost_center_doc = frappe.get_doc("Cost Center", doc.cost_center)

        # Ensure the Cost Center has a valid custom_zatca_branch_address
        if not cost_center_doc.custom_zatca_branch_address:
            frappe.throw(
                f"The Cost Center '{doc.cost_center}' is missing a valid branch address. "
                "Please update the Cost Center with a valid `custom_zatca_branch_address`."
            )
        if not cost_center_doc.custom_zatca__registration_type:
            frappe.throw(
                f"The Cost Center '{doc.cost_center}' is missing a valid registration_type "
                "Please update the Cost Center with a valid `custom_zatca__registration_type`."
            )
        if not cost_center_doc.custom_zatca__registration_number:
            frappe.throw(
                f"The Cost Center '{doc.cost_center}' is missing a valid registration_type "
                "Please update the Cost Center with a valid `custom_zatca__registration_type`."
            )

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
