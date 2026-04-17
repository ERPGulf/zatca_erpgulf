"""
ZATCA Compliance Hooks for Frappe

This file contains hook functions related to ZATCA (Zakat, Tax, and Customs Authority)
compliance for invoice processing in the Frappe system. The hooks ensure that invoices
are properly submitted, validated, and duplicated according to ZATCA requirements.

"""

from frappe import _
import frappe
from erpnext import get_region


def zatca_done_or_not(doc, method=None):  # pylint: disable=unused-argument
    """
    Ensures that the invoice is submitted to ZATCA before submission.
    """

    region = get_region(doc.company)
    if region not in ["Saudi Arabia"]:
        return

    if doc.custom_zatca_status not in ("REPORTED", "CLEARED"):
        frappe.throw(_("Please send this invoice to ZATCA, before submitting"))


def before_save(doc, method=None):  # pylint: disable=unused-argument
    """
    Prevents editing, canceling, or saving of invoices that are already submitted to ZATCA.
    """

    region = get_region(doc.company)
    if region not in ["Saudi Arabia"]:
        return

    if doc.custom_zatca_status in ("REPORTED", "CLEARED"):
        frappe.throw(
            _(
                "This invoice is already submitted to ZATCA. You cannot edit, cancel or save it."
            )
        )


def duplicating_invoice(doc, method=None):  # pylint: disable=unused-argument
    """
    Duplicates the invoice for Frappe version 13,
    where the no-copy setting on fields is not available.
    """

    region = get_region(doc.company)
    if region not in ["Saudi Arabia"]:
        return

    if int(frappe.__version__.split(".", maxsplit=1)[0]) == 13:
        frappe.msgprint(_("Duplicating invoice"))
        doc.custom_uuid = "Not submitted"
        doc.custom_zatca_status = "Not Submitted"
        doc.save()


def test_save_validate(doc, method=None):  # pylint: disable=unused-argument
    """
    Used for testing purposes to display a message during save validation.
    """

    region = get_region(doc.company)
    if region not in ["Saudi Arabia"]:
        return

    frappe.msgprint(_("Test save validated and stopped it here"))
