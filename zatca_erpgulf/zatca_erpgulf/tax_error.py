"""this module contains functions that are used to validate tax information
in sales invoices."""

from frappe import _
import frappe


def validate_sales_invoice_taxes(doc, event=None):
    """
    Validate that the sales invoice has at least one tax entry.
    Raises a validation error if taxes are missing.

    :param sales_invoice_doc: The sales invoice document object
    :return: None
    """
    company_doc = frappe.get_doc("Company", doc.company)

    # ✅ Exit early if ZATCA is not enabled
    if not company_doc.custom_zatca_invoice_enabled:
        return
    is_gpos_installed = "gpos" in frappe.get_installed_apps()
    field_exists = frappe.get_meta(doc.doctype).has_field("custom_unique_id")

    if is_gpos_installed and field_exists:
        if doc.custom_unique_id and not doc.custom_zatca_pos_name:
            frappe.throw(
                "ZATCA POS Machine name is missing for invoice, Add ZATCA POS machine name"
            )
    customer_doc = frappe.get_doc("Customer", doc.customer)
    # if customer_doc.custom_b2c != 1:
    #     frappe.throw("This customer should be B2C for Background")
    company_doc = frappe.get_doc("Company", doc.company)

    # if (
    #     customer_doc.custom_b2c != 1
    #     and company_doc.custom_send_invoice_to_zatca == "Background"
    # ):
    #     frappe.throw(
    #         _("As per ZATCA regulation, This customer should be B2C for Background")
    #     )

    # If the company requires cost centers, ensure the invoice has one
    if doc.custom_zatca_pos_name:
        zatca_settings = frappe.get_doc("ZATCA Multiple Setting", doc.custom_zatca_pos_name)

        # Get the linked Company from custom_linked_doctype
        linked_company_doc = frappe.get_doc("Company", zatca_settings.custom_linked_doctype)

        # Validation: doc.company and linked company must be the same
        if linked_company_doc.name != doc.company:
            frappe.throw(
                f"Company mismatch: Document company '{doc.company}' "
                f"does not match linked ZATCA company '{linked_company_doc.name}of machine setting'."
            )
    if company_doc.custom_costcenter == 1:
        if not doc.cost_center:
            frappe.throw(_("This company requires a Cost Center"))

        cost_center_doc = frappe.get_doc("Cost Center", doc.cost_center)

        # Ensure the Cost Center has a valid custom_zatca_branch_address
        if not cost_center_doc.custom_zatca_branch_address:
            frappe.throw(
                _(
                    f"As per ZATCA regulation, The Cost Center '{doc.cost_center}' is missing a valid branch address. "
                    "Please update the Cost Center with a valid `custom_zatca_branch_address`."
                )
            )
        if not cost_center_doc.custom_zatca__registration_type:
            frappe.throw(
                _(
                    f"As per ZATCA regulation, The Cost Center '{doc.cost_center}' is missing a valid registration_type "
                    "Please update the Cost Center with a valid `custom_zatca__registration_type`."
                )
            )
        if not cost_center_doc.custom_zatca__registration_number:
            frappe.throw(
                _(
                    f"As per ZATCA regulation,The Cost Center '{doc.cost_center}' is missing a valid registration_type "
                    "Please update the Cost Center with a valid `custom_zatca__registration_type`."
                )
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
                    _(
                        f"As per ZATCA regulation, The Item Tax Template '{item.item_tax_template}' "
                        "for item '{item.item_code}' does not exist."
                    )
                )

        if not doc.taxes or len(doc.taxes) == 0:
            frappe.throw(
                _(
                    "As per ZATCA regulation,Tax information is missing from the Sales Invoice."
                    " Either add an Item Tax Template for all items "
                    "or include taxes in the invoice."
                )
            )
    if doc.is_return == 1 and doc.doctype in ["Sales Invoice", "POS Invoice"]:
        if not doc.return_against:
            frappe.throw(
                _(
                    "As per ZATCA regulation, the Billing Reference ID "
                    "(Original Invoice Number) is mandatory for "
                    "Credit Notes and Return Invoices. "
                    "Please select the original invoice in the 'Return Against' field."
                )
            )
    if doc.doctype == "Sales Invoice":
        if doc.is_debit_note == 1 and not doc.return_against:
            frappe.throw(
                _("Debit Note must reference a Sales Invoice in 'Return Against'.")
            )
    if doc.doctype == "Sales Invoice":
        if "claudion4saudi" in frappe.get_installed_apps():
            if hasattr(doc, "custom_advances_copy") and doc.custom_advances_copy:
                for advance_row in doc.custom_advances_copy:
                    if (
                        advance_row.difference_posting_date
                        and not advance_row.reference_name
                    ):
                        frappe.throw(
                            _(
                                "⚠️As per ZATCA regulation, Missing Advance Sales Invoice referncename in feting details ."
                                "If there is no advance sales invoice,then remove the row from the table"
                            )
                        )
