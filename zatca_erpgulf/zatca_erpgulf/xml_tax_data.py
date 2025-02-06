"""
This module contains utilities for ZATCA 2024 e-invoicing.
Includes functions for XML parsing, API interactions, and custom handling.
"""

import json
import xml.etree.ElementTree as ET
import frappe
from decimal import Decimal, ROUND_HALF_UP

TAX_CALCULATION_ERROR = "Tax Calculation Error"
CAC_TAX_TOTAL = "cac:TaxTotal"


def get_exemption_reason_map():
    """Mapping of the exception reason code accoding to the reason code"""
    return {
        "VATEX-SA-29": (
            "Financial services mentioned in Article 29 of the VAT Regulations."
        ),
        "VATEX-SA-29-7": (
            "Life insurance services mentioned in Article 29 of the VAT Regulations."
        ),
        "VATEX-SA-30": (
            "Real estate transactions mentioned in Article 30 of the VAT Regulations."
        ),
        "VATEX-SA-32": "Export of goods.",
        "VATEX-SA-33": "Export of services.",
        "VATEX-SA-34-1": "The international transport of Goods.",
        "VATEX-SA-34-2": "International transport of passengers.",
        "VATEX-SA-34-3": (
            "Services directly connected and incidental to a Supply of "
            "international passenger transport."
        ),
        "VATEX-SA-34-4": "Supply of a qualifying means of transport.",
        "VATEX-SA-34-5": (
            "Any services relating to Goods or passenger transportation, as defined "
            "in article twenty five of these Regulations."
        ),
        "VATEX-SA-35": "Medicines and medical equipment.",
        "VATEX-SA-36": "Qualifying metals.",
        "VATEX-SA-EDU": "Private education to citizen.",
        "VATEX-SA-HEA": "Private healthcare to citizen.",
        "VATEX-SA-MLTRY": "Supply of qualified military goods",
        "VATEX-SA-OOS": (
            "The reason is a free text, has to be provided by the taxpayer on a "
            "case-by-case basis."
        ),
    }


def get_tax_for_item(full_string, item):
    """
    Extracts the tax amount and tax percentage for a specific item from a JSON-encoded string.
    """
    try:  # getting tax percentage and tax amount
        data = json.loads(full_string)
        tax_percentage = data.get(item, [0, 0])[0]
        tax_amount = data.get(item, [0, 0])[1]
        return tax_amount, tax_percentage
    except json.JSONDecodeError as e:
        frappe.throw("JSON decoding error occurred in tax for item: " + str(e))
        return None
    except KeyError as e:
        frappe.throw(f"Key error occurred while accessing item '{item}': " + str(e))
        return None
    except TypeError as e:
        frappe.throw("Type error occurred in tax for item: " + str(e))
        return None


def get_tax_total_from_items(sales_invoice_doc):
    """Getting tax total for items"""
    try:
        total_tax = 0
        for single_item in sales_invoice_doc.items:
            _item_tax_amount, tax_percent = get_tax_for_item(
                sales_invoice_doc.taxes[0].item_wise_tax_detail, single_item.item_code
            )
            total_tax = total_tax + (single_item.net_amount * (tax_percent / 100))
        return total_tax
    except AttributeError as e:
        frappe.throw(
            f"AttributeError in get_tax_total_from_items: {str(e)}",
            TAX_CALCULATION_ERROR,
        )
        return None
    except KeyError as e:
        frappe.throw(
            f"KeyError in get_tax_total_from_items: {str(e)}", TAX_CALCULATION_ERROR
        )

        return None
    except TypeError as e:
        frappe.throw(
            f"KeyError in get_tax_total_from_items: {str(e)}", TAX_CALCULATION_ERROR
        )

        return None


def tax_data(invoice, sales_invoice_doc):
    """extract tax data without template"""
    try:

        # Handle SAR-specific logic
        if sales_invoice_doc.currency == "SAR":
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
            cbc_taxamount.set("currencyID", sales_invoice_doc.currency)
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
            cbc_taxableamount.set("currencyID", sales_invoice_doc.currency)

            if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
                taxable_amount = sales_invoice_doc.base_total - sales_invoice_doc.get(
                    "base_discount_amount", 0.0
                )

            else:
                taxable_amount = (
                    sales_invoice_doc.base_net_total
                    - sales_invoice_doc.get("base_discount_amount", 0.0)
                )

            cbc_taxableamount.text = str(abs(round(taxable_amount, 2)))
            cbc_taxamount_2 = ET.SubElement(cac_taxsubtotal, "cbc:TaxAmount")
            cbc_taxamount_2.set("currencyID", sales_invoice_doc.currency)
            cbc_taxamount_2.text = f"{abs(round(tax_amount_without_retention, 2)):.2f}"

        # Handle USD-specific logic
        else:
            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount_usd_1 = ET.SubElement(cac_taxtotal, "cbc:TaxAmount")
            cbc_taxamount_usd_1.set(
                "currencyID", sales_invoice_doc.currency
            )  # USD currency
            if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
                taxable_amount_1 = sales_invoice_doc.total - sales_invoice_doc.get(
                    "discount_amount", 0.0
                )
            else:
                taxable_amount_1 = (
                    sales_invoice_doc.base_net_total
                    - sales_invoice_doc.get("discount_amount", 0.0)
                )
            tax_amount_without_retention = (
                taxable_amount_1 * float(sales_invoice_doc.taxes[0].rate) / 100
            )
            cbc_taxamount_usd_1.text = str(round(tax_amount_without_retention, 2))
            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount_usd = ET.SubElement(cac_taxtotal, "cbc:TaxAmount")
            cbc_taxamount_usd.set(
                "currencyID", sales_invoice_doc.currency
            )  # USD currency
            if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
                taxable_amount_1 = sales_invoice_doc.total - sales_invoice_doc.get(
                    "discount_amount", 0.0
                )

            else:
                taxable_amount_1 = (
                    sales_invoice_doc.base_net_total
                    - sales_invoice_doc.get("discount_amount", 0.0)
                )
            tax_amount_without_retention = (
                taxable_amount_1 * float(sales_invoice_doc.taxes[0].rate) / 100
            )
            cbc_taxamount_usd.text = str(round(tax_amount_without_retention, 2))

            # Tax Subtotal
            cac_taxsubtotal = ET.SubElement(cac_taxtotal, "cac:TaxSubtotal")
            cbc_taxableamount = ET.SubElement(cac_taxsubtotal, "cbc:TaxableAmount")
            cbc_taxableamount.set("currencyID", sales_invoice_doc.currency)
            cbc_taxableamount.text = str(abs(round(taxable_amount_1, 2)))

            cbc_taxamount_2 = ET.SubElement(cac_taxsubtotal, "cbc:TaxAmount")
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
        cbc_lineextensionamount.set("currencyID", sales_invoice_doc.currency)
        if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
            cbc_lineextensionamount.text = str(round(abs(sales_invoice_doc.total), 2))
        else:

            cbc_lineextensionamount.text = str(
                round(abs(sales_invoice_doc.base_net_total), 2)
            )
        cbc_taxexclusiveamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:TaxExclusiveAmount"
        )
        cbc_taxexclusiveamount.set("currencyID", sales_invoice_doc.currency)
        if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
            cbc_taxexclusiveamount.text = str(
                round(
                    abs(
                        sales_invoice_doc.total
                        - sales_invoice_doc.get("discount_amount", 0.0)
                    ),
                    2,
                )
            )
        else:
            cbc_taxexclusiveamount.text = str(
                round(
                    abs(
                        sales_invoice_doc.base_net_total
                        - sales_invoice_doc.get("discount_amount", 0.0)
                    ),
                    2,
                )
            )
        cbc_taxinclusiveamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:TaxInclusiveAmount"
        )
        cbc_taxinclusiveamount.set("currencyID", sales_invoice_doc.currency)
        if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
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
        else:
            cbc_taxinclusiveamount.text = str(
                round(
                    abs(
                        sales_invoice_doc.base_net_total
                        - sales_invoice_doc.get("discount_amount", 0.0)
                    )
                    + abs(tax_amount_without_retention),
                    2,
                )
            )
        cbc_allowancetotalamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:AllowanceTotalAmount"
        )
        cbc_allowancetotalamount.set("currencyID", sales_invoice_doc.currency)
        cbc_allowancetotalamount.text = str(
            abs(sales_invoice_doc.get("discount_amount", 0.0))
        )

        cbc_payableamount = ET.SubElement(cac_legalmonetarytotal, "cbc:PayableAmount")
        cbc_payableamount.set("currencyID", sales_invoice_doc.currency)
        if sales_invoice_doc.taxes[0].included_in_print_rate == 0:
            cbc_payableamount.text = str(
                round(
                    abs(
                        sales_invoice_doc.total
                        - sales_invoice_doc.get("discount_amount", 0.0)
                    )
                    + abs(tax_amount_without_retention),
                    2,
                )
            )
        else:
            cbc_payableamount.text = str(
                round(
                    abs(
                        sales_invoice_doc.base_net_total
                        - sales_invoice_doc.get("discount_amount", 0.0)
                    )
                    + abs(tax_amount_without_retention),
                    2,
                )
            )
        return invoice

    except (AttributeError, KeyError, ValueError, TypeError) as e:
        frappe.throw(f"Data processing error in tax data: {str(e)}")
        return None


def tax_data_with_template(invoice, sales_invoice_doc):
    """Adding tax data with template to the xml"""
    try:
        # Initialize tax category totals
        tax_category_totals = {}
        for item in sales_invoice_doc.items:
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
            if sales_invoice_doc.currency == "SAR":
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
        if sales_invoice_doc.currency == "SAR":
            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount_sar = ET.SubElement(cac_taxtotal, "cbc:TaxAmount")
            cbc_taxamount_sar.set(
                "currencyID", "SAR"
            )  # SAR is as ZATCA requires tax amount in SAR
            tax_amount_without_retention_sar = round(abs(total_tax), 2)
            cbc_taxamount_sar.text = str(tax_amount_without_retention_sar)

            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount = ET.SubElement(cac_taxtotal, "cbc:TaxAmount")
            cbc_taxamount.set("currencyID", sales_invoice_doc.currency)
            # tax_amount_without_retention = round(abs(total_tax), 2)
            tax_amount_without_retention = total_tax.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            cbc_taxamount.text = str(tax_amount_without_retention)
        else:
            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount_sar = ET.SubElement(cac_taxtotal, "cbc:TaxAmount")
            cbc_taxamount_sar.set("currencyID", sales_invoice_doc.currency)
            tax_amount_without_retention_sar = round(abs(total_tax), 2)
            cbc_taxamount_sar.text = str(tax_amount_without_retention_sar)

            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount = ET.SubElement(cac_taxtotal, "cbc:TaxAmount")
            cbc_taxamount.set("currencyID", sales_invoice_doc.currency)
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
        for item in sales_invoice_doc.items:
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
                        if sales_invoice_doc.currency == "SAR"
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
            cbc_taxableamount.set("currencyID", sales_invoice_doc.currency)
            cbc_taxableamount.text = str(round(totals["taxable_amount"], 2))

            cbc_taxamount_2 = ET.SubElement(cac_taxsubtotal, "cbc:TaxAmount")
            cbc_taxamount_2.set("currencyID", sales_invoice_doc.currency)
            cbc_taxamount_2.text = str(round(totals["tax_amount"], 2))

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
        cbc_lineextensionamount.set("currencyID", sales_invoice_doc.currency)
        cbc_lineextensionamount.text = str(round(abs(sales_invoice_doc.total), 2))

        # Tax-Exclusive Amount (base_total - base_discount_amount)
        cbc_taxexclusiveamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:TaxExclusiveAmount"
        )
        cbc_taxexclusiveamount.set("currencyID", sales_invoice_doc.currency)
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
        cbc_taxinclusiveamount.set("currencyID", sales_invoice_doc.currency)
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
        cbc_allowancetotalamount.set("currencyID", sales_invoice_doc.currency)

        cbc_allowancetotalamount.text = str(
            round(abs(sales_invoice_doc.get("discount_amount", 0.0)), 2)
        )

        cbc_payableamount = ET.SubElement(cac_legalmonetarytotal, "cbc:PayableAmount")
        cbc_payableamount.set("currencyID", sales_invoice_doc.currency)
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
