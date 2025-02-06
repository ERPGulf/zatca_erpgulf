"""
This module contains utilities for ZATCA 2024 e-invoicing.
Includes functions for XML parsing, API interactions, and custom handling.
"""

from decimal import Decimal, ROUND_DOWN
import xml.etree.ElementTree as ET
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


def tax_data_with_template_nominal(invoice, sales_invoice_doc):
    """
    Adding tax data of nominal  invoices which  having
    item tax template
    """
    try:
        # For SAR currency
        if sales_invoice_doc.currency == "SAR":
            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount_sar = ET.SubElement(cac_taxtotal, CBC_TAX_AMOUNT)
            cbc_taxamount_sar.set(
                "currencyID", "SAR"
            )  # SAR is as ZATCA requires tax amount in SAR

            tax_amount_without_retention_sar = (
                sales_invoice_doc.base_total
                * float(sales_invoice_doc.taxes[0].rate)
                / 100
            )
            cbc_taxamount_sar.text = str(round(tax_amount_without_retention_sar, 2))

            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount = ET.SubElement(cac_taxtotal, CBC_TAX_AMOUNT)
            cbc_taxamount.set("currencyID", sales_invoice_doc.currency)
            cbc_taxamount.text = (
                f"{abs(round(tax_amount_without_retention_sar, 2)):.2f}"
            )
        else:
            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount_sar = ET.SubElement(cac_taxtotal, CBC_TAX_AMOUNT)
            cbc_taxamount_sar.set("currencyID", sales_invoice_doc.currency)
            tax_amount_without_retention_sar = (
                sales_invoice_doc.total * float(sales_invoice_doc.taxes[0].rate) / 100
            )
            cbc_taxamount_sar.text = str(tax_amount_without_retention_sar)

            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount = ET.SubElement(cac_taxtotal, CBC_TAX_AMOUNT)
            cbc_taxamount.set("currencyID", sales_invoice_doc.currency)
            cbc_taxamount.text = str(tax_amount_without_retention_sar)

        # Group items by ZATCA tax category
        tax_category_totals = {}

        for item in sales_invoice_doc.items:
            item_tax_template = frappe.get_doc(
                ITEM_TAX_TEMPLATE, item.item_tax_template
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
            if sales_invoice_doc.currency == "SAR":
                tax_category_totals[zatca_tax_category]["taxable_amount"] += abs(
                    item.base_amount
                )
            else:
                tax_category_totals[zatca_tax_category]["taxable_amount"] += abs(
                    item.amount
                )

        first_tax_category = next(iter(tax_category_totals))
        tax_category_totals[first_tax_category]["taxable_amount"] -= abs(
            sales_invoice_doc.get("discount_amount", 0.0)
        )

        for item in sales_invoice_doc.items:
            item_tax_template = frappe.get_doc(
                ITEM_TAX_TEMPLATE, item.item_tax_template
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

        # Use the same technique for calculating tax amount
        for zatca_tax_category, totals in tax_category_totals.items():
            totals["tax_amount"] = abs(
                round(totals["taxable_amount"] * totals["tax_rate"] / 100, 2)
            )

        # Create XML elements for each ZATCA tax category
        for zatca_tax_category, totals in tax_category_totals.items():
            cac_taxsubtotal = ET.SubElement(cac_taxtotal, CAC_TAX_SUBTOTAL)
            cbc_taxableamount = ET.SubElement(cac_taxsubtotal, CBC_TAXABLE_AMOUNT)
            cbc_taxableamount.set("currencyID", sales_invoice_doc.currency)
            cbc_taxableamount.text = str(abs(round(sales_invoice_doc.base_total, 2)))

            cbc_taxamount_2 = ET.SubElement(cac_taxsubtotal, CBC_TAX_AMOUNT)
            cbc_taxamount_2.set("currencyID", sales_invoice_doc.currency)
            cbc_taxamount_2.text = (
                f"{abs(round(tax_amount_without_retention_sar, 2)):.2f}"
            )
            cac_taxcategory_1 = ET.SubElement(cac_taxsubtotal, "cac:TaxCategory")
            cbc_id_8 = ET.SubElement(cac_taxcategory_1, "cbc:ID")
            zatca_tax_category = item_tax_template.custom_zatca_tax_category

            if zatca_tax_category == "Standard":
                cbc_id_8.text = "S"
            elif zatca_tax_category == ZERO_RATED:
                cbc_id_8.text = "Z"
            elif zatca_tax_category == "Exempted":
                cbc_id_8.text = "E"
            elif zatca_tax_category == OUTSIDE_SCOPE:
                cbc_id_8.text = "O"

            cbc_percent_1 = ET.SubElement(cac_taxcategory_1, "cbc:Percent")
            cbc_percent_1.text = (
                f"{item_tax_template.taxes[0].tax_rate:.2f}"
                if item_tax_template.taxes
                else "15.00"
            )

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

        cac_taxsubtotal_2 = ET.SubElement(cac_taxtotal, CAC_TAX_SUBTOTAL)
        cbc_taxableamount_2 = ET.SubElement(cac_taxsubtotal_2, CBC_TAXABLE_AMOUNT)
        cbc_taxableamount_2.set("currencyID", "SAR")
        cbc_taxableamount_2.text = str(-round(abs(sales_invoice_doc.total), 2))

        cbc_taxamount_3 = ET.SubElement(cac_taxsubtotal_2, CBC_TAX_AMOUNT)
        cbc_taxamount_3.set("currencyID", "SAR")
        cbc_taxamount_3.text = "0.0"

        cac_taxcategory_2 = ET.SubElement(cac_taxsubtotal_2, "cac:TaxCategory")
        cbc_id_9 = ET.SubElement(cac_taxcategory_2, "cbc:ID")
        cbc_id_9.text = "O"

        cbc_percent_2 = ET.SubElement(cac_taxcategory_2, "cbc:Percent")
        cbc_percent_2.text = "0.00"

        cbc_taxexemptionreasoncode = ET.SubElement(
            cac_taxcategory_2, "cbc:TaxExemptionReasonCode"
        )
        cbc_taxexemptionreasoncode.text = "VATEX-SA-OOS"

        cbc_taxexemptionreason = ET.SubElement(
            cac_taxcategory_2, "cbc:TaxExemptionReason"
        )
        cbc_taxexemptionreason.text = "Nominal Invoice"

        cac_taxscheme_2 = ET.SubElement(cac_taxcategory_2, "cac:TaxScheme")
        cbc_id_10 = ET.SubElement(cac_taxscheme_2, "cbc:ID")
        cbc_id_10.text = "VAT"
        # Discount
        cac_legalmonetarytotal = ET.SubElement(invoice, "cac:LegalMonetaryTotal")
        cbc_lineextensionamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:LineExtensionAmount"
        )
        cbc_lineextensionamount.set("currencyID", sales_invoice_doc.currency)
        cbc_lineextensionamount.text = str(round(abs(sales_invoice_doc.total), 2))

        cbc_taxexclusiveamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:TaxExclusiveAmount"
        )
        cbc_taxexclusiveamount.set("currencyID", sales_invoice_doc.currency)
        cbc_taxexclusiveamount.text = "0.0"  # str(round(abs(sales_invoice_doc.total)))

        cbc_taxinclusiveamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:TaxInclusiveAmount"
        )
        cbc_taxinclusiveamount.set("currencyID", sales_invoice_doc.currency)
        cbc_taxinclusiveamount.text = str(
            round(abs(tax_amount_without_retention_sar), 2)
        )

        cbc_allowancetotalamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:AllowanceTotalAmount"
        )
        cbc_allowancetotalamount.set("currencyID", sales_invoice_doc.currency)

        cbc_allowancetotalamount.text = str(round(abs(sales_invoice_doc.total), 2))

        cbc_payableamount = ET.SubElement(cac_legalmonetarytotal, "cbc:PayableAmount")
        cbc_payableamount.set("currencyID", sales_invoice_doc.currency)
        cbc_payableamount.text = str(round(abs(tax_amount_without_retention_sar), 2))

        return invoice

    except (ValueError, AttributeError, KeyError) as error:
        frappe.throw(
            f"Error in nominal tax data due to invalid value or missing data: {str(error)}"
        )
        return None

    except ET.ParseError as error:
        frappe.throw(f"XML Parse Error in nominal tax data: {str(error)}")
        return None

    except TypeError as error:
        frappe.throw(f"Type Error in nominal tax data: {str(error)}")
        return None


def tax_data_nominal(invoice, sales_invoice_doc):
    """Define tax data nominal"""
    try:
        # Handle SAR-specific logic
        if sales_invoice_doc.currency == "SAR":
            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount_sar = ET.SubElement(cac_taxtotal, CBC_TAX_AMOUNT)
            cbc_taxamount_sar.set(
                "currencyID", "SAR"
            )  # ZATCA requires tax amount in SAR

            total_line_extension = 0

            for single_item in sales_invoice_doc.items:
                line_extension_amount = abs(
                    round(
                        single_item.amount
                        / (1 + sales_invoice_doc.taxes[0].rate / 100),
                        2,
                    )
                )
                total_line_extension += round(line_extension_amount, 2)
            discount_amount = abs(round(sales_invoice_doc.discount_amount, 2))
            difference = difference = abs(
                round(discount_amount - total_line_extension, 2)
            )

            if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
                tax_amount_without_retention_sar = (
                    sales_invoice_doc.base_total
                    * float(sales_invoice_doc.taxes[0].rate)
                    / 100
                )
            else:
                if difference == 0.01:
                    tax_amount_without_retention_sar = (
                        (total_line_extension)
                        * float(sales_invoice_doc.taxes[0].rate)
                        / 100
                    )

                else:
                    tax_amount_without_retention_sar = (
                        sales_invoice_doc.base_discount_amount
                        * float(sales_invoice_doc.taxes[0].rate)
                        / 100
                    )

            cbc_taxamount_sar.text = str(
                round(tax_amount_without_retention_sar, 2)
            )  # Tax amount in SAR

            if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
                taxable_amount = sales_invoice_doc.base_total
            else:
                if difference == 0.01:
                    taxable_amount = total_line_extension
                else:
                    taxable_amount = sales_invoice_doc.base_discount_amount

            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount = ET.SubElement(cac_taxtotal, CBC_TAX_AMOUNT)
            cbc_taxamount.set("currencyID", sales_invoice_doc.currency)
            cbc_taxamount.text = (
                f"{abs(round(tax_amount_without_retention_sar, 2)):.2f}"
            )

            # Tax Subtotal
            cac_taxsubtotal = ET.SubElement(cac_taxtotal, CAC_TAX_SUBTOTAL)
            cbc_taxableamount = ET.SubElement(cac_taxsubtotal, CBC_TAXABLE_AMOUNT)
            cbc_taxableamount.set("currencyID", sales_invoice_doc.currency)
            if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
                cbc_taxableamount.text = str(
                    abs(round(sales_invoice_doc.base_total, 2))
                )
            else:
                if difference == 0.01:
                    cbc_taxableamount.text = str(total_line_extension)
                else:
                    cbc_taxableamount.text = str(
                        abs(round(sales_invoice_doc.base_discount_amount, 2))
                    )

            cbc_taxamount_2 = ET.SubElement(cac_taxsubtotal, CBC_TAX_AMOUNT)
            cbc_taxamount_2.set("currencyID", sales_invoice_doc.currency)
            cbc_taxamount_2.text = (
                f"{abs(round(tax_amount_without_retention_sar, 2)):.2f}"
            )

        # Handle USD-specific logic
        else:
            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount_usd_1 = ET.SubElement(cac_taxtotal, CBC_TAX_AMOUNT)
            cbc_taxamount_usd_1.set(
                "currencyID", sales_invoice_doc.currency
            )  # USD currency
            if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
                taxable_amount_1 = sales_invoice_doc.total
            else:
                if difference == 0.01:
                    taxable_amount_1 = str(total_line_extension)
                else:
                    taxable_amount_1 = sales_invoice_doc.base_discount_amount
            tax_amount_without_retention = (
                taxable_amount_1 * float(sales_invoice_doc.taxes[0].rate) / 100
            )
            cbc_taxamount_usd_1.text = str(round(tax_amount_without_retention, 2))
            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount_usd = ET.SubElement(cac_taxtotal, CBC_TAX_AMOUNT)
            cbc_taxamount_usd.set(
                "currencyID", sales_invoice_doc.currency
            )  # USD currency

            if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
                taxable_amount_1 = sales_invoice_doc.total
            else:
                if difference == 0.01:
                    taxable_amount_1 = str(total_line_extension)
                else:
                    taxable_amount_1 = sales_invoice_doc.base_discount_amount

            tax_amount_without_retention = (
                taxable_amount_1 * float(sales_invoice_doc.taxes[0].rate) / 100
            )
            cbc_taxamount_usd.text = str(round(tax_amount_without_retention, 2))

            # Tax Subtotal
            cac_taxsubtotal = ET.SubElement(cac_taxtotal, CAC_TAX_SUBTOTAL)
            cbc_taxableamount = ET.SubElement(cac_taxsubtotal, CBC_TAXABLE_AMOUNT)
            cbc_taxableamount.set("currencyID", sales_invoice_doc.currency)
            cbc_taxableamount.text = str(abs(round(taxable_amount_1, 2)))

            cbc_taxamount_2 = ET.SubElement(cac_taxsubtotal, CBC_TAX_AMOUNT)
            cbc_taxamount_2.set("currencyID", sales_invoice_doc.currency)
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
        elif sales_invoice_doc.custom_zatca_tax_category == ZERO_RATED:
            cbc_id_8.text = "Z"
        elif sales_invoice_doc.custom_zatca_tax_category == "Exempted":
            cbc_id_8.text = "E"
        elif sales_invoice_doc.custom_zatca_tax_category == OUTSIDE_SCOPE:
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

        # Adding the second Tax Subtotal (newly added)
        if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
            taxable_amount = sales_invoice_doc.base_total
        else:
            if difference == 0.01:
                taxable_amount = total_line_extension
            else:
                taxable_amount = sales_invoice_doc.base_discount_amount
        cac_taxsubtotal_2 = ET.SubElement(cac_taxtotal, CAC_TAX_SUBTOTAL)
        cbc_taxableamount_2 = ET.SubElement(cac_taxsubtotal_2, CBC_TAXABLE_AMOUNT)
        cbc_taxableamount_2.set("currencyID", "SAR")
        cbc_taxableamount_2.text = str(-round(taxable_amount, 2))

        cbc_taxamount_3 = ET.SubElement(cac_taxsubtotal_2, CBC_TAX_AMOUNT)
        cbc_taxamount_3.set("currencyID", "SAR")
        cbc_taxamount_3.text = "0.0"

        cac_taxcategory_2 = ET.SubElement(cac_taxsubtotal_2, "cac:TaxCategory")
        cbc_id_9 = ET.SubElement(cac_taxcategory_2, "cbc:ID")
        cbc_id_9.text = "O"

        cbc_percent_2 = ET.SubElement(cac_taxcategory_2, "cbc:Percent")
        cbc_percent_2.text = "0.00"

        cbc_taxexemptionreasoncode = ET.SubElement(
            cac_taxcategory_2, "cbc:TaxExemptionReasonCode"
        )
        cbc_taxexemptionreasoncode.text = "VATEX-SA-OOS"

        cbc_taxexemptionreason = ET.SubElement(
            cac_taxcategory_2, "cbc:TaxExemptionReason"
        )
        cbc_taxexemptionreason.text = "Nominal Invoice"

        cac_taxscheme_2 = ET.SubElement(cac_taxcategory_2, "cac:TaxScheme")
        cbc_id_10 = ET.SubElement(cac_taxscheme_2, "cbc:ID")
        cbc_id_10.text = "VAT"

        # Legal Monetary Total (adjust for both SAR and USD)
        cac_legalmonetarytotal = ET.SubElement(invoice, "cac:LegalMonetaryTotal")
        cbc_lineextensionamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:LineExtensionAmount"
        )
        cbc_lineextensionamount.set("currencyID", sales_invoice_doc.currency)
        if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
            cbc_lineextensionamount.text = str(round(abs(sales_invoice_doc.total), 2))
        else:
            if difference == 0.01:
                cbc_lineextensionamount.text = str(total_line_extension)
            else:
                cbc_lineextensionamount.text = str(
                    round(abs(sales_invoice_doc.discount_amount), 2)
                )

        cbc_taxexclusiveamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:TaxExclusiveAmount"
        )
        cbc_taxexclusiveamount.set("currencyID", sales_invoice_doc.currency)

        cbc_taxexclusiveamount.text = "0.0"  # str(round(abs(sales_invoice_doc.total)))

        cbc_taxinclusiveamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:TaxInclusiveAmount"
        )
        cbc_taxinclusiveamount.set("currencyID", sales_invoice_doc.currency)
        cbc_taxinclusiveamount.text = str(
            round(abs(tax_amount_without_retention_sar), 2)
        )

        cbc_allowancetotalamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:AllowanceTotalAmount"
        )
        cbc_allowancetotalamount.set("currencyID", sales_invoice_doc.currency)
        if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
            cbc_allowancetotalamount.text = str(round(abs(sales_invoice_doc.total), 2))
        else:

            if difference == 0.01:
                cbc_allowancetotalamount.text = str(total_line_extension)
            else:
                cbc_allowancetotalamount.text = str(
                    round(abs(sales_invoice_doc.discount_amount), 2)
                )

        cbc_payableamount = ET.SubElement(cac_legalmonetarytotal, "cbc:PayableAmount")
        cbc_payableamount.set("currencyID", sales_invoice_doc.currency)
        cbc_payableamount.text = str(round(abs(tax_amount_without_retention_sar), 2))

        return invoice

    except (ValueError, AttributeError, KeyError) as error:
        frappe.throw(
            f"Error in nominal tax data due to invalid value or missing data: {str(error)}"
        )
        return None

    except ET.ParseError as error:
        frappe.throw(f"XML Parse Error in nominal tax data: {str(error)}")
        return None

    except TypeError as error:
        frappe.throw(f"Type Error in nominal tax data: {str(error)}")
        return None


def add_line_item_discount(cac_price, single_item, sales_invoice_doc):
    """
    Adds a line item discount and related details to the XML structure.
    """
    try:
        cac_allowance_charge = ET.SubElement(cac_price, "cac:AllowanceCharge")

        cbc_charge_indicator = ET.SubElement(
            cac_allowance_charge, "cbc:ChargeIndicator"
        )
        cbc_charge_indicator.text = "false"  # Indicates a discount

        cbc_allowance_charge_reason_code = ET.SubElement(
            cac_allowance_charge, "cbc:AllowanceChargeReasonCode"
        )
        cbc_allowance_charge_reason_code.text = str(
            sales_invoice_doc.custom_zatca_discount_reason_code
        )

        cbc_allowance_charge_reason = ET.SubElement(
            cac_allowance_charge, "cbc:AllowanceChargeReason"
        )
        cbc_allowance_charge_reason.text = str(
            sales_invoice_doc.custom_zatca_discount_reason
        )

        cbc_amount = ET.SubElement(
            cac_allowance_charge, "cbc:Amount", currencyID=sales_invoice_doc.currency
        )
        cbc_amount.text = str(abs(single_item.discount_amount))

        cbc_base_amount = ET.SubElement(
            cac_allowance_charge,
            "cbc:BaseAmount",
            currencyID=sales_invoice_doc.currency,
        )
        cbc_base_amount.text = str(
            abs(single_item.rate) + abs(single_item.discount_amount)
        )

        return cac_price

    except (ValueError, KeyError, AttributeError) as error:
        frappe.throw(f"Error occurred while adding line item discount: {str(error)}")
        return None


def item_data(invoice, sales_invoice_doc):
    """
    The function defines the xml creating without item tax template
    """
    try:
        qty = "cbc:BaseQuantity"
        for single_item in sales_invoice_doc.items:
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
            cbc_lineextensionamount_1.set("currencyID", sales_invoice_doc.currency)

            if sales_invoice_doc.currency == "SAR":
                if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
                    # Tax is not included in print rate
                    cbc_lineextensionamount_1.text = str(abs(single_item.base_amount))
                elif sales_invoice_doc.taxes[0].included_in_print_rate == 1:
                    # Tax is included in print rate
                    cbc_lineextensionamount_1.text = str(
                        abs(
                            round(
                                single_item.base_amount
                                / (1 + sales_invoice_doc.taxes[0].rate / 100),
                                2,
                            )
                        )
                    )
            else:
                # For other currencies
                if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
                    cbc_lineextensionamount_1.text = str(abs(single_item.amount))
                else:

                    cbc_lineextensionamount_1.text = str(
                        abs(
                            round(
                                single_item.amount
                                / (1 + sales_invoice_doc.taxes[0].rate / 100),
                                2,
                            )
                        )
                    )

            cac_taxtotal_2 = ET.SubElement(cac_invoiceline, CAC_TAX_TOTAL)
            cbc_taxamount_3 = ET.SubElement(cac_taxtotal_2, CBC_TAX_AMOUNT)
            cbc_taxamount_3.set("currencyID", sales_invoice_doc.currency)
            if sales_invoice_doc.taxes[0].included_in_print_rate == 1:
                cbc_taxamount_3.text = str(
                    abs(
                        round(
                            single_item.base_amount
                            * sales_invoice_doc.taxes[0].rate
                            / (100 + sales_invoice_doc.taxes[0].rate),
                            2,
                        )
                    )
                )

            else:
                # cbc_taxamount_3.text = str(
                #     abs(custom_round(item_tax_percentage * single_item.amount / 100))
                # )

                cbc_taxamount_3.text = str(
                    Decimal(
                        str(abs(item_tax_percentage * single_item.amount / 100))
                    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                )
            cbc_roundingamount = ET.SubElement(cac_taxtotal_2, "cbc:RoundingAmount")
            cbc_roundingamount.set("currencyID", sales_invoice_doc.currency)
            lineextensionamount = float(cbc_lineextensionamount_1.text)
            taxamount = float(cbc_taxamount_3.text)
            # frappe.throw(f"Tax Amount1: {taxamount}")
            cbc_roundingamount.text = str(round(lineextensionamount + taxamount, 2))
            cac_item = ET.SubElement(cac_invoiceline, "cac:Item")
            cbc_name = ET.SubElement(cac_item, "cbc:Name")
            cbc_name.text = single_item.item_code
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
            cbc_priceamount.set("currencyID", sales_invoice_doc.currency)
            if sales_invoice_doc.custom_zatca_nominal_invoice == 1:
                # Case 1: Nominal Invoice, Tax Not Included in Print Rate
                if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
                    cbc_priceamount.text = str(abs(single_item.rate))
                # Case 2: Nominal Invoice, Tax Included in Print Rate
                elif sales_invoice_doc.taxes[0].included_in_print_rate == 1:
                    cbc_priceamount.text = str(
                        abs(
                            round(
                                single_item.rate
                                / (1 + sales_invoice_doc.taxes[0].rate / 100),
                                2,
                            )
                        )
                    )
            else:
                # Handle other cases based on ZATCA line item discount submission
                if sales_invoice_doc.custom_submit_line_item_discount_to_zatca != 1:
                    # Case 3: No Discount Submission to ZATCA, Tax Not Included in Print Rate
                    if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
                        cbc_priceamount.text = str(abs(single_item.rate))
                    # Case 4: No Discount Submission to ZATCA, Tax Included in Print Rate
                    elif sales_invoice_doc.taxes[0].included_in_print_rate == 1:
                        cbc_priceamount.text = str(
                            abs(
                                round(
                                    single_item.rate
                                    / (1 + sales_invoice_doc.taxes[0].rate / 100),
                                    2,
                                )
                            )
                        )
                else:
                    # Case 5: Discount Submission to ZATCA, Tax Not Included in Print Rate
                    if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
                        cbc_priceamount.text = str(abs(single_item.rate))
                        cbc_basequantity = ET.SubElement(
                            cac_price, qty, unitCode=str(single_item.uom)
                        )
                        cbc_basequantity.text = "1"
                        add_line_item_discount(
                            cac_price, single_item, sales_invoice_doc
                        )
                    # Case 6: Discount Submission to ZATCA, Tax Included in Print Rate
                    elif sales_invoice_doc.taxes[0].included_in_print_rate == 1:
                        cbc_priceamount.text = str(
                            abs(
                                round(
                                    single_item.rate
                                    / (1 + sales_invoice_doc.taxes[0].rate / 100),
                                    2,
                                )
                            )
                        )
                        cbc_basequantity = ET.SubElement(
                            cac_price, qty, unitCode=str(single_item.uom)
                        )
                        cbc_basequantity.text = "1"
                        add_line_item_discount(
                            cac_price, single_item, sales_invoice_doc
                        )

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


def item_data_with_template(invoice, sales_invoice_doc):
    """The defining of xml item data according to the item tax template datas and feilds"""
    try:
        qty = "cbc:BaseQuantity"
        for single_item in sales_invoice_doc.items:
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
            cbc_lineextensionamount_1.set("currencyID", sales_invoice_doc.currency)
            cbc_lineextensionamount_1.text = str(abs(single_item.amount))

            cac_taxtotal_2 = ET.SubElement(cac_invoiceline, CAC_TAX_TOTAL)
            cbc_taxamount_3 = ET.SubElement(cac_taxtotal_2, CBC_TAX_AMOUNT)
            cbc_taxamount_3.set("currencyID", sales_invoice_doc.currency)
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
            cbc_roundingamount.set("currencyID", sales_invoice_doc.currency)
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
            cbc_name.text = single_item.item_code

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
            cbc_priceamount.set("currencyID", sales_invoice_doc.currency)

            if sales_invoice_doc.custom_zatca_nominal_invoice == 1:
                # If nominal invoice, only set cbc_PriceAmount
                cbc_priceamount.text = f"{abs(single_item.rate):.6f}"
            else:
                # Check for line item discount submission to ZATCA
                if sales_invoice_doc.custom_submit_line_item_discount_to_zatca != 1:
                    # No discount submission to ZATCA
                    cbc_priceamount.text = f"{abs(single_item.rate):.6f}"
                elif sales_invoice_doc.custom_submit_line_item_discount_to_zatca == 1:
                    # Discount submission to ZATCA
                    cbc_priceamount.text = f"{abs(single_item.rate):.6f}"
                    cbc_basequantity = ET.SubElement(
                        cac_price, qty, unitCode=str(single_item.uom)
                    )
                    cbc_basequantity.text = "1"
                    add_line_item_discount(cac_price, single_item, sales_invoice_doc)

        return invoice
    except (ValueError, KeyError, TypeError) as e:
        frappe.throw(f"Error occurred in item template data processing: {str(e)}")
        return None


def xml_structuring(invoice):
    """
    Xml structuring and final saving of the xml into private files
    """
    try:

        tree = ET.ElementTree(invoice)
        xml_file_path = frappe.local.site + "/private/files/xml_files.xml"

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
        final_xml_path = frappe.local.site + "/private/files/finalzatcaxml.xml"
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
