"""this module is used to generate the CSR configuration data for a company based on its abbreviation."""

import random
import frappe
from frappe import _


@frappe.whitelist()
def get_csr_config(company_abbr):
    """
    Retrieve and generate CSR configuration data for a company based on its abbreviation.
    """
    try:
        company_name_val = frappe.db.get_value(
            "Company", {"abbr": company_abbr}, "name"
        )
        if not company_name_val:
            frappe.throw(_(f"Company with abbreviation {company_abbr} not found."))
        company_doc = frappe.get_doc("Company", company_name_val)
        tax_id = company_doc.tax_id
        location = company_doc.custom_zatca__location_for_csr_configuratoin
        business_category = (
            company_doc.custom_zatca__company_category_for_csr_configuration
        )
        company_name = company_doc.company_name
        if not tax_id:
            frappe.throw(_("Tax ID (VAT number) is required."))
        if not location:
            frappe.throw(_("Location for CSR configuration is required."))
        if not business_category:
            frappe.throw(_("Company category for CSR configuration is required."))
        if not company_name:
            frappe.throw(_("Company name is required."))
        vat_number = tax_id
        city = location.upper()

        def hex_segment() -> str:
            return f"{random.getrandbits(32):08x}"

        serial_number = (
            f"1-TST|2-TST|3-"
            f"{hex_segment()}-"
            f"{hex_segment()[:4]}-"
            f"{hex_segment()[:4]}-"
            f"{hex_segment()[:4]}-"
            f"{hex_segment()[:12]}"
        )
        config = (
            f"csr.common.name=TST-886431145-{vat_number}\n"
            f"csr.serial.number={serial_number}\n"
            f"csr.organization.identifier={vat_number}\n"
            f"csr.organization.unit.name={vat_number}\n"
            f"csr.organization.name={company_name}\n"
            f"csr.country.name=SA\n"
            f"csr.invoice.type=1100\n"
            f"csr.location.address={city}\n"
            f"csr.industry.business.category={business_category}"
        )

        frappe.msgprint(_(
            msg=f"<div style='font-size: 12px; white-space: pre-wrap;'>{config}</div>",
            title="Thank You! Successfully completed CSR configuration",
        ))
        return config
    except Exception as e:
        frappe.throw(_(str(e)))
