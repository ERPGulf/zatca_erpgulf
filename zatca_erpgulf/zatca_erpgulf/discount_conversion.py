"""Grand Total discount support for ZATCA XML.

ZATCA only accepts a document discount before VAT. ERPNext's "Grand Total" discount is
VAT-inclusive, but ERPNext already spreads it over net and VAT, so net_total, taxes and
grand_total on the invoice are correct. For the XML we only re-express the discount as
its net (ex-VAT) amount. This is done on the in-memory doc used to build the XML and is
never saved, so the invoice keeps showing Grand Total and the amount the user entered.
"""

from frappe.utils import flt


def normalize_grand_total_discount_for_xml(doc):
    if doc.get("apply_discount_on") != "Grand Total" or not flt(doc.get("discount_amount")):
        return doc
    if not doc.get("taxes"):
        return doc

    tax_row = doc.taxes[0]
    rate = flt(tax_row.rate)

    if tax_row.included_in_print_rate:
        # Same per-line rounding the XML uses for LineExtensionAmount
        net_before = sum(round(flt(i.amount) / (1 + rate / 100), 2) for i in doc.items)
        base_net_before = sum(round(flt(i.base_amount) / (1 + rate / 100), 2) for i in doc.items)
    else:
        net_before = flt(doc.total)
        base_net_before = flt(doc.base_total)

    # Net allowance = net before discount - net after discount (as ERPNext computed it)
    doc.discount_amount = round(net_before - flt(doc.net_total), 2)
    doc.base_discount_amount = round(base_net_before - flt(doc.base_net_total), 2)
    doc.additional_discount_percentage = 0
    doc.apply_discount_on = "Net Total"
    return doc