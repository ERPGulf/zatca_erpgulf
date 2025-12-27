"""
This module contains functions to generate, structure, and
manage ZATCA-compliant UBL XML invoices . functions to handle company,
customer, tax, line items, discounts, delivery, and payment information.
The XML is generated according to ZATCA (Zakat, Tax, and Customs Authority)
requirements for VAT compliance in Saudi Arabia.
The primary goal of this module is to produce a UBL-compliant
 XML file for invoices, debit notes, and credit notes.
The file also handles compliance with e-invoicing and clearance rules
for ZATCA and provides support for multiple currencies (SAR and USD).
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from frappe import _
import frappe
from zatca_erpgulf.zatca_erpgulf.posxml import (
    get_exemption_reason_map,
    get_tax_for_item,
    add_line_item_discount,
)


ITEM_TAX_TEMPLATE = "Item Tax Template"
CAC_TAX_TOTAL = "cac:TaxTotal"
CBC_TAX_AMOUNT = "cbc:TaxAmount"


def tax_data_with_template(invoice, pos_invoice_doc):
    """ "function for tax data with template"""
    try:
        # Initialize tax category totals
        tax_category_totals = {}
        for item in pos_invoice_doc.items:
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
            if pos_invoice_doc.currency == "SAR":
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
        base_discount_amount = pos_invoice_doc.get("discount_amount", 0.0)

        # Subtract the base discount from the taxable amount of the first tax category
        tax_category_totals[first_tax_category][
            "taxable_amount"
        ] -= base_discount_amount

        for zatca_tax_category, totals in tax_category_totals.items():
            totals["tax_amount"] = abs(
                round(totals["taxable_amount"] * totals["tax_rate"] / 100, 2)
            )

        total_tax = sum(
            category_totals["tax_amount"]
            for category_totals in tax_category_totals.values()
        )
        # For foreign currency

        # For SAR currency
        if pos_invoice_doc.currency == "SAR":
            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount_sar = ET.SubElement(cac_taxtotal, CBC_TAX_AMOUNT)
            cbc_taxamount_sar.set(
                "currencyID", "SAR"
            )  # SAR is as ZATCA requires tax amount in SAR
            tax_amount_without_retention_sar = round(abs(total_tax), 2)
            cbc_taxamount_sar.text = str(round(tax_amount_without_retention_sar, 2))

            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount = ET.SubElement(cac_taxtotal, CBC_TAX_AMOUNT)
            cbc_taxamount.set("currencyID", pos_invoice_doc.currency)
            tax_amount_without_retention = round(abs(total_tax), 2)
            cbc_taxamount.text = str(round(tax_amount_without_retention, 2))
        else:
            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount_sar = ET.SubElement(cac_taxtotal, CBC_TAX_AMOUNT)
            cbc_taxamount_sar.set(
                "currencyID", pos_invoice_doc.currency
            )  # SAR is as ZATCA requires tax amount in SAR
            tax_amount_without_retention_sar = round(abs(total_tax), 2)
            cbc_taxamount_sar.text = str(round(tax_amount_without_retention_sar, 2))

            cac_taxtotal = ET.SubElement(invoice, CAC_TAX_TOTAL)
            cbc_taxamount = ET.SubElement(cac_taxtotal, CBC_TAX_AMOUNT)
            cbc_taxamount.set("currencyID", pos_invoice_doc.currency)
            tax_amount_without_retention = round(abs(total_tax), 2)
            cbc_taxamount.text = str(round(tax_amount_without_retention, 2))

        tax_category_totals = {}
        for item in pos_invoice_doc.items:
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
            if pos_invoice_doc.currency == "SAR":
                tax_category_totals[zatca_tax_category]["taxable_amount"] += abs(
                    item.base_amount
                )
            else:
                tax_category_totals[zatca_tax_category]["taxable_amount"] += abs(
                    item.amount
                )

        first_tax_category = next(iter(tax_category_totals))
        tax_category_totals[first_tax_category][
            "taxable_amount"
        ] -= pos_invoice_doc.get("discount_amount", 0.0)

        for item in pos_invoice_doc.items:
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

        for zatca_tax_category, totals in tax_category_totals.items():
            tax_category_totals[zatca_tax_category]["tax_amount"] += abs(
                round(
                    tax_category_totals[zatca_tax_category]["taxable_amount"]
                    * tax_category_totals[zatca_tax_category]["tax_rate"]
                    / 100,
                    2,
                )
            )
        # Create XML elements for each ZATCA tax category
        for zatca_tax_category, totals in tax_category_totals.items():
            cac_taxsubtotal = ET.SubElement(cac_taxtotal, "cac:TaxSubtotal")
            cbc_taxableamount = ET.SubElement(cac_taxsubtotal, "cbc:TaxableAmount")
            cbc_taxableamount.set("currencyID", pos_invoice_doc.currency)
            cbc_taxableamount.text = str(totals["taxable_amount"])

            cbc_taxamount_2 = ET.SubElement(cac_taxsubtotal, CBC_TAX_AMOUNT)
            cbc_taxamount_2.set("currencyID", pos_invoice_doc.currency)
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
        cbc_lineextensionamount.set("currencyID", pos_invoice_doc.currency)
        cbc_lineextensionamount.text = str(abs(pos_invoice_doc.total))

        # Tax-Exclusive Amount (base_total - base_discount_amount)
        cbc_taxexclusiveamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:TaxExclusiveAmount"
        )
        cbc_taxexclusiveamount.set("currencyID", pos_invoice_doc.currency)
        cbc_taxexclusiveamount.text = str(
            round(
                abs(
                    pos_invoice_doc.total - pos_invoice_doc.get("discount_amount", 0.0)
                ),
                2,
            )
        )
        # Tax-Inclusive Amount (Tax-Exclusive Amount + tax_amount_without_retention)
        cbc_taxinclusiveamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:TaxInclusiveAmount"
        )
        cbc_taxinclusiveamount.set("currencyID", pos_invoice_doc.currency)
        cbc_taxinclusiveamount.text = str(
            round(
                abs(pos_invoice_doc.total - pos_invoice_doc.get("discount_amount", 0.0))
                + abs(tax_amount_without_retention),
                2,
            )
        )
        cbc_allowancetotalamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:AllowanceTotalAmount"
        )
        cbc_allowancetotalamount.set("currencyID", pos_invoice_doc.currency)
        cbc_allowancetotalamount.text = str(
            round(abs(pos_invoice_doc.get("discount_amount", 0.0)), 2)
        )

        cbc_payableamount = ET.SubElement(cac_legalmonetarytotal, "cbc:PayableAmount")
        cbc_payableamount.set("currencyID", pos_invoice_doc.currency)
        cbc_payableamount.text = str(
            round(
                abs(pos_invoice_doc.total - pos_invoice_doc.get("discount_amount", 0.0))
                + abs(tax_amount_without_retention),
                2,
            )
        )
        return invoice

    except (AttributeError, KeyError, ValueError, TypeError) as e:
        frappe.throw(_(f"Data processing error in tax data with template: {str(e)}"))


def item_data(invoice, pos_invoice_doc):
    """Function for item data"""
    try:
        for single_item in pos_invoice_doc.items:
            _item_tax_amount, item_tax_percentage = get_tax_for_item(
                pos_invoice_doc.taxes[0].item_wise_tax_detail, single_item.item_code
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
            cbc_lineextensionamount_1.set("currencyID", pos_invoice_doc.currency)
            pos_profile = pos_invoice_doc.pos_profile
            if not pos_profile:
                frappe.throw("POS Profile is not set in the POS Invoice.")
            pos_profile_doc = frappe.get_doc("POS Profile", pos_profile)
            taxes_and_charges = pos_profile_doc.taxes_and_charges
            taxes_template_doc = frappe.get_doc(
                "Sales Taxes and Charges Template", taxes_and_charges
            )
            tax_rate = taxes_template_doc.taxes[0]
            if pos_invoice_doc.currency == "SAR":
                if tax_rate.included_in_print_rate == 0:
                    cbc_lineextensionamount_1.text = str(abs(single_item.base_amount))
                elif tax_rate.included_in_print_rate == 1:
                    cbc_lineextensionamount_1.text = str(
                        abs(
                            round(
                                single_item.base_amount
                                / (1 + pos_invoice_doc.taxes[0].rate / 100),
                                2,
                            )
                        )
                    )

            else:
                if tax_rate.included_in_print_rate == 0:
                    cbc_lineextensionamount_1.text = str(abs(single_item.amount))
                elif tax_rate.included_in_print_rate == 1:
                    cbc_lineextensionamount_1.text = str(
                        abs(
                            round(
                                single_item.amount
                                / (1 + pos_invoice_doc.taxes[0].rate / 100),
                                2,
                            )
                        )
                    )
            cac_taxtotal_2 = ET.SubElement(cac_invoiceline, CAC_TAX_TOTAL)
            cbc_taxamount_3 = ET.SubElement(cac_taxtotal_2, CBC_TAX_AMOUNT)
            cbc_taxamount_3.set("currencyID", pos_invoice_doc.currency)
            cbc_taxamount_3.text = str(
                abs(round(item_tax_percentage * single_item.net_amount / 100, 2))
            )
            cbc_roundingamount = ET.SubElement(cac_taxtotal_2, "cbc:RoundingAmount")
            cbc_roundingamount.set("currencyID", pos_invoice_doc.currency)
            lineextensionamount = float(cbc_lineextensionamount_1.text)
            taxamount = float(cbc_taxamount_3.text)
            cbc_roundingamount.text = str(round(lineextensionamount + taxamount, 2))
            cac_item = ET.SubElement(cac_invoiceline, "cac:Item")
            cbc_name = ET.SubElement(cac_item, "cbc:Name")
            cbc_name.text = f"{single_item.item_code}:{single_item.item_name}"
            cac_classifiedtaxcategory = ET.SubElement(
                cac_item, "cac:ClassifiedTaxCategory"
            )
            cbc_id_11 = ET.SubElement(cac_classifiedtaxcategory, "cbc:ID")
            if pos_invoice_doc.custom_zatca_tax_category == "Standard":
                cbc_id_11.text = "S"
            elif pos_invoice_doc.custom_zatca_tax_category == "Zero Rated":
                cbc_id_11.text = "Z"
            elif pos_invoice_doc.custom_zatca_tax_category == "Exempted":
                cbc_id_11.text = "E"
            elif (
                pos_invoice_doc.custom_zatca_tax_category
                == "Services outside scope of tax / Not subject to VAT"
            ):
                cbc_id_11.text = "O"
            cbc_percent_2 = ET.SubElement(cac_classifiedtaxcategory, "cbc:Percent")
            cbc_percent_2.text = f"{float(item_tax_percentage):.2f}"
            cac_taxscheme_4 = ET.SubElement(cac_classifiedtaxcategory, "cac:TaxScheme")
            cbc_id_12 = ET.SubElement(cac_taxscheme_4, "cbc:ID")
            cbc_id_12.text = "VAT"
            cac_price = ET.SubElement(cac_invoiceline, "cac:Price")
            cbc_priceamount = ET.SubElement(cac_price, "cbc:PriceAmount")
            cbc_priceamount.set("currencyID", pos_invoice_doc.currency)
            company_name = pos_invoice_doc.company
            settings = frappe.get_doc("Company", company_name)
            if settings.custom_submit_line_item_discount_to_zatca != 1:
                if tax_rate.included_in_print_rate == 0:
                    cbc_priceamount.text = str(
                        abs(single_item.price_list_rate)
                        - abs(single_item.discount_amount)
                    )
                elif tax_rate.included_in_print_rate == 1:
                    cbc_priceamount.text = str(
                        abs(
                            round(
                                single_item.rate
                                / (1 + pos_invoice_doc.taxes[0].rate / 100),
                                2,
                            )
                        )
                    )
            if settings.custom_submit_line_item_discount_to_zatca == 1:
                if tax_rate.included_in_print_rate == 0:
                    cbc_priceamount.text = str(
                        abs(single_item.price_list_rate)
                        - abs(single_item.discount_amount)
                    )
                    cbc_basequantity = ET.SubElement(
                        cac_price, "cbc:BaseQuantity", unitCode=str(single_item.uom)
                    )
                    cbc_basequantity.text = "1"

                    add_line_item_discount(cac_price, single_item, pos_invoice_doc)
                elif tax_rate.included_in_print_rate == 1:
                    cbc_priceamount.text = str(
                        abs(
                            round(
                                single_item.rate
                                / (1 + pos_invoice_doc.taxes[0].rate / 100),
                                2,
                            )
                        )
                    )
                    cbc_basequantity = ET.SubElement(
                        cac_price, "cbc:BaseQuantity", unitCode=str(single_item.uom)
                    )
                    cbc_basequantity.text = "1"

                    add_line_item_discount(cac_price, single_item, pos_invoice_doc)

        return invoice
    except (AttributeError, KeyError, ValueError, TypeError) as e:
        frappe.throw(_(f"Data processing error in item data: {str(e)}"))


def item_data_with_template(invoice, pos_invoice_doc):
    """function for item data with template"""
    try:
        for single_item in pos_invoice_doc.items:
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
            cbc_lineextensionamount_1.set("currencyID", pos_invoice_doc.currency)
            cbc_lineextensionamount_1.text = str(abs(single_item.amount))

            cac_taxtotal_2 = ET.SubElement(cac_invoiceline, CAC_TAX_TOTAL)
            cbc_taxamount_3 = ET.SubElement(cac_taxtotal_2, CBC_TAX_AMOUNT)
            cbc_taxamount_3.set("currencyID", pos_invoice_doc.currency)
            cbc_taxamount_3.text = str(
                abs(round(item_tax_percentage * single_item.amount / 100, 2))
            )
            cbc_roundingamount = ET.SubElement(cac_taxtotal_2, "cbc:RoundingAmount")
            cbc_roundingamount.set("currencyID", pos_invoice_doc.currency)
            cbc_roundingamount.text = str(
                abs(
                    round(
                        single_item.amount
                        + (item_tax_percentage * single_item.amount / 100),
                        2,
                    )
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
            elif zatca_tax_category == "Zero Rated":
                cbc_id_11.text = "Z"
            elif zatca_tax_category == "Exempted":
                cbc_id_11.text = "E"
            elif (
                zatca_tax_category
                == "Services outside scope of tax / Not subject to VAT"
            ):
                cbc_id_11.text = "O"

            cbc_percent_2 = ET.SubElement(cac_classifiedtaxcategory, "cbc:Percent")
            cbc_percent_2.text = f"{float(item_tax_percentage):.2f}"
            cac_taxscheme_4 = ET.SubElement(cac_classifiedtaxcategory, "cac:TaxScheme")
            cbc_id_12 = ET.SubElement(cac_taxscheme_4, "cbc:ID")
            cbc_id_12.text = "VAT"
            cac_price = ET.SubElement(cac_invoiceline, "cac:Price")
            cbc_priceamount = ET.SubElement(cac_price, "cbc:PriceAmount")
            cbc_priceamount.set("currencyID", pos_invoice_doc.currency)
            company_name = pos_invoice_doc.company
            settings = frappe.get_doc("Company", company_name)
            if settings.custom_submit_line_item_discount_to_zatca != 1:
                cbc_priceamount.text = f"{abs(single_item.rate):.6f}"
            if settings.custom_submit_line_item_discount_to_zatca == 1:
                cbc_priceamount.text = f"{abs(single_item.rate):.6f}"
                cbc_basequantity = ET.SubElement(
                    cac_price, "cbc:BaseQuantity", unitCode=str(single_item.uom)
                )
                cbc_basequantity.text = "1"

                add_line_item_discount(cac_price, single_item, pos_invoice_doc)

        return invoice
    except (AttributeError, KeyError, ValueError, TypeError) as e:
        frappe.throw(
            _(f"Data processing error in item tax with template data: {str(e)}")
        )


def xml_structuring(invoice,invoice_number):
    """function for xml structuring"""
    try:

        xml_file_path = f"{frappe.local.site}/private/files/xml_files_{invoice_number}.xml"
        tree = ET.ElementTree(invoice)
        with open(xml_file_path, "wb") as file:
            tree.write(file, encoding="utf-8", xml_declaration=True)
        with open(xml_file_path, "r", encoding="utf-8") as file:
            xml_string = file.read()
        xml_dom = minidom.parseString(xml_string)
        pretty_xml_string = xml_dom.toprettyxml(
            indent="  "
        )  # created xml into formatted xml form
        # final_xml_path = f"{frappe.local.site}/private/files/finalzatcaxml_{invoice_number}.xml"
        # with open(final_xml_path, "w", encoding="utf-8") as file:
        #     file.write(pretty_xml_string)
        return pretty_xml_string
    except (FileNotFoundError, IOError):
        frappe.throw(
            _(
                "File operation error occurred while structuring the XML. "
                "Please contact your system administrator."
            )
        )
        return None

    except ET.ParseError:
        frappe.throw(
            _(
                "Error occurred in XML parsing or formatting. "
                "Please check the XML structure for errors. "
                "If the problem persists, contact your system administrator."
            )
        )
        return None
    except UnicodeDecodeError:
        frappe.throw(
            _(
                "Encoding error occurred while processing the XML file. "
                "Please contact your system administrator."
            )
        )
        return None
