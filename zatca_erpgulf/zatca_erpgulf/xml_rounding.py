"""Keep the ZATCA XML header consistent with its invoice lines on tax-inclusive invoices.

The XML lines write each item's net as round(amount / (1 + rate), 2). Since ERPNext
v15.125.0 / v16.54.0 ("distribute inclusive net rounding") ERPNext carries rounding
across items, so its net_total can be 0.01 off the sum of those lines. That gives
BR-CO-10, BR-CO-13 and BR-S-08 warnings and a TaxInclusiveAmount 0.01 off the
grand total.

This aligns the in-memory document used to build the XML with the same per-line
rounding the lines use. It is never saved: invoice values in ERPNext are untouched.
"""

from decimal import Decimal, ROUND_HALF_UP

import frappe
from frappe.utils import flt


def align_inclusive_net_for_xml(doc):
    taxes = doc.get("taxes") or []
    if not taxes or not taxes[0].included_in_print_rate:
        return doc
    if doc.get("custom_zatca_nominal_invoice"):
        return doc
    if any(item.get("item_tax_template") for item in doc.items):
        # Per-item tax rates: lines are built differently, left as ERPNext calculated
        return doc
    if doc.get("apply_discount_on") == "Grand Total" and flt(doc.get("discount_amount")):
        return doc

    divisor = 1 + flt(taxes[0].rate) / 100
    # Same formula as the XML line code, so lines and header always agree
    nets = [round(flt(item.amount) / divisor, 2) for item in doc.items]
    base_nets = [round(flt(item.base_amount) / divisor, 2) for item in doc.items]

    discount = flt(doc.get("discount_amount"))
    base_discount = flt(doc.get("base_discount_amount"))

    _set_item_nets(doc.items, nets, discount, "net_amount")
    _set_item_nets(doc.items, base_nets, base_discount, "base_net_amount")
    doc.net_total = round(sum(nets) - discount, 2)
    doc.base_net_total = round(sum(base_nets) - base_discount, 2)

    _log_if_total_differs(doc, flt(taxes[0].rate))
    return doc


def _set_item_nets(items, line_nets, discount, field):
    """Item nets = line net minus its share of the net document discount."""
    total = sum(line_nets)
    remaining = round(discount, 2)
    last = len(items) - 1
    for idx, (item, line_net) in enumerate(zip(items, line_nets)):
        if idx == last:
            share = remaining
        else:
            share = round(discount * line_net / total, 2) if total else 0
            remaining = round(remaining - share, 2)
        item.set(field, round(line_net - share, 2))


def _log_if_total_differs(doc, rate):
    """XML total = net + VAT. Log when it isn't the invoice grand total."""
    vat = Decimal(str(abs(sum(flt(i.base_net_amount) * rate / 100 for i in doc.items)))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    xml_total = Decimal(str(abs(doc.base_net_total))).quantize(Decimal("0.01")) + vat
    grand_total = Decimal(str(abs(flt(doc.base_grand_total)))).quantize(Decimal("0.01"))
    if xml_total != grand_total:
        frappe.log_error(
            title=f"ZATCA XML total differs from grand total: {doc.name}",
            message=(
                f"{doc.doctype} {doc.name}: XML total {xml_total} "
                f"(net {doc.base_net_total} + VAT {vat}) vs grand total {grand_total}"
            ),
        )