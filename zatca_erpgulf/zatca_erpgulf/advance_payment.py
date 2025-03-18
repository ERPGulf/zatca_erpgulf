"""this module is used to populate the Advance Payment data in the XML file."""

import re
import os
import io
import base64
import json
import frappe
import requests
import uuid
import xml.etree.ElementTree as ET
import frappe
from frappe.utils.data import get_time
from decimal import Decimal, ROUND_DOWN
import xml.etree.ElementTree as ET
from datetime import datetime
from xml.dom import minidom
import frappe
from zatca_erpgulf.zatca_erpgulf.xml_tax_data import (
    get_tax_for_item,
    get_exemption_reason_map,
)
from decimal import Decimal, ROUND_HALF_UP

ITEM_TAX_TEMPLATE = "Item Tax Template"
CAC_TAX_TOTAL = "cac:TaxTotal"
CBC_TAX_AMOUNT = "cbc:TaxAmount"
CAC_TAX_SUBTOTAL = "cac:TaxSubtotal"
CBC_TAXABLE_AMOUNT = "cbc:TaxableAmount"
ZERO_RATED = "Zero Rated"
OUTSIDE_SCOPE = "Services outside scope of tax / Not subject to VAT"
from zatca_erpgulf.zatca_erpgulf.createxml import (
    xml_tags,
    invoice_typecode_standard,
    get_icv_code,
    invoice_typecode_compliance,
    invoice_typecode_standard,
    doc_reference,
    doc_reference_compliance,
    get_address,
    customer_data,
)
from zatca_erpgulf.zatca_erpgulf.xml_tax_data import (
    get_exemption_reason_map,
    get_tax_for_item,
    get_tax_total_from_items,
)


from zatca_erpgulf.zatca_erpgulf.createxml_advance import (
    removetags,
    canonicalize_xml,
    getinvoicehash,
    digital_signature,
    extract_certificate_details,
    certificate_hash,
    signxml_modify,
    generate_signed_properties_hash,
    populate_the_ubl_extensions_output,
    generate_tlv_xml,
    structuring_signedxml,
    get_tlv_for_value,
    update_qr_toxml,
    compliance_api_call,
)

CBC_ID = "cbc:ID"
DS_TRANSFORM = "ds:Transform"

from zatca_erpgulf.zatca_erpgulf.sign_invoice import get_api_url, attach_qr_image

from zatca_erpgulf.zatca_erpgulf.create_qr import create_qr_code


# frappe.init(site="zatca.erpgulf.com")
# frappe.connect()
def get_issue_time(invoice_number):
    """
    Extracts and formats the posting time of a Sales Invoice as HH:MM:SS.
    """
    doc = frappe.get_doc("Advance Sales Invoice", invoice_number)
    time = get_time(doc.posting_time)
    issue_time = time.strftime("%H:%M:%S")  # time in format of  hour,mints,secnds
    return issue_time


# def billing_reference_adavancepayment(invoice, invoice_number):
#     """Populate basic invoice data and include billing reference and prepaid amount."""
#     try:
#         sales_invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)

#         # Adding BillingReference
#         billing_reference = ET.SubElement(invoice, "cac:BillingReference")
#         invoice_document_reference = ET.SubElement(
#             billing_reference, "cac:InvoiceDocumentReference"
#         )

#         invoice_ref_id = ET.SubElement(invoice_document_reference, "cbc:ID")
#         invoice_ref_id.text = "Advance-INV-00123"

#         invoice_ref_uuid = ET.SubElement(invoice_document_reference, "cbc:UUID")
#         invoice_ref_uuid = "f77abe9a-fa43-11ef-8a33-020017019f27"
#         invoice_ref_uuid = invoice_ref_id
#         invoice_ref_uuid.text = invoice_ref_id

#         cbc_issue_date = ET.SubElement(invoice, "cbc:IssueDate")
#         cbc_issue_date.text = str(sales_invoice_doc.posting_date)

#         cbc_issue_time = ET.SubElement(invoice, "cbc:IssueTime")
#         cbc_issue_time.text = get_issue_time(invoice_number)

#         # Prepaid Amount Adjustment
#         prepaid_amount = ET.SubElement(invoice, "cbc:PrepaidAmount", currencyID="SAR")
#         prepaid_amount.text = "115000.00"

#         return invoice, invoice_ref_id, sales_invoice_doc
#     except (AttributeError, ValueError, frappe.ValidationError) as e:
#         frappe.throw(
#             ("Error occurred in billing_reference_adavancepayment data: {}".format(e))
#         )


def salesinvoice_data_advance(invoice, invoice_number):
    """
    Populates the Sales Invoice XML with key elements and metadata.
    """
    try:
        sales_invoice_doc = frappe.get_doc("Advance Sales Invoice", invoice_number)

        cbc_profile_id = ET.SubElement(invoice, "cbc:ProfileID")
        cbc_profile_id.text = "reporting:1.0"

        cbc_id = ET.SubElement(invoice, CBC_ID)
        cbc_id.text = str(sales_invoice_doc.name)

        cbc_uuid = ET.SubElement(invoice, "cbc:UUID")
        cbc_uuid.text = str(uuid.uuid1())
        uuid1 = cbc_uuid.text

        cbc_issue_date = ET.SubElement(invoice, "cbc:IssueDate")
        cbc_issue_date.text = str(sales_invoice_doc.posting_date)

        cbc_issue_time = ET.SubElement(invoice, "cbc:IssueTime")
        cbc_issue_time.text = get_issue_time(invoice_number)

        return invoice, uuid1, sales_invoice_doc
    except (AttributeError, ValueError, frappe.ValidationError) as e:
        frappe.throw(("Error occurred in SalesInvoice data: " f"{str(e)}"))
        return None


def tax_data(invoice, sales_invoice_doc):
    """extract tax data without template"""
    try:

        # Handle SAR-specific logic
        if sales_invoice_doc.paid_from_account_currency == "SAR":
            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount_sar = ET.SubElement(cac_taxtotal, "cbc:TaxAmount")
            cbc_taxamount_sar.set(
                "currencyID", "SAR"
            )  # ZATCA requires tax amount in SAR
            # tax_amount_without_retention_sar = round(
            #     abs(get_tax_total_from_items(sales_invoice_doc)), 2
            # )

            tax_amount_without_retention_sar = Decimal(
                str(abs(get_tax_total_from_items(sales_invoice_doc)))
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            cbc_taxamount_sar.text = str(
                tax_amount_without_retention_sar
            )  # Tax amount in SAR

            taxable_amount = sales_invoice_doc.base_total - sales_invoice_doc.get(
                "base_discount_amount", 0.0
            )
            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount = ET.SubElement(cac_taxtotal, "cbc:TaxAmount")
            cbc_taxamount.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )
            # tax_amount_without_retention = round(
            #     abs(get_tax_total_from_items(sales_invoice_doc)), 2
            # )

            tax_amount_without_retention = float(
                Decimal(str(abs(get_tax_total_from_items(sales_invoice_doc)))).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            )

            cbc_taxamount.text = f"{abs(round(tax_amount_without_retention, 2)):.2f}"

            # Tax Subtotal
            cac_taxsubtotal = ET.SubElement(cac_taxtotal, "cac:TaxSubtotal")
            cbc_taxableamount = ET.SubElement(cac_taxsubtotal, "cbc:TaxableAmount")
            cbc_taxableamount.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )

            # if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
            taxable_amount = sales_invoice_doc.base_total - sales_invoice_doc.get(
                "base_discount_amount", 0.0
            )

            # else:
            # taxable_amount = sales_invoice_doc.base_net_total - sales_invoice_doc.get(
            #     "base_discount_amount", 0.0
            # )

            cbc_taxableamount.text = str(abs(round(taxable_amount, 2)))
            cbc_taxamount_2 = ET.SubElement(cac_taxsubtotal, "cbc:TaxAmount")
            cbc_taxamount_2.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )
            cbc_taxamount_2.text = f"{abs(round(tax_amount_without_retention, 2)):.2f}"

        # Handle USD-specific logic
        else:
            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount_usd_1 = ET.SubElement(cac_taxtotal, "cbc:TaxAmount")
            cbc_taxamount_usd_1.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )  # USD currency
            # if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
            taxable_amount_1 = sales_invoice_doc.total - sales_invoice_doc.get(
                "discount_amount", 0.0
            )
            # else:
            # taxable_amount_1 = sales_invoice_doc.base_net_total - sales_invoice_doc.get(
            #     "discount_amount", 0.0
            # )
            tax_amount_without_retention = (
                taxable_amount_1 * float(sales_invoice_doc.taxes[0].rate) / 100
            )
            cbc_taxamount_usd_1.text = str(round(tax_amount_without_retention, 2))
            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount_usd = ET.SubElement(cac_taxtotal, "cbc:TaxAmount")
            cbc_taxamount_usd.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )  # USD currency
            # if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
            taxable_amount_1 = sales_invoice_doc.total - sales_invoice_doc.get(
                "discount_amount", 0.0
            )

            # else:
            # taxable_amount_1 = sales_invoice_doc.base_net_total - sales_invoice_doc.get(
            #     "discount_amount", 0.0
            # )
            tax_amount_without_retention = (
                taxable_amount_1 * float(sales_invoice_doc.taxes[0].rate) / 100
            )
            cbc_taxamount_usd.text = str(round(tax_amount_without_retention, 2))

            # Tax Subtotal
            cac_taxsubtotal = ET.SubElement(cac_taxtotal, "cac:TaxSubtotal")
            cbc_taxableamount = ET.SubElement(cac_taxsubtotal, "cbc:TaxableAmount")
            cbc_taxableamount.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )
            cbc_taxableamount.text = str(abs(round(taxable_amount_1, 2)))

            cbc_taxamount_2 = ET.SubElement(cac_taxsubtotal, "cbc:TaxAmount")
            cbc_taxamount_2.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )
            cbc_taxamount_2.text = str(
                abs(
                    round(
                        taxable_amount_1 * float(sales_invoice_doc.taxes[0].rate) / 100,
                        2,
                    )
                )
            )

        # Tax Category and Scheme

        cac_taxcategory_1 = ET.SubElement(cac_taxsubtotal, "cac:TaxCategory")
        cbc_id_8 = ET.SubElement(cac_taxcategory_1, "cbc:ID")

        if sales_invoice_doc.custom_zatca_tax_category == "Standard":
            cbc_id_8.text = "S"
        elif sales_invoice_doc.custom_zatca_tax_category == "Zero Rated":
            cbc_id_8.text = "Z"
        elif sales_invoice_doc.custom_zatca_tax_category == "Exempted":
            cbc_id_8.text = "E"
        elif (
            sales_invoice_doc.custom_zatca_tax_category
            == "Services outside scope of tax / Not subject to VAT"
        ):
            cbc_id_8.text = "O"

        cbc_percent_1 = ET.SubElement(cac_taxcategory_1, "cbc:Percent")
        cbc_percent_1.text = f"{float(sales_invoice_doc.taxes[0].rate):.2f}"

        # Exemption Reason (if applicable)
        exemption_reason_map = get_exemption_reason_map()
        if sales_invoice_doc.custom_zatca_tax_category != "Standard":
            cbc_taxexemptionreasoncode = ET.SubElement(
                cac_taxcategory_1, "cbc:TaxExemptionReasonCode"
            )
            cbc_taxexemptionreasoncode.text = (
                sales_invoice_doc.custom_exemption_reason_code
            )
            cbc_taxexemptionreason = ET.SubElement(
                cac_taxcategory_1, "cbc:TaxExemptionReason"
            )
            reason_code = sales_invoice_doc.custom_exemption_reason_code
            if reason_code in exemption_reason_map:
                cbc_taxexemptionreason.text = exemption_reason_map[reason_code]

        # Tax Scheme
        cac_taxscheme_3 = ET.SubElement(cac_taxcategory_1, "cac:TaxScheme")
        cbc_id_9 = ET.SubElement(cac_taxscheme_3, "cbc:ID")
        cbc_id_9.text = "VAT"

        # Legal Monetary Total (adjust for both SAR and USD)
        cac_legalmonetarytotal = ET.SubElement(invoice, "cac:LegalMonetaryTotal")
        cbc_lineextensionamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:LineExtensionAmount"
        )
        cbc_lineextensionamount.set(
            "currencyID", sales_invoice_doc.paid_from_account_currency
        )
        # if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
        cbc_lineextensionamount.text = str(round(abs(sales_invoice_doc.total), 2))
        # else:

        # cbc_lineextensionamount.text = str(
        #     round(abs(sales_invoice_doc.base_net_total), 2)
        # )
        cbc_taxexclusiveamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:TaxExclusiveAmount"
        )
        cbc_taxexclusiveamount.set(
            "currencyID", sales_invoice_doc.paid_from_account_currency
        )
        # if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
        cbc_taxexclusiveamount.text = str(
            round(
                abs(
                    sales_invoice_doc.total
                    - sales_invoice_doc.get("discount_amount", 0.0)
                ),
                2,
            )
        )
        # else:
        # cbc_taxexclusiveamount.text = str(
        #     round(
        #         abs(
        #             sales_invoice_doc.base_net_total
        #             - sales_invoice_doc.get("discount_amount", 0.0)
        #         ),
        #         2,
        #     )
        # )
        cbc_taxinclusiveamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:TaxInclusiveAmount"
        )
        cbc_taxinclusiveamount.set(
            "currencyID", sales_invoice_doc.paid_from_account_currency
        )
        # if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
        cbc_taxinclusiveamount.text = str(
            round(
                abs(
                    sales_invoice_doc.total
                    - sales_invoice_doc.get("discount_amount", 0.0)
                )
                + abs(tax_amount_without_retention),
                2,
            )
        )
        # else:
        # cbc_taxinclusiveamount.text = str(
        #     round(
        #         abs(
        #             sales_invoice_doc.base_net_total
        #             - sales_invoice_doc.get("discount_amount", 0.0)
        #         )
        #         + abs(tax_amount_without_retention),
        #         2,
        #     )
        # )
        cbc_allowancetotalamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:AllowanceTotalAmount"
        )
        cbc_allowancetotalamount.set(
            "currencyID", sales_invoice_doc.paid_from_account_currency
        )
        cbc_allowancetotalamount.text = str(
            abs(sales_invoice_doc.get("discount_amount", 0.0))
        )

        cbc_prepaidamount = ET.SubElement(cac_legalmonetarytotal, "cbc:PrepaidAmount")
        cbc_prepaidamount.set(
            "currencyID", sales_invoice_doc.paid_from_account_currency
        )
        cbc_prepaidamount.text = str(round(abs(sales_invoice_doc.grand_total), 2))

        cbc_payableamount = ET.SubElement(cac_legalmonetarytotal, "cbc:PayableAmount")
        cbc_payableamount.set(
            "currencyID", sales_invoice_doc.paid_from_account_currency
        )
        # if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
        inclusive_amount = round(
            abs(sales_invoice_doc.total - sales_invoice_doc.get("discount_amount", 0.0))
            + abs(tax_amount_without_retention),
            2,
        )
        # else:
        # inclusive_amount = round(
        #     abs(
        #         sales_invoice_doc.base_net_total
        #         - sales_invoice_doc.get("discount_amount", 0.0)
        #     )
        #     + abs(tax_amount_without_retention),
        #     2,
        # )

        cbc_payableamount.text = str(
            round(float(cbc_prepaidamount.text) - inclusive_amount, 2)
        )
        # if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
        #     cbc_payableamount.text = str(
        #         round(
        #             abs(
        #                 sales_invoice_doc.total
        #                 - sales_invoice_doc.get("discount_amount", 0.0)
        #             )
        #             + abs(tax_amount_without_retention),
        #             2,
        #         )
        #     )
        # else:
        #     cbc_payableamount.text = str(
        #         round(
        #             abs(
        #                 sales_invoice_doc.base_net_total
        #                 - sales_invoice_doc.get("discount_amount", 0.0)
        #             )
        #             + abs(tax_amount_without_retention),
        #             2,
        #         )
        #     )
        return invoice

    except (AttributeError, KeyError, ValueError, TypeError) as e:
        frappe.throw(f"Data processing error in tax data: {str(e)}")
        return None


def tax_data_with_template(invoice, sales_invoice_doc):
    """Adding tax data with template to the xml"""
    try:
        # Initialize tax category totals
        tax_category_totals = {}
        for item in sales_invoice_doc.custom_item:
            item_tax_template = frappe.get_doc(
                "Item Tax Template", item.item_tax_template
            )
            zatca_tax_category = item_tax_template.custom_zatca_tax_category

            if zatca_tax_category not in tax_category_totals:
                tax_category_totals[zatca_tax_category] = {
                    "taxable_amount": 0,
                    "tax_amount": 0,
                    "tax_rate": (
                        item_tax_template.taxes[0].tax_rate
                        if item_tax_template.taxes
                        else 15
                    ),
                    "exemption_reason_code": item_tax_template.custom_exemption_reason_code,
                }
            if sales_invoice_doc.paid_from_account_currency == "SAR":
                tax_category_totals[zatca_tax_category]["taxable_amount"] += abs(
                    item.base_amount
                )
            else:
                tax_category_totals[zatca_tax_category]["taxable_amount"] += abs(
                    item.amount
                )

        first_tax_category = next(
            iter(tax_category_totals)
        )  # Get the first tax category
        base_discount_amount = sales_invoice_doc.get("discount_amount", 0.0)

        # Subtract the base discount from the taxable amount of the first tax category
        tax_category_totals[first_tax_category]["taxable_amount"] -= abs(
            base_discount_amount
        )

        # Calculate the total tax using the same technique as the 3rd place
        # for zatca_tax_category, totals in tax_category_totals.items():
        #     totals["tax_amount"] = abs(
        #         round(totals["taxable_amount"] * totals["tax_rate"] / 100, 2)
        #     )
        # total_tax = sum(
        #     category_totals["tax_amount"]
        #     for category_totals in tax_category_totals.values()
        # )
        for zatca_tax_category, totals in tax_category_totals.items():
            totals["taxable_amount"] = Decimal(
                str(totals["taxable_amount"])
            )  # Convert to Decimal
            totals["tax_rate"] = Decimal(str(totals["tax_rate"]))  # Convert to Decimal

            # Calculate tax amount with proper rounding
            totals["tax_amount"] = (
                totals["taxable_amount"] * totals["tax_rate"] / Decimal("100")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Compute total tax
        total_tax = sum(
            category_totals["tax_amount"]
            for category_totals in tax_category_totals.values()
        )
        total_tax = total_tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        # For SAR currency
        if sales_invoice_doc.paid_from_account_currency == "SAR":
            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount_sar = ET.SubElement(cac_taxtotal, "cbc:TaxAmount")
            cbc_taxamount_sar.set(
                "currencyID", "SAR"
            )  # SAR is as ZATCA requires tax amount in SAR
            tax_amount_without_retention_sar = round(abs(total_tax), 2)
            cbc_taxamount_sar.text = str(tax_amount_without_retention_sar)

            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount = ET.SubElement(cac_taxtotal, "cbc:TaxAmount")
            cbc_taxamount.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )
            # tax_amount_without_retention = round(abs(total_tax), 2)
            tax_amount_without_retention = total_tax.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            cbc_taxamount.text = str(tax_amount_without_retention)
        else:
            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount_sar = ET.SubElement(cac_taxtotal, "cbc:TaxAmount")
            cbc_taxamount_sar.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )
            tax_amount_without_retention_sar = round(abs(total_tax), 2)
            cbc_taxamount_sar.text = str(tax_amount_without_retention_sar)

            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount = ET.SubElement(cac_taxtotal, "cbc:TaxAmount")
            cbc_taxamount.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )
            tax_amount_without_retention = round(abs(total_tax), 2)
            cbc_taxamount.text = str(tax_amount_without_retention)

        # Group items by ZATCA tax category
        # tax_category_totals = {}

        # for item in sales_invoice_doc.items:
        #     item_tax_template = frappe.get_doc(
        #         "Item Tax Template", item.item_tax_template
        #     )
        #     zatca_tax_category = item_tax_template.custom_zatca_tax_category

        #     if zatca_tax_category not in tax_category_totals:
        #         tax_category_totals[zatca_tax_category] = {
        #             "taxable_amount": 0,
        #             "tax_amount": 0,
        #             "tax_rate": (
        #                 item_tax_template.taxes[0].tax_rate
        #                 if item_tax_template.taxes
        #                 else 15
        #             ),
        #             "exemption_reason_code": item_tax_template.custom_exemption_reason_code,
        #         }
        #     if sales_invoice_doc.currency == "SAR":
        #         tax_category_totals[zatca_tax_category]["taxable_amount"] += abs(
        #             item.base_amount
        #         )
        #     else:
        #         tax_category_totals[zatca_tax_category]["taxable_amount"] += abs(
        #             item.amount
        #         )

        # first_tax_category = next(iter(tax_category_totals))
        # tax_category_totals[first_tax_category]["taxable_amount"] -= abs(
        #     sales_invoice_doc.get("discount_amount", 0.0)
        # )

        # for item in sales_invoice_doc.items:
        #     item_tax_template = frappe.get_doc(
        #         "Item Tax Template", item.item_tax_template
        #     )
        #     zatca_tax_category = item_tax_template.custom_zatca_tax_category

        #     if zatca_tax_category not in tax_category_totals:
        #         tax_category_totals[zatca_tax_category] = {
        #             "taxable_amount": 0,
        #             "tax_amount": 0,
        #             "tax_rate": (
        #                 item_tax_template.taxes[0].tax_rate
        #                 if item_tax_template.taxes
        #                 else 15
        #             ),
        #             "exemption_reason_code": item_tax_template.custom_exemption_reason_code,
        #         }

        # # Use the same technique for calculating tax amount
        # for zatca_tax_category, totals in tax_category_totals.items():
        #     totals["tax_amount"] = abs(
        #         round(totals["taxable_amount"] * totals["tax_rate"] / 100, 2)
        #     )

        tax_category_totals = {}

        # Process Items and Calculate Taxable Amounts
        for item in sales_invoice_doc.custom_item:
            item_tax_template = frappe.get_doc(
                "Item Tax Template", item.item_tax_template
            )
            zatca_tax_category = item_tax_template.custom_zatca_tax_category

            if zatca_tax_category not in tax_category_totals:
                tax_category_totals[zatca_tax_category] = {
                    "taxable_amount": Decimal("0.00"),  # Ensure it's Decimal
                    "tax_amount": Decimal("0.00"),
                    "tax_rate": (
                        Decimal(str(item_tax_template.taxes[0].tax_rate))
                        if item_tax_template.taxes
                        else Decimal("15.00")
                    ),
                    "exemption_reason_code": item_tax_template.custom_exemption_reason_code,
                }

            # Convert item amounts to Decimal before adding
            item_amount = Decimal(
                str(
                    abs(
                        item.base_amount
                        if sales_invoice_doc.paid_from_account_currency == "SAR"
                        else item.amount
                    )
                )
            )

            tax_category_totals[zatca_tax_category]["taxable_amount"] += item_amount

        # Apply Discount to the First Tax Category
        first_tax_category = next(iter(tax_category_totals))

        discount_amount = Decimal(
            str(abs(sales_invoice_doc.get("discount_amount", 0.0)))
        )
        tax_category_totals[first_tax_category]["taxable_amount"] -= discount_amount

        # Calculate the tax amount using Decimal and proper rounding
        for zatca_tax_category, totals in tax_category_totals.items():
            totals["tax_amount"] = (
                totals["taxable_amount"] * totals["tax_rate"] / Decimal("100")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Debugging Output
        # frappe.throw(f"tax_category_totals: {tax_category_totals}")

        for zatca_tax_category, totals in tax_category_totals.items():
            cac_taxsubtotal = ET.SubElement(cac_taxtotal, "cac:TaxSubtotal")
            cbc_taxableamount = ET.SubElement(cac_taxsubtotal, "cbc:TaxableAmount")
            cbc_taxableamount.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )
            cbc_taxableamount.text = str(round(totals["taxable_amount"], 2))

            cbc_taxamount_2 = ET.SubElement(cac_taxsubtotal, "cbc:TaxAmount")
            cbc_taxamount_2.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )
            # cbc_taxamount_2.text = str(round(totals["tax_amount"], 2))
            cbc_taxamount_value = str(tax_amount_without_retention)
            cbc_taxamount_2_value = str(round(totals["tax_amount"], 2))

            # Check if values match
            if cbc_taxamount_value != cbc_taxamount_2_value:
                cbc_taxamount_2_value = str(tax_amount_without_retention)
            else:
                cbc_taxamount_2_value = str(round(totals["tax_amount"], 2))

            cbc_taxamount_2.text = cbc_taxamount_2_value

            cac_taxcategory_1 = ET.SubElement(cac_taxsubtotal, "cac:TaxCategory")
            cbc_id_8 = ET.SubElement(cac_taxcategory_1, "cbc:ID")

            if zatca_tax_category == "Standard":
                cbc_id_8.text = "S"
            elif zatca_tax_category == "Zero Rated":
                cbc_id_8.text = "Z"
            elif zatca_tax_category == "Exempted":
                cbc_id_8.text = "E"
            elif (
                zatca_tax_category
                == "Services outside scope of tax / Not subject to VAT"
            ):
                cbc_id_8.text = "O"

            cbc_percent_1 = ET.SubElement(cac_taxcategory_1, "cbc:Percent")
            cbc_percent_1.text = f"{totals['tax_rate']:.2f}"

            if zatca_tax_category != "Standard":
                cbc_taxexemptionreasoncode = ET.SubElement(
                    cac_taxcategory_1, "cbc:TaxExemptionReasonCode"
                )
                cbc_taxexemptionreasoncode.text = totals["exemption_reason_code"]
                cbc_taxexemptionreason = ET.SubElement(
                    cac_taxcategory_1, "cbc:TaxExemptionReason"
                )

                exemption_reason_map = get_exemption_reason_map()
                if totals["exemption_reason_code"] in exemption_reason_map:
                    cbc_taxexemptionreason.text = exemption_reason_map[
                        totals["exemption_reason_code"]
                    ]

            cac_taxscheme = ET.SubElement(cac_taxcategory_1, "cac:TaxScheme")
            cbc_taxscheme_id = ET.SubElement(cac_taxscheme, "cbc:ID")
            cbc_taxscheme_id.text = "VAT"

        # Discount
        cac_legalmonetarytotal = ET.SubElement(invoice, "cac:LegalMonetaryTotal")
        cbc_lineextensionamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:LineExtensionAmount"
        )
        cbc_lineextensionamount.set(
            "currencyID", sales_invoice_doc.paid_from_account_currency
        )
        cbc_lineextensionamount.text = str(round(abs(sales_invoice_doc.total), 2))

        # Tax-Exclusive Amount (base_total - base_discount_amount)
        cbc_taxexclusiveamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:TaxExclusiveAmount"
        )
        cbc_taxexclusiveamount.set(
            "currencyID", sales_invoice_doc.paid_from_account_currency
        )
        cbc_taxexclusiveamount.text = str(
            round(
                abs(
                    sales_invoice_doc.total
                    - sales_invoice_doc.get("discount_amount", 0.0)
                ),
                2,
            )
        )

        # Tax-Inclusive Amount (Tax-Exclusive Amount + tax_amount_without_retention)
        cbc_taxinclusiveamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:TaxInclusiveAmount"
        )
        cbc_taxinclusiveamount.set(
            "currencyID", sales_invoice_doc.paid_from_account_currency
        )
        # cbc_taxinclusiveamount.text = str(
        #     round(
        #         abs(
        #             sales_invoice_doc.total
        #             - sales_invoice_doc.get("discount_amount", 0.0)
        #         )
        #         + abs(tax_amount_without_retention),
        #         2,
        #     )
        # )

        total_amount = Decimal(str(sales_invoice_doc.total))
        discount_amount = Decimal(str(sales_invoice_doc.get("discount_amount", 0.0)))
        tax_amount = abs(tax_amount_without_retention)  # Already Decimal
        tax_inclusive_amount = (
            abs(total_amount - discount_amount) + tax_amount
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        cbc_taxinclusiveamount.text = str(tax_inclusive_amount)

        cbc_allowancetotalamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:AllowanceTotalAmount"
        )
        cbc_allowancetotalamount.set(
            "currencyID", sales_invoice_doc.paid_from_account_currency
        )

        cbc_allowancetotalamount.text = str(
            round(abs(sales_invoice_doc.get("discount_amount", 0.0)), 2)
        )
        cbc_prepaidamount = ET.SubElement(cac_legalmonetarytotal, "cbc:PrepaidAmount")
        cbc_prepaidamount.set(
            "currencyID", sales_invoice_doc.paid_from_account_currency
        )
        cbc_prepaidamount.text = "1150"

        cbc_payableamount = ET.SubElement(cac_legalmonetarytotal, "cbc:PayableAmount")
        cbc_payableamount.set(
            "currencyID", sales_invoice_doc.paid_from_account_currency
        )
        # cbc_payableamount.text = str(
        #     round(
        #         abs(
        #             sales_invoice_doc.total
        #             - sales_invoice_doc.get("discount_amount", 0.0)
        #         )
        #         + abs(tax_amount_without_retention),
        #         2,
        #     )
        # )
        payable_amount = (abs(total_amount - discount_amount) + tax_amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        cbc_payableamount.text = str(payable_amount)

        return invoice

    except (AttributeError, KeyError, ValueError, TypeError) as e:
        frappe.throw(f"Data processing error in tax data: {str(e)}")
        return None


def additional_reference_advanve(invoice, company_abbr, sales_invoice_doc):
    """
    Adds additional document references to the XML invoice for PIH, QR, and Signature elements.
    """
    try:
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")

        company_doc = frappe.get_doc("Company", company_name)

        # Create the first AdditionalDocumentReference element for PIH
        cac_additionaldocumentreference2 = ET.SubElement(
            invoice, "cac:AdditionalDocumentReference"
        )
        cbc_id_1_1 = ET.SubElement(cac_additionaldocumentreference2, CBC_ID)
        cbc_id_1_1.text = "PIH"
        cac_attachment = ET.SubElement(
            cac_additionaldocumentreference2, "cac:Attachment"
        )
        cbc_embeddeddocumentbinaryobject = ET.SubElement(
            cac_attachment, "cbc:EmbeddedDocumentBinaryObject"
        )
        cbc_embeddeddocumentbinaryobject.set("mimeCode", "text/plain")
        pih = company_doc.custom_pih
        cbc_embeddeddocumentbinaryobject.text = pih
        cac_additionaldocumentreference22 = ET.SubElement(
            invoice, "cac:AdditionalDocumentReference"
        )
        cbc_id_1_12 = ET.SubElement(cac_additionaldocumentreference22, CBC_ID)
        cbc_id_1_12.text = "QR"
        cac_attachment22 = ET.SubElement(
            cac_additionaldocumentreference22, "cac:Attachment"
        )
        cbc_embeddeddocumentbinaryobject22 = ET.SubElement(
            cac_attachment22, "cbc:EmbeddedDocumentBinaryObject"
        )
        cbc_embeddeddocumentbinaryobject22.set("mimeCode", "text/plain")
        cbc_embeddeddocumentbinaryobject22.text = "GsiuvGjvchjbFhibcDhjv1886G"
        cac_sign = ET.SubElement(invoice, "cac:Signature")
        cbc_id_sign = ET.SubElement(cac_sign, CBC_ID)
        cbc_method_sign = ET.SubElement(cac_sign, "cbc:SignatureMethod")
        cbc_id_sign.text = "urn:oasis:names:specification:ubl:signature:Invoice"
        cbc_method_sign.text = "urn:oasis:names:specification:ubl:dsig:enveloped:xades"

        return invoice

    except (ET.ParseError, AttributeError, ValueError, frappe.DoesNotExistError) as e:
        frappe.throw(f"Error occurred in additional references: {e}")
        return None


def company_data_advance(invoice, sales_invoice_doc):
    """
    Adds company data elements to the XML invoice, including supplier details, address,
    and tax information.
    """
    try:
        company_doc = frappe.get_doc("Company", sales_invoice_doc.company)
        if company_doc.custom_costcenter == 1 and not sales_invoice_doc.cost_center:
            frappe.throw("no Cost Center is set in the invoice.Give the feild")
        custom_registration_type = company_doc.custom_registration_type
        custom_company_registration = company_doc.custom_company_registration

        cac_accountingsupplierparty = ET.SubElement(
            invoice, "cac:AccountingSupplierParty"
        )
        cac_party_1 = ET.SubElement(cac_accountingsupplierparty, "cac:Party")
        cac_partyidentification = ET.SubElement(cac_party_1, "cac:PartyIdentification")
        cbc_id_2 = ET.SubElement(cac_partyidentification, CBC_ID)
        cbc_id_2.set("schemeID", custom_registration_type)
        cbc_id_2.text = custom_company_registration
        address = get_address(sales_invoice_doc, company_doc)

        cac_postaladdress = ET.SubElement(cac_party_1, "cac:PostalAddress")
        cbc_streetname = ET.SubElement(cac_postaladdress, "cbc:StreetName")
        cbc_streetname.text = address.address_line1
        cbc_buildingnumber = ET.SubElement(cac_postaladdress, "cbc:BuildingNumber")
        cbc_buildingnumber.text = address.custom_building_number
        cbc_plotidentification = ET.SubElement(
            cac_postaladdress, "cbc:PlotIdentification"
        )
        cbc_plotidentification.text = address.address_line1
        cbc_citysubdivisionname = ET.SubElement(
            cac_postaladdress, "cbc:CitySubdivisionName"
        )
        cbc_citysubdivisionname.text = address.address_line2
        cbc_cityname = ET.SubElement(cac_postaladdress, "cbc:CityName")
        cbc_cityname.text = address.city
        cbc_postalzone = ET.SubElement(cac_postaladdress, "cbc:PostalZone")
        cbc_postalzone.text = address.pincode
        cbc_countrysubentity = ET.SubElement(cac_postaladdress, "cbc:CountrySubentity")
        cbc_countrysubentity.text = address.state

        cac_country = ET.SubElement(cac_postaladdress, "cac:Country")
        cbc_identificationcode = ET.SubElement(cac_country, "cbc:IdentificationCode")
        cbc_identificationcode.text = "SA"

        cac_partytaxscheme = ET.SubElement(cac_party_1, "cac:PartyTaxScheme")
        cbc_companyid = ET.SubElement(cac_partytaxscheme, "cbc:CompanyID")
        cbc_companyid.text = company_doc.tax_id

        cac_taxscheme = ET.SubElement(cac_partytaxscheme, "cac:TaxScheme")
        cbc_id_3 = ET.SubElement(cac_taxscheme, CBC_ID)
        cbc_id_3.text = "VAT"

        cac_partylegalentity = ET.SubElement(cac_party_1, "cac:PartyLegalEntity")
        cbc_registrationname = ET.SubElement(
            cac_partylegalentity, "cbc:RegistrationName"
        )
        cbc_registrationname.text = sales_invoice_doc.company

        return invoice
    except (ET.ParseError, AttributeError, ValueError, frappe.DoesNotExistError) as e:
        frappe.throw(f"Error occurred in company data: {e}")
        return None


def customer_data_advance(invoice, sales_invoice_doc):
    """
    customer data of address and need values
    """
    try:
        customer_doc = frappe.get_doc("Customer", sales_invoice_doc.party)
        # frappe.throw(str(customer_doc))
        cac_accountingcustomerparty = ET.SubElement(
            invoice, "cac:AccountingCustomerParty"
        )
        cac_party_2 = ET.SubElement(cac_accountingcustomerparty, "cac:Party")
        cac_partyidentification_1 = ET.SubElement(
            cac_party_2, "cac:PartyIdentification"
        )
        cbc_id_4 = ET.SubElement(cac_partyidentification_1, CBC_ID)
        cbc_id_4.set("schemeID", str(customer_doc.custom_buyer_id_type))
        cbc_id_4.text = customer_doc.custom_buyer_id

        address = None
        # if customer_doc.custom_b2c != 1:
        #     if int(frappe.__version__.split(".", maxsplit=1)[0]) == 13:
        #         if sales_invoice_doc.customer_address:
        #             address = frappe.get_doc(
        #                 "Address", sales_invoice_doc.customer_address
        #             )
        #     else:
        if customer_doc.customer_primary_address:
            address = frappe.get_doc("Address", customer_doc.customer_primary_address)

            if not address:
                frappe.throw("Customer address is mandatory for non-B2C customers.")

            cac_postaladdress_1 = ET.SubElement(cac_party_2, "cac:PostalAddress")
            # frappe.throw(address.address_line1)
            if address.address_line1:
                cbc_streetname_1 = ET.SubElement(cac_postaladdress_1, "cbc:StreetName")
                cbc_streetname_1.text = address.address_line1

            if (
                hasattr(address, "custom_building_number")
                and address.custom_building_number
            ):
                cbc_buildingnumber_1 = ET.SubElement(
                    cac_postaladdress_1, "cbc:BuildingNumber"
                )
                cbc_buildingnumber_1.text = address.custom_building_number

            cbc_plotidentification_1 = ET.SubElement(
                cac_postaladdress_1, "cbc:PlotIdentification"
            )
            if hasattr(address, "po_box") and address.po_box:
                cbc_plotidentification_1.text = address.po_box
            elif address.address_line1:
                cbc_plotidentification_1.text = address.address_line1

            if address.address_line2:
                cbc_citysubdivisionname_1 = ET.SubElement(
                    cac_postaladdress_1, "cbc:CitySubdivisionName"
                )
                cbc_citysubdivisionname_1.text = address.address_line2

            if address.city:
                cbc_cityname_1 = ET.SubElement(cac_postaladdress_1, "cbc:CityName")
                cbc_cityname_1.text = address.city

            if address.pincode:
                cbc_postalzone_1 = ET.SubElement(cac_postaladdress_1, "cbc:PostalZone")
                cbc_postalzone_1.text = address.pincode

            if address.state:
                cbc_countrysubentity_1 = ET.SubElement(
                    cac_postaladdress_1, "cbc:CountrySubentity"
                )
                cbc_countrysubentity_1.text = address.state

            cac_country_1 = ET.SubElement(cac_postaladdress_1, "cac:Country")
            cbc_identificationcode_1 = ET.SubElement(
                cac_country_1, "cbc:IdentificationCode"
            )

            cbc_identificationcode_1.text = "SA"

        cac_partytaxscheme_1 = ET.SubElement(cac_party_2, "cac:PartyTaxScheme")
        cac_taxscheme_1 = ET.SubElement(cac_partytaxscheme_1, "cac:TaxScheme")
        cbc_id_5 = ET.SubElement(cac_taxscheme_1, CBC_ID)
        cbc_id_5.text = "VAT"
        cac_partylegalentity_1 = ET.SubElement(cac_party_2, "cac:PartyLegalEntity")
        cbc_registrationname_1 = ET.SubElement(
            cac_partylegalentity_1, "cbc:RegistrationName"
        )
        cbc_registrationname_1.text = customer_doc.customer_name

        return invoice
    except (ET.ParseError, AttributeError, ValueError, frappe.DoesNotExistError) as e:
        frappe.throw(f"Error occurred in customer data: {e}")
        return None


def delivery_and_payment_means_adavance(invoice, sales_invoice_doc):
    """
    Adds delivery and payment means elements to the XML invoice,
    including actual delivery date and payment means.
    """
    try:
        cac_delivery = ET.SubElement(invoice, "cac:Delivery")
        cbc_actual_delivery_date = ET.SubElement(cac_delivery, "cbc:ActualDeliveryDate")
        cbc_actual_delivery_date.text = str(sales_invoice_doc.due_date)

        cac_payment_means = ET.SubElement(invoice, "cac:PaymentMeans")
        cbc_payment_means_code = ET.SubElement(
            cac_payment_means, "cbc:PaymentMeansCode"
        )
        cbc_payment_means_code.text = "30"

        return invoice

    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(f"Delivery and payment means failed: {e}")
        return None  # Ensures all return paths explicitly return a value


def delivery_and_payment_means_for_compliance_advance(
    invoice, sales_invoice_doc, compliance_type
):
    """
    Adds delivery and payment means elements to the XML invoice for compliance,
    including actual delivery date, payment means, and instruction notes for cancellations.
    """
    try:
        cac_delivery = ET.SubElement(invoice, "cac:Delivery")
        cbc_actual_delivery_date = ET.SubElement(cac_delivery, "cbc:ActualDeliveryDate")
        cbc_actual_delivery_date.text = str(sales_invoice_doc.due_date)

        cac_payment_means = ET.SubElement(invoice, "cac:PaymentMeans")
        cbc_payment_means_code = ET.SubElement(
            cac_payment_means, "cbc:PaymentMeansCode"
        )
        cbc_payment_means_code.text = "30"

        if compliance_type in {"3", "4", "5", "6"}:
            cbc_instruction_note = ET.SubElement(
                cac_payment_means, "cbc:InstructionNote"
            )
            cbc_instruction_note.text = "Cancellation"

        return invoice

    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(f"Delivery and payment means failed: {e}")
        return None


def item_data_advance(invoice, sales_invoice_doc, invoice_number):
    """
    The function defines the xml creating without item tax template
    """
    try:
        for single_item in sales_invoice_doc.custom_item:
            _item_tax_amount, item_tax_percentage = get_tax_for_item(
                sales_invoice_doc.taxes[0].item_wise_tax_detail, single_item.item_code
            )
            cac_invoiceline = ET.SubElement(invoice, "cac:InvoiceLine")
            cbc_id_10 = ET.SubElement(cac_invoiceline, "cbc:ID")
            cbc_id_10.text = str(single_item.idx)
            cbc_invoicedquantity = ET.SubElement(
                cac_invoiceline, "cbc:InvoicedQuantity"
            )
            cbc_invoicedquantity.set("unitCode", str(single_item.uom))
            cbc_invoicedquantity.text = str(abs(single_item.qty))
            cbc_lineextensionamount_1 = ET.SubElement(
                cac_invoiceline, "cbc:LineExtensionAmount"
            )
            cbc_lineextensionamount_1.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )

            if sales_invoice_doc.currency == "SAR":
                # if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
                # Tax is not included in print rate
                cbc_lineextensionamount_1.text = str(abs(single_item.base_amount))
                # elif sales_invoice_doc.taxes[0].included_in_print_rate == 1:
                #     # Tax is included in print rate
                #     cbc_lineextensionamount_1.text = str(
                #         abs(
                #             round(
                #                 single_item.base_amount
                #                 / (1 + sales_invoice_doc.taxes[0].rate / 100),
                #                 2,
                #             )
                #         )
                #     )
            else:
                # For other currencies
                # if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
                cbc_lineextensionamount_1.text = str(abs(single_item.amount))
                # else:

                #     cbc_lineextensionamount_1.text = str(
                #         abs(
                #             round(
                #                 single_item.amount
                #                 / (1 + sales_invoice_doc.taxes[0].rate / 100),
                #                 2,
                #             )
                #         )
                #     )

            cac_taxtotal_2 = ET.SubElement(cac_invoiceline, CAC_TAX_TOTAL)
            cbc_taxamount_3 = ET.SubElement(cac_taxtotal_2, CBC_TAX_AMOUNT)
            cbc_taxamount_3.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )
            # if sales_invoice_doc.taxes[0].included_in_print_rate == 1:
            #     cbc_taxamount_3.text = str(
            #         abs(
            #             round(
            #                 single_item.base_amount
            #                 * sales_invoice_doc.taxes[0].rate
            #                 / (100 + sales_invoice_doc.taxes[0].rate),
            #                 2,
            #             )
            #         )
            #     )

            # else:
            # cbc_taxamount_3.text = str(
            #     abs(custom_round(item_tax_percentage * single_item.amount / 100))
            # )

            cbc_taxamount_3.text = str(
                Decimal(
                    str(abs(item_tax_percentage * single_item.amount / 100))
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            )
            cbc_roundingamount = ET.SubElement(cac_taxtotal_2, "cbc:RoundingAmount")
            cbc_roundingamount.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )
            lineextensionamount = float(cbc_lineextensionamount_1.text)
            taxamount = float(cbc_taxamount_3.text)
            # frappe.throw(f"Tax Amount1: {taxamount}")
            cbc_roundingamount.text = str(round(lineextensionamount + taxamount, 2))
            cac_item = ET.SubElement(cac_invoiceline, "cac:Item")
            cbc_name = ET.SubElement(cac_item, "cbc:Name")
            cbc_name.text = f"{single_item.item_code}:{single_item.item_name}"

            cac_classifiedtaxcategory = ET.SubElement(
                cac_item, "cac:ClassifiedTaxCategory"
            )
            cbc_id_11 = ET.SubElement(cac_classifiedtaxcategory, "cbc:ID")
            if sales_invoice_doc.custom_zatca_tax_category == "Standard":
                cbc_id_11.text = "S"
            elif sales_invoice_doc.custom_zatca_tax_category == ZERO_RATED:
                cbc_id_11.text = "Z"
            elif sales_invoice_doc.custom_zatca_tax_category == "Exempted":
                cbc_id_11.text = "E"
            elif sales_invoice_doc.custom_zatca_tax_category == OUTSIDE_SCOPE:
                cbc_id_11.text = "O"
            cbc_percent_2 = ET.SubElement(cac_classifiedtaxcategory, "cbc:Percent")
            cbc_percent_2.text = f"{float(item_tax_percentage):.2f}"
            cac_taxscheme_4 = ET.SubElement(cac_classifiedtaxcategory, "cac:TaxScheme")
            cbc_id_12 = ET.SubElement(cac_taxscheme_4, "cbc:ID")
            cbc_id_12.text = "VAT"
            cac_price = ET.SubElement(cac_invoiceline, "cac:Price")
            cbc_priceamount = ET.SubElement(cac_price, "cbc:PriceAmount")
            cbc_priceamount.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )

            # if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
            cbc_priceamount.text = str(abs(single_item.rate))
            # Case 4: No Discount Submission to ZATCA, Tax Included in Print Rate
            # elif sales_invoice_doc.taxes[0].included_in_print_rate == 1:
            #     cbc_priceamount.text = str(
            #         abs(
            #             round(
            #                 single_item.rate
            #                 / (1 + sales_invoice_doc.taxes[0].rate / 100),
            #                 2,
            #             )
            #         )
            #     )

            cac_invoiceline_adv = ET.SubElement(invoice, "cac:InvoiceLine")
            ET.SubElement(cac_invoiceline_adv, "cbc:ID").text = str(single_item.idx + 1)
            ET.SubElement(
                cac_invoiceline_adv,
                "cbc:InvoicedQuantity",
                unitCode=str(single_item.uom),
            ).text = "0.000000"
            ET.SubElement(
                cac_invoiceline_adv,
                "cbc:LineExtensionAmount",
                currencyID=sales_invoice_doc.paid_from_account_currency,
            ).text = "0.00"

            cac_docref = ET.SubElement(cac_invoiceline_adv, "cac:DocumentReference")
            ET.SubElement(cac_docref, "cbc:ID").text = str(get_icv_code(invoice_number))
            # ET.SubElement(cac_docref, "cbc:UUID").text = (
            #     "a79760f7-2f48-4da9-85a5-40459a147c80"
            # )
            current_date = datetime.now().strftime("%Y-%m-%d")
            ET.SubElement(cac_docref, "cbc:IssueDate").text = current_date
            current_time = datetime.now().strftime("%H:%M:%S")
            ET.SubElement(cac_docref, "cbc:IssueTime").text = current_time
            ET.SubElement(cac_docref, "cbc:DocumentTypeCode").text = "386"

            cac_taxtotal_adv = ET.SubElement(cac_invoiceline_adv, CAC_TAX_TOTAL)
            ET.SubElement(
                cac_taxtotal_adv,
                CBC_TAX_AMOUNT,
                currencyID=sales_invoice_doc.paid_from_account_currency,
            ).text = "0"
            ET.SubElement(
                cac_taxtotal_adv,
                "cbc:RoundingAmount",
                currencyID=sales_invoice_doc.paid_from_account_currency,
            ).text = "0"

            cac_taxsubtotal_adv = ET.SubElement(cac_taxtotal_adv, "cac:TaxSubtotal")
            ET.SubElement(
                cac_taxsubtotal_adv,
                "cbc:TaxableAmount",
                currencyID=sales_invoice_doc.paid_from_account_currency,
            ).text = str(abs(single_item.amount))
            ET.SubElement(
                cac_taxsubtotal_adv,
                "cbc:TaxAmount",
                currencyID=sales_invoice_doc.paid_from_account_currency,
            ).text = str(abs(round(single_item.amount * item_tax_percentage / 100, 2)))

            cac_taxcategory_adv = ET.SubElement(cac_taxsubtotal_adv, "cac:TaxCategory")
            cbc_id_adv = ET.SubElement(cac_taxcategory_adv, "cbc:ID")
            cbc_id_adv.text = {
                "Standard": "S",
                ZERO_RATED: "Z",
                "Exempted": "E",
                OUTSIDE_SCOPE: "O",
            }.get(sales_invoice_doc.custom_zatca_tax_category, "S")
            cbc_percent_adv = ET.SubElement(cac_taxcategory_adv, "cbc:Percent")
            cbc_percent_adv.text = f"{float(item_tax_percentage):.2f}"

            cac_taxscheme_adv = ET.SubElement(cac_taxcategory_adv, "cac:TaxScheme")
            ET.SubElement(cac_taxscheme_adv, "cbc:ID").text = "VAT"

            cac_item_adv = ET.SubElement(cac_invoiceline_adv, "cac:Item")
            ET.SubElement(cac_item_adv, "cbc:Name").text = (
                f"{single_item.item_code}:{single_item.item_name}"
            )

            cac_classifiedtaxcategory_adv = ET.SubElement(
                cac_item_adv, "cac:ClassifiedTaxCategory"
            )
            ET.SubElement(cac_classifiedtaxcategory_adv, "cbc:ID").text = (
                cbc_id_adv.text
            )
            ET.SubElement(cac_classifiedtaxcategory_adv, "cbc:Percent").text = (
                cbc_percent_adv.text
            )
            cac_taxscheme_item_adv = ET.SubElement(
                cac_classifiedtaxcategory_adv, "cac:TaxScheme"
            )
            ET.SubElement(cac_taxscheme_item_adv, "cbc:ID").text = "VAT"

            cac_price_adv = ET.SubElement(cac_invoiceline_adv, "cac:Price")
            ET.SubElement(
                cac_price_adv,
                "cbc:PriceAmount",
                currencyID=sales_invoice_doc.paid_from_account_currency,
            ).text = "0.00"
        return invoice
    except (ValueError, KeyError, TypeError) as e:
        frappe.throw(f"Error occurred in item data processing: {str(e)}")
        return None


def custom_round(value):
    """Rounding CCording to our need"""
    # Convert the value to a Decimal for accurate handling
    decimal_value = Decimal(str(value))

    # Check if the number has less than 3 decimal places
    if decimal_value.as_tuple().exponent >= -2:
        # If there are less than 3 decimal places, return the original value as float
        return float(decimal_value)

    # Extract the third decimal digit accurately
    third_digit = int((decimal_value * 1000) % 10)

    # Check if the third digit is strictly greater than 5
    if third_digit > 5:
        # Increment the rounded result by 0.01 to ensure rounding up
        return float(decimal_value.quantize(Decimal("0.01")))
    elif third_digit == 5:
        # If the third digit is exactly 5, ensure we round down as desired
        return float(decimal_value.quantize(Decimal("0.01"), rounding=ROUND_DOWN))
    else:
        # Otherwise, round normally to 2 decimal places using ROUND_DOWN
        return float(decimal_value.quantize(Decimal("0.01"), rounding=ROUND_DOWN))


def item_data_with_template_adavance(invoice, sales_invoice_doc):
    """The defining of xml item data according to the item tax template datas and feilds"""
    try:
        for single_item in sales_invoice_doc.custom_item:
            item_tax_template = frappe.get_doc(
                ITEM_TAX_TEMPLATE, single_item.item_tax_template
            )
            item_tax_percentage = (
                item_tax_template.taxes[0].tax_rate if item_tax_template.taxes else 15
            )

            cac_invoiceline = ET.SubElement(invoice, "cac:InvoiceLine")
            cbc_id_10 = ET.SubElement(cac_invoiceline, "cbc:ID")
            cbc_id_10.text = str(single_item.idx)
            cbc_invoicedquantity = ET.SubElement(
                cac_invoiceline, "cbc:InvoicedQuantity"
            )
            cbc_invoicedquantity.set("unitCode", str(single_item.uom))
            cbc_invoicedquantity.text = str(abs(single_item.qty))
            cbc_lineextensionamount_1 = ET.SubElement(
                cac_invoiceline, "cbc:LineExtensionAmount"
            )
            cbc_lineextensionamount_1.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )
            cbc_lineextensionamount_1.text = str(abs(single_item.amount))

            cac_taxtotal_2 = ET.SubElement(cac_invoiceline, CAC_TAX_TOTAL)
            cbc_taxamount_3 = ET.SubElement(cac_taxtotal_2, CBC_TAX_AMOUNT)
            cbc_taxamount_3.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )
            cbc_taxamount_3.text = str(
                abs(
                    (
                        Decimal(str(item_tax_percentage))
                        * Decimal(str(single_item.amount))
                        / Decimal("100")
                    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                )
            )
            cbc_roundingamount = ET.SubElement(cac_taxtotal_2, "cbc:RoundingAmount")
            cbc_roundingamount.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )
            cbc_roundingamount.text = str(
                abs(
                    (
                        Decimal(str(single_item.amount))
                        + (
                            Decimal(str(item_tax_percentage))
                            * Decimal(str(single_item.amount))
                            / Decimal("100")
                        )
                    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                )
            )
            cac_item = ET.SubElement(cac_invoiceline, "cac:Item")
            cbc_name = ET.SubElement(cac_item, "cbc:Name")
            cbc_name.text = f"{single_item.item_code}:{single_item.item_name}"

            cac_classifiedtaxcategory = ET.SubElement(
                cac_item, "cac:ClassifiedTaxCategory"
            )
            cbc_id_11 = ET.SubElement(cac_classifiedtaxcategory, "cbc:ID")
            zatca_tax_category = item_tax_template.custom_zatca_tax_category
            if zatca_tax_category == "Standard":
                cbc_id_11.text = "S"
            elif zatca_tax_category == ZERO_RATED:
                cbc_id_11.text = "Z"
            elif zatca_tax_category == "Exempted":
                cbc_id_11.text = "E"
            elif zatca_tax_category == OUTSIDE_SCOPE:
                cbc_id_11.text = "O"

            cbc_percent_2 = ET.SubElement(cac_classifiedtaxcategory, "cbc:Percent")
            cbc_percent_2.text = f"{float(item_tax_percentage):.2f}"

            cac_taxscheme_4 = ET.SubElement(cac_classifiedtaxcategory, "cac:TaxScheme")
            cbc_id_12 = ET.SubElement(cac_taxscheme_4, "cbc:ID")
            cbc_id_12.text = "VAT"

            cac_price = ET.SubElement(cac_invoiceline, "cac:Price")
            cbc_priceamount = ET.SubElement(cac_price, "cbc:PriceAmount")
            cbc_priceamount.set(
                "currencyID", sales_invoice_doc.paid_from_account_currency
            )
            cbc_priceamount.text = f"{abs(single_item.rate):.6f}"

        return invoice
    except (ValueError, KeyError, TypeError) as e:
        frappe.throw(f"Error occurred in item template data processing: {str(e)}")
        return None


def xml_structuring_advance(invoice):
    """
    Xml structuring and final saving of the xml into private files
    """
    try:

        tree = ET.ElementTree(invoice)
        xml_file_path = frappe.local.site + "/private/files/xml_filesadavance1.xml"

        # Save the XML tree to a file
        with open(xml_file_path, "wb") as file:
            tree.write(file, encoding="utf-8", xml_declaration=True)

        # Read the XML file and format it
        with open(xml_file_path, "r", encoding="utf-8") as file:
            xml_string = file.read()

        # Format the XML string to make it pretty
        xml_dom = minidom.parseString(xml_string)
        pretty_xml_string = xml_dom.toprettyxml(indent="  ")

        # Write the formatted XML to the final file
        final_xml_path = frappe.local.site + "/private/files/finalzatcaxmladavance1.xml"
        with open(final_xml_path, "w", encoding="utf-8") as file:
            file.write(pretty_xml_string)

    except (FileNotFoundError, IOError):
        frappe.throw(
            "File operation error occurred while structuring the XML. "
            "Please contact your system administrator."
        )

    except ET.ParseError:
        frappe.throw(
            "Error occurred in XML parsing or formatting. "
            "Please check the XML structure for errors. "
            "If the problem persists, contact your system administrator."
        )
    except UnicodeDecodeError:
        frappe.throw(
            "Encoding error occurred while processing the XML file. "
            "Please contact your system administrator."
        )


def xml_base64_decode(signed_xmlfile_name):
    """xml base64 decode"""
    try:
        with open(signed_xmlfile_name, "r", encoding="utf-8") as file:
            xml = file.read().lstrip()
            base64_encoded = base64.b64encode(xml.encode("utf-8"))
            base64_decoded = base64_encoded.decode("utf-8")
            return base64_decoded
    except (ValueError, TypeError, KeyError) as e:
        frappe.throw(("xml decode base64" f"error: {str(e)}"))
        return None


def success_log(response, uuid1, invoice_number):
    """defining the success log"""
    try:
        current_time = frappe.utils.now()
        frappe.get_doc(
            {
                "doctype": "Zatca ERPgulf Success Log",
                "title": "Zatca invoice call done successfully",
                "message": "This message by Zatca Compliance",
                "uuid": uuid1,
                "invoice_number": invoice_number,
                "time": current_time,
                "zatca_response": response,
            }
        ).insert(ignore_permissions=True)
    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        frappe.throw(("error in success log" f"error: {str(e)}"))
        return None


def error_log():
    """defining the error log"""
    try:
        frappe.log_error(
            title="Zatca invoice call failed in clearance status",
            message=frappe.get_traceback(),
        )
    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        frappe.throw(("error in error log" f"error: {str(e)}"))
        return None


def clearance_api(
    uuid1, encoded_hash, signed_xmlfile_name, invoice_number, sales_invoice_doc
):
    """The clearance api with payload and headeders aand signed xml data"""
    try:
        company_abbr = frappe.db.get_value(
            "Company", {"name": sales_invoice_doc.company}, "abbr"
        )
        if not company_abbr:
            frappe.throw(
                f" problem with company name in {sales_invoice_doc.company} not found."
            )
        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})
        production_csid = company_doc.custom_basic_auth_from_production or ""
        payload = {
            "invoiceHash": encoded_hash,
            "uuid": uuid1,
            "invoice": xml_base64_decode(signed_xmlfile_name),
        }

        if production_csid:
            headers = {
                "accept": "application/json",
                "accept-language": "en",
                "Clearance-Status": "1",
                "Accept-Version": "V2",
                "Authorization": "Basic " + production_csid,
                "Content-Type": "application/json",
                "Cookie": "TS0106293e=0132a679c03c628e6c49de86c0f6bb76390abb4416868d6368d6d7c05da619c8326266f5bc262b7c0c65a6863cd3b19081d64eee99",
            }
        else:
            frappe.throw(f"Production CSID for company {company_abbr} not found.")
            headers = None
        frappe.publish_realtime(
            "show_gif",
            {"gif_url": "/assets/zatca_erpgulf/js/loading.gif"},
            user=frappe.session.user,
        )

        response = requests.post(
            url=get_api_url(company_abbr, base_url="invoices/clearance/single"),
            headers=headers,
            json=payload,
            timeout=300,
        )
        frappe.publish_realtime("hide_gif", user=frappe.session.user)

        if response.status_code in (400, 405, 406, 409):
            invoice_doc = frappe.get_doc("Advance Sales Invoice", invoice_number)
            invoice_doc.db_set(
                "custom_uuid", "Not Submitted", commit=True, update_modified=True
            )
            invoice_doc.db_set(
                "custom_zatca_status",
                "Not Submitted",
                commit=True,
                update_modified=True,
            )
            invoice_doc.db_set("custom_zatca_full_response", "Not Submitted")
            frappe.throw(
                (
                    "Error: The request you are sending to Zatca is in incorrect format. "
                    f"Status code: {response.status_code}<br><br>"
                    f"{response.text}"
                )
            )
        if response.status_code in (401, 403, 407, 451):
            invoice_doc = frappe.get_doc("Advance Sales Invoice", invoice_number)
            invoice_doc.db_set(
                "custom_uuid", "Not Submitted", commit=True, update_modified=True
            )
            invoice_doc.db_set(
                "custom_zatca_status",
                "Not Submitted",
                commit=True,
                update_modified=True,
            )
            invoice_doc.db_set("custom_zatca_full_response", "Not Submitted")
            frappe.throw(
                (
                    "Error: Zatca Authentication failed. "
                    f"Status code: {response.status_code}<br><br>"
                    f"{response.text}"
                )
            )
        if response.status_code not in (200, 202):
            invoice_doc = frappe.get_doc("Advance Sales Invoice", invoice_number)
            invoice_doc.db_set(
                "custom_uuid", "Not Submitted", commit=True, update_modified=True
            )
            invoice_doc.db_set(
                "custom_zatca_status",
                "Not Submitted",
                commit=True,
                update_modified=True,
            )
            invoice_doc.db_set("custom_zatca_full_response", "Not Submitted")
            frappe.throw(
                f"Error: Zatca server busy or not responding. Status code: {response.status_code}"
            )

        if response.status_code in (200, 202):
            msg = (
                "CLEARED WITH WARNINGS: <br><br>"
                if response.status_code == 202
                else "SUCCESS: <br><br>"
            )
            msg += (
                f"Status Code: {response.status_code}<br><br>"
                f"Zatca Response: {response.text}<br><br>"
            )

            company_name = sales_invoice_doc.company
            settings = frappe.get_doc("Company", company_name)
            company_abbr = settings.abbr
            if settings.custom_send_einvoice_background:
                frappe.msgprint(msg)

                # Update PIH data without JSON formatting
            company_doc.custom_pih = encoded_hash
            company_doc.save(ignore_permissions=True)

            invoice_doc = frappe.get_doc("Advance Sales Invoice", invoice_number)
            invoice_doc.db_set(
                "custom_zatca_full_response", msg, commit=True, update_modified=True
            )
            invoice_doc.db_set("custom_uuid", uuid1, commit=True, update_modified=True)
            invoice_doc.db_set(
                "custom_zatca_status", "CLEARED", commit=True, update_modified=True
            )

            data = response.json()
            base64_xml = data.get("clearedInvoice")
            xml_cleared = base64.b64decode(base64_xml).decode("utf-8")
            file = frappe.get_doc(
                {
                    "doctype": "File",
                    "file_name": "Cleared Advance xml file "
                    + sales_invoice_doc.name
                    + ".xml",
                    "attached_to_doctype": sales_invoice_doc.doctype,
                    "is_private": 1,
                    "attached_to_name": sales_invoice_doc.name,
                    "content": xml_cleared,
                }
            )
            file.save(ignore_permissions=True)
            sales_invoice_doc.db_set("custom_ksa_einvoicing_xml", file.file_url)
            success_log(response.text, uuid1, invoice_number)
            return xml_cleared
        else:
            error_log()

    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        invoice_doc = frappe.get_doc("Advance Sales Invoice", invoice_number)
        invoice_doc.db_set(
            "custom_zatca_full_response",
            f"Error: {str(e)}",
            commit=True,
            update_modified=True,
        )
        invoice_doc.db_set(
            "custom_zatca_status",
            "503 Service Unavailable",
            commit=True,
            update_modified=True,
        )
        frappe.throw(f"Error in clearance API: {str(e)}")


def invoice_typecode_standard_advance(invoice, sales_invoice_doc):
    """
    Sets the InvoiceTypeCode for a standard invoice based on sales invoice document attributes.
    """
    try:
        cbc_invoicetypecode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")

        cbc_invoicetypecode.set("name", "0100000")
        cbc_invoicetypecode.text = "386"
        return invoice
    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(f"Error in standard invoice type code: {e}")
        return None


def invoice_typecode_compliance_advance(invoice, compliance_type):
    """
    Creates and populates XML tags for a UBL Invoice document.
    """

    try:

        if compliance_type == "1":  # simplified invoice
            cbc_invoicetypecode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
            cbc_invoicetypecode.set("name", "0200000")
            cbc_invoicetypecode.text = "388"

        elif compliance_type == "2":  # standard invoice
            cbc_invoicetypecode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
            cbc_invoicetypecode.set("name", "0100000")
            cbc_invoicetypecode.text = "388"

        elif compliance_type == "3":  # simplified Credit note
            cbc_invoicetypecode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
            cbc_invoicetypecode.set("name", "0200000")
            cbc_invoicetypecode.text = "381"

        elif compliance_type == "4":  # Standard Credit note
            cbc_invoicetypecode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
            cbc_invoicetypecode.set("name", "0100000")
            cbc_invoicetypecode.text = "381"

        elif compliance_type == "5":  # simplified Debit note
            cbc_invoicetypecode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
            cbc_invoicetypecode.set("name", "0211000")
            cbc_invoicetypecode.text = "383"

        elif compliance_type == "6":  # Standard Debit note
            cbc_invoicetypecode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
            cbc_invoicetypecode.set("name", "0100000")
            cbc_invoicetypecode.text = "383"
        return invoice

    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(f"Error occurred in compliance typecode: {e}")
        return None


def doc_reference_advance(invoice, sales_invoice_doc, invoice_number):
    """
    Adds document reference elements to the XML invoice,
    including currency codes and additional document references.
    """
    try:
        cbc_documentcurrencycode = ET.SubElement(invoice, "cbc:DocumentCurrencyCode")
        cbc_documentcurrencycode.text = sales_invoice_doc.paid_from_account_currency
        cbc_taxcurrencycode = ET.SubElement(invoice, "cbc:TaxCurrencyCode")
        cbc_taxcurrencycode.text = "SAR"  # SAR is as zatca requires tax amount in SAR

        cac_additionaldocumentreference = ET.SubElement(
            invoice, "cac:AdditionalDocumentReference"
        )
        cbc_id_1 = ET.SubElement(cac_additionaldocumentreference, CBC_ID)
        cbc_id_1.text = "ICV"
        cbc_uuid_1 = ET.SubElement(cac_additionaldocumentreference, "cbc:UUID")
        cbc_uuid_1.text = str(get_icv_code(invoice_number))
        return invoice
    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(f"Error occurred in reference doc: {e}")
        return None


@frappe.whitelist(allow_guest=False)
def zatca_call(
    invoice_number,
    compliance_type="0",
    any_item_has_tax_template=False,
    company_abbr=None,
    source_doc=None,
):
    """zatca call which includes the function calling and validation reguarding the api and
    based on this the zATCA output and message is getting"""
    try:
        if not frappe.db.exists("Advance Sales Invoice", invoice_number):
            frappe.throw("Invoice Number is NOT Valid: " + str(invoice_number))
        invoice = xml_tags()
        invoice, uuid1, sales_invoice_doc = salesinvoice_data_advance(
            invoice, invoice_number
        )
        # Get the company abbreviation
        company_abbr = frappe.db.get_value(
            "Company", {"name": sales_invoice_doc.company}, "abbr"
        )

        customer_doc = frappe.get_doc("Customer", sales_invoice_doc.party)
        # frappe.throw(str(customer_doc))

        invoice = invoice_typecode_standard_advance(invoice, sales_invoice_doc)

        invoice = doc_reference_advance(invoice, sales_invoice_doc, invoice_number)
        invoice = additional_reference_advanve(invoice, company_abbr, sales_invoice_doc)
        invoice = company_data_advance(invoice, sales_invoice_doc)
        invoice = customer_data_advance(invoice, sales_invoice_doc)
        invoice = delivery_and_payment_means_adavance(invoice, sales_invoice_doc)
        # frappe.throw(str(sales_invoice_doc))
        if not any_item_has_tax_template:
            invoice = tax_data(invoice, sales_invoice_doc)
            # frappe.msgprint("invoiceis", str(invoice))
        else:
            invoice = tax_data_with_template(invoice, sales_invoice_doc)
            # frappe.msgprint(invoice)

        if not any_item_has_tax_template:
            invoice = item_data_advance(invoice, sales_invoice_doc, invoice_number)
            # frappe.msgprint(invoice)
        else:
            invoice = item_data_with_template_adavance(invoice, sales_invoice_doc)
            # frappe.msgprint(invoice)
        xml_structuring_advance(invoice)

        with open(
            frappe.local.site + "/private/files/finalzatcaxmladavance1.xml",
            "r",
            encoding="utf-8",
        ) as file:
            file_content = file.read()
            # frappe.msgprint(file_content)

        tag_removed_xml = removetags(file_content)
        canonicalized_xml = canonicalize_xml(tag_removed_xml)
        hash1, encoded_hash = getinvoicehash(canonicalized_xml)
        encoded_signature = digital_signature(hash1, company_abbr, source_doc)
        issuer_name, serial_number = extract_certificate_details(
            company_abbr, source_doc
        )
        encoded_certificate_hash = certificate_hash(company_abbr, source_doc)
        namespaces, signing_time = signxml_modify(company_abbr, source_doc)
        signed_properties_base64 = generate_signed_properties_hash(
            signing_time, issuer_name, serial_number, encoded_certificate_hash
        )
        populate_the_ubl_extensions_output(
            encoded_signature,
            namespaces,
            signed_properties_base64,
            encoded_hash,
            company_abbr,
            source_doc,
        )
        tlv_data = generate_tlv_xml(company_abbr, source_doc)

        tagsbufsarray = []
        for tag_num, tag_value in tlv_data.items():
            tagsbufsarray.append(get_tlv_for_value(tag_num, tag_value))

        qrcodebuf = b"".join(tagsbufsarray)
        qrcodeb64 = base64.b64encode(qrcodebuf).decode("utf-8")
        update_qr_toxml(qrcodeb64, company_abbr)
        signed_xmlfile_name = structuring_signedxml()
        # Example usage
        # # file_path = generate_invoice_pdf(
        # #     invoice_number, l anguage="en", letterhead="Sample letterhead"
        # )
        # frappe.throw(f"PDF saved at: {signed_xmlfile_name}")
        if compliance_type == "0":
            # if customer_doc.custom_b2c != 1:

            clearance_api(
                uuid1,
                encoded_hash,
                signed_xmlfile_name,
                invoice_number,
                sales_invoice_doc,
            )
            attach_qr_image(qrcodeb64, sales_invoice_doc)
        else:
            compliance_api_call(
                uuid1,
                encoded_hash,
                signed_xmlfile_name,
                company_abbr,
                source_doc,
            )
            attach_qr_image(qrcodeb64, sales_invoice_doc)

    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        frappe.log_error(
            title="Zatca invoice call failed",
            message=f"{frappe.get_traceback()}\nError: {str(e)}",
        )


@frappe.whitelist(allow_guest=False)
def zatca_background_on_submit(doc, _method=None, bypass_background_check=False):
    """referes according to the ZATC based sytem with the submitbutton of the sales invoice"""
    try:
        source_doc = doc
        sales_invoice_doc = doc
        invoice_number = sales_invoice_doc.name
        sales_invoice_doc = frappe.get_doc("Advance Sales Invoice", invoice_number)
        company_abbr = frappe.db.get_value(
            "Company", {"name": sales_invoice_doc.company}, "abbr"
        )
        if not company_abbr:
            frappe.throw(
                f"Company abbreviation for {sales_invoice_doc.company} not found."
            )
        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})
        if company_doc.custom_zatca_invoice_enabled != 1:
            # frappe.msgprint("Zatca Invoice is not enabled. Submitting the document.")
            return  # Exit the function without further checks

        # if (
        #     sales_invoice_doc.taxes
        #     and sales_invoice_doc.taxes[0].included_in_print_rate == 1
        # ):
        #     if any(item.item_tax_template for item in sales_invoice_doc.custom_item):
        #         frappe.throw(
        #             "Item Tax Template cannot be used when taxes are included"
        #             " in the print rate. Please remove Item Tax Templates."
        # )
        any_item_has_tax_template = False
        for item in sales_invoice_doc.custom_item:
            if item.item_tax_template:
                any_item_has_tax_template = True
                break
        if any_item_has_tax_template:
            for item in sales_invoice_doc.custom_item:
                if not item.item_tax_template:
                    frappe.throw(
                        "If any one item has an Item Tax Template,"
                        " all items must have an Item Tax Template."
                    )
        tax_categories = set()
        for item in sales_invoice_doc.custom_item:
            if item.item_tax_template:
                item_tax_template = frappe.get_doc(
                    "Item Tax Template", item.item_tax_template
                )
                zatca_tax_category = item_tax_template.custom_zatca_tax_category
                tax_categories.add(zatca_tax_category)
                for tax in item_tax_template.taxes:
                    tax_rate = float(tax.tax_rate)

                    if f"{tax_rate:.2f}" not in [
                        "5.00",
                        "15.00",
                    ] and zatca_tax_category not in [
                        "Zero Rated",
                        "Exempted",
                        "Services outside scope of tax / Not subject to VAT",
                    ]:
                        frappe.throw(
                            "Zatca tax category should be 'Zero Rated', 'Exempted', or "
                            "'Services outside scope of tax / Not subject to VAT' "
                            "for items with tax rate not equal to 5.00 or 15.00."
                        )

                    if (
                        f"{tax_rate:.2f}" == "15.00"
                        and zatca_tax_category != "Standard"
                    ):
                        frappe.throw(
                            "Check the Zatca category code and enable it as Standard."
                        )

        if not frappe.db.exists("Advance Sales Invoice", invoice_number):
            frappe.throw(
                f"Please save and submit the invoice before sending to ZATCA: {invoice_number}"
            )

        if sales_invoice_doc.docstatus in [0, 2]:
            frappe.throw(
                f"Please submit the invoice before sending to ZATCA: {invoice_number}"
            )
        if sales_invoice_doc.custom_zatca_status in ["REPORTED", "CLEARED"]:
            frappe.throw(
                "This invoice has already been submitted to Zakat and Tax Authority."
            )
        company_name = sales_invoice_doc.company
        settings = frappe.get_doc("Company", company_name)
        # if settings.custom_phase_1_or_2 == "Phase-2":

        if settings.custom_phase_1_or_2 == "Phase-2":
            zatca_call(
                invoice_number,
                "0",
                any_item_has_tax_template,
                company_abbr,
                source_doc,
            )

        else:
            create_qr_code(sales_invoice_doc, method=None)
        doc.reload()
    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        frappe.throw(f"Error in background call: {str(e)}")
