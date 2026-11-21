"""
Advance payment invoices from Payment Entry.

A customer advance received through a normal ERPNext Payment Entry (with VAT in
its taxes table) is sent to ZATCA as a prepayment invoice (type 386). A refund of
that advance is sent as a credit note (type 381) against it. On the final Sales
Invoice, advances allocated from such Payment Entries are reported as prepayment
lines with PrepaidAmount, and the VAT already declared on the advance can be
reversed automatically so it is not counted twice.

Everything here is switched on per company (Company > ZATCA >
"Send customer advance Payment Entries to ZATCA"). It does not need or touch the
claudion4saudi "Advance Sales Invoice" route, which keeps working as before.

The XML builders of the existing advance route (advance_payment.py) are reused
unchanged through AdvancePaymentEntryView, a read-only view that gives a Payment
Entry the shape those builders expect.
"""

import base64
import contextlib
import uuid
import xml.etree.ElementTree as ET
from decimal import Decimal, ROUND_HALF_UP

import frappe
import requests
from frappe import _
from frappe.utils import cint, flt, get_time

from zatca_erpgulf.zatca_erpgulf.createxml import xml_tags, get_icv_code
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
)
from zatca_erpgulf.zatca_erpgulf.advance_payment import (
    additional_reference_advanve,
    company_data_advance,
    customer_data_advance,
    delivery_and_payment_means_adavance,
    tax_data,
    item_data_advance,
    xml_structuring_advance,
    xml_base64_decode,
    attach_qr_image_advance,
)
from zatca_erpgulf.zatca_erpgulf.sign_invoice import get_api_url

try:  # frappe >= v15
    from frappe.utils.synchronization import filelock
except ImportError:  # pragma: no cover
    filelock = None

PAYMENT_ENTRY = "Payment Entry"
DONE_STATUSES = ("CLEARED", "REPORTED")
ADVANCE_ITEM_CODE = "ADVANCE"
PREPAYMENT_TYPE = "386"
CREDIT_NOTE_TYPE = "381"
STANDARD_SUBTYPE = "0100000"
SIMPLIFIED_SUBTYPE = "0200000"
REFUND_REASON = "Refund of advance payment"


# --------------------------------------------------------------------------
# Settings and classification
# --------------------------------------------------------------------------


def is_enabled(company):
    """True when the company sends advance Payment Entries to ZATCA."""
    if not company:
        return False
    values = frappe.db.get_value(
        "Company",
        company,
        ["custom_zatca_invoice_enabled", "custom_zatca_advance_payment_entry"],
        as_dict=True,
    )
    return bool(
        values
        and cint(values.custom_zatca_invoice_enabled)
        and cint(values.custom_zatca_advance_payment_entry)
    )


def is_vat_reversal_enabled(company):
    """True when the final invoice should reverse the VAT declared on its advances."""
    return is_enabled(company) and cint(
        frappe.db.get_value("Company", company, "custom_reverse_advance_vat")
    )


def is_advance(pe):
    """A customer receipt with VAT on it = an advance tax invoice."""
    return (
        pe.payment_type == "Receive"
        and pe.party_type == "Customer"
        and bool(pe.get("taxes"))
    )


def is_advance_refund(pe):
    """A payment back to the customer against an advance = a credit note."""
    return (
        pe.payment_type == "Pay"
        and pe.party_type == "Customer"
        and bool(pe.get("custom_advance_refund_against"))
    )


def get_vat_row(pe):
    """The single VAT row of the Payment Entry."""
    taxes = pe.get("taxes") or []
    if len(taxes) != 1:
        frappe.throw(
            _(
                "{0}: an advance sent to ZATCA must have exactly one VAT row in Taxes and Charges."
            ).format(pe.name)
        )
    row = taxes[0]
    if row.charge_type != "On Paid Amount":
        frappe.throw(_("{0}: the VAT row must be 'On Paid Amount'.").format(pe.name))
    if f"{flt(row.rate):.2f}" not in ("5.00", "15.00"):
        frappe.throw(_("{0}: the VAT rate must be 15% or 5%.").format(pe.name))
    if row.add_deduct_tax and row.add_deduct_tax != "Add":
        frappe.throw(_("{0}: the VAT row must be 'Add'.").format(pe.name))
    return row


def get_vat_rate(pe):
    return flt(get_vat_row(pe).rate)


def get_net_amount(pe, base=False):
    """Amount excluding VAT, i.e. what the party account is credited (or debited)."""
    row = get_vat_row(pe)
    paid = flt(pe.base_paid_amount if base else pe.paid_amount)
    if cint(row.included_in_paid_amount):
        tax = flt(row.base_tax_amount if base else row.tax_amount)
        return flt(paid - tax, 2)
    return flt(paid, 2)


def get_refunded_net(advance_name, exclude=None):
    """Net amount already refunded (submitted refund Payment Entries) against an advance."""
    filters = {
        "docstatus": 1,
        "payment_type": "Pay",
        "custom_advance_refund_against": advance_name,
    }
    if exclude:
        filters["name"] = ["!=", exclude]
    total = 0
    for name in frappe.get_all(PAYMENT_ENTRY, filters=filters, pluck="name"):
        total += get_net_amount(frappe.get_doc(PAYMENT_ENTRY, name))
    return flt(total, 2)


def is_simplified(pe):
    return cint(frappe.db.get_value("Customer", pe.party, "custom_b2c")) == 1


# --------------------------------------------------------------------------
# View: a Payment Entry shaped like an Advance Sales Invoice
# --------------------------------------------------------------------------


class AdvancePaymentEntryView:
    """Read-only view over a Payment Entry exposing the fields that the
    advance_payment.py XML builders read (custom_item, total, base_total, tax
    category). Everything else, db_set included, goes to the Payment Entry."""

    def __init__(self, pe):
        self.__dict__["_pe"] = pe
        net = get_net_amount(pe)
        base_net = get_net_amount(pe, base=True)
        rate = get_vat_rate(pe)
        so = next(
            (
                r.reference_name
                for r in pe.get("references") or []
                if r.reference_doctype == "Sales Order"
            ),
            None,
        )
        if is_advance_refund(pe):
            label = _("Refund of advance {0}").format(pe.custom_advance_refund_against)
        elif so:
            label = _("Advance payment for {0}").format(so)
        else:
            label = _("Advance payment")
        line = frappe._dict(
            idx=1,
            item_code=ADVANCE_ITEM_CODE,
            item_name=label,
            uom="EA",
            qty=1,
            rate=net,
            price_list_rate=net,
            amount=net,
            base_amount=base_net,
            net_amount=net,
            base_net_amount=base_net,
            item_tax_template=None,
        )
        self.__dict__.update(
            custom_item=[line],
            total=net,
            base_total=base_net,
            net_total=net,
            base_net_total=base_net,
            vat_rate=rate,
            custom_zatca_tax_category="Standard",
            custom_exemption_reason_code=None,
            custom_tax_exemption_reason=None,
            doctype=PAYMENT_ENTRY,
        )

    def __getattr__(self, name):
        return getattr(self.__dict__["_pe"], name)

    def get(self, key, default=None):
        if key in self.__dict__:
            return self.__dict__[key]
        return self.__dict__["_pe"].get(key, default)

    def db_set(self, *args, **kwargs):
        return self.__dict__["_pe"].db_set(*args, **kwargs)

    def notify_update(self):
        return self.__dict__["_pe"].notify_update()


# --------------------------------------------------------------------------
# XML
# --------------------------------------------------------------------------


def _header(invoice, view):
    ET.SubElement(invoice, "cbc:ProfileID").text = "reporting:1.0"
    ET.SubElement(invoice, "cbc:ID").text = str(view.name)
    uuid1 = str(uuid.uuid1())
    ET.SubElement(invoice, "cbc:UUID").text = uuid1
    ET.SubElement(invoice, "cbc:IssueDate").text = str(view.posting_date)
    ET.SubElement(invoice, "cbc:IssueTime").text = issue_time(view)
    return uuid1


def issue_time(pe):
    """Payment Entry has no posting time: its creation time is used, the same in
    the advance's own XML and in every final invoice that refers to it."""
    return get_time(pe.creation).strftime("%H:%M:%S")


def _type_code(invoice, simplified, refund):
    code = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
    code.set("name", SIMPLIFIED_SUBTYPE if simplified else STANDARD_SUBTYPE)
    code.text = CREDIT_NOTE_TYPE if refund else PREPAYMENT_TYPE


def _currency_and_icv(invoice, view, refund):
    ET.SubElement(invoice, "cbc:DocumentCurrencyCode").text = view.paid_from_account_currency
    ET.SubElement(invoice, "cbc:TaxCurrencyCode").text = "SAR"
    if refund:
        billing = ET.SubElement(invoice, "cac:BillingReference")
        ref = ET.SubElement(billing, "cac:InvoiceDocumentReference")
        ET.SubElement(ref, "cbc:ID").text = str(view.custom_advance_refund_against)
    icv = ET.SubElement(invoice, "cac:AdditionalDocumentReference")
    ET.SubElement(icv, "cbc:ID").text = "ICV"
    ET.SubElement(icv, "cbc:UUID").text = str(get_icv_code(view.name))


def _child(element, tag):
    """First direct child with this literal tag. The builders write prefixed tag
    names ("cac:Party") without namespaces, so ElementTree's find() can't be used."""
    if element is None:
        return None
    return next((c for c in element if c.tag == tag), None)


def _add_buyer_vat(invoice, pe):
    """Buyer VAT number (BT-48), as the normal Sales Invoice XML does: Saudi
    customers with a VAT number only (BR-KSA-44)."""
    tax_id, address_name = frappe.db.get_value(
        "Customer", pe.party, ["tax_id", "customer_primary_address"]
    )
    if not tax_id or not address_name:
        return
    if frappe.db.get_value("Address", address_name, "country") != "Saudi Arabia":
        return
    scheme = _child(_child(_child(invoice, "cac:AccountingCustomerParty"), "cac:Party"), "cac:PartyTaxScheme")
    if scheme is None or _child(scheme, "cbc:CompanyID") is not None:
        return
    company_id = ET.Element("cbc:CompanyID")
    company_id.text = tax_id
    scheme.insert(0, company_id)


def _add_instruction_note(invoice):
    """Credit notes need the reason (KSA-10) in PaymentMeans."""
    means = _child(invoice, "cac:PaymentMeans")
    if means is not None:
        ET.SubElement(means, "cbc:InstructionNote").text = REFUND_REASON


def build_signed_xml(pe):
    """Build and sign the XML; returns (uuid, hash, signed file path, qr b64)."""
    view = AdvancePaymentEntryView(pe)
    refund = is_advance_refund(pe)
    simplified = is_simplified(pe)
    company_abbr = frappe.db.get_value("Company", pe.company, "abbr")

    invoice = xml_tags()
    uuid1 = _header(invoice, view)
    _type_code(invoice, simplified, refund)
    _currency_and_icv(invoice, view, refund)
    invoice = additional_reference_advanve(invoice, company_abbr, view)
    invoice = company_data_advance(invoice, view)
    invoice = customer_data_advance(invoice, view)
    _add_buyer_vat(invoice, pe)
    invoice = delivery_and_payment_means_adavance(invoice, view)
    if refund:
        _add_instruction_note(invoice)
    invoice = tax_data(invoice, view)
    invoice = item_data_advance(invoice, view, pe.name)
    file_content = xml_structuring_advance(invoice, view)

    canonicalized_xml = canonicalize_xml(removetags(file_content))
    hash1, encoded_hash = getinvoicehash(canonicalized_xml)
    encoded_signature = digital_signature(hash1, company_abbr, pe)
    issuer_name, serial_number = extract_certificate_details(company_abbr, pe)
    encoded_certificate_hash = certificate_hash(company_abbr, pe)
    modified_xml_string, namespaces, signing_time = signxml_modify(
        company_abbr, file_content, pe
    )
    signed_properties_base64 = generate_signed_properties_hash(
        signing_time, issuer_name, serial_number, encoded_certificate_hash
    )
    final_xml_string = populate_the_ubl_extensions_output(
        modified_xml_string,
        encoded_signature,
        namespaces,
        signed_properties_base64,
        encoded_hash,
        company_abbr,
        pe,
    )
    tlv_data = generate_tlv_xml(final_xml_string, company_abbr, pe)
    qrcodeb64 = base64.b64encode(
        b"".join(get_tlv_for_value(num, value) for num, value in tlv_data.items())
    ).decode("utf-8")
    updated_xml_string = update_qr_toxml(final_xml_string, qrcodeb64, company_abbr)
    signed_xmlfile_name = structuring_signedxml(pe.name, updated_xml_string)
    return view, uuid1, encoded_hash, signed_xmlfile_name, qrcodeb64, simplified


# --------------------------------------------------------------------------
# Sending
# --------------------------------------------------------------------------


@contextlib.contextmanager
def _company_chain_lock(company):
    """Send one document at a time per company so the PIH chain stays in order."""
    if filelock is None:
        yield
        return
    with filelock(f"zatca_pih_{frappe.scrub(company)}", timeout=120):
        yield


def _set_not_submitted(pe, message):
    pe.db_set("custom_zatca_status", "Not Submitted", update_modified=False)
    pe.db_set("custom_zatca_full_response", message, update_modified=False)


def _attach_xml(pe, xml_text, label):
    file = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": f"{label} xml file {pe.name}.xml",
            "attached_to_doctype": pe.doctype,
            "attached_to_name": pe.name,
            "is_private": 1,
            "content": xml_text,
        }
    )
    file.save(ignore_permissions=True)
    pe.db_set("custom_ksa_einvoicing_xml", file.file_url, update_modified=False)


def send_to_zatca(pe):
    """Sign and send one advance (or advance refund) Payment Entry to ZATCA."""
    if pe.get("custom_zatca_status") in DONE_STATUSES:
        frappe.throw(_("{0} has already been sent to ZATCA.").format(pe.name))

    with _company_chain_lock(pe.company):
        company_abbr, csid = frappe.db.get_value(
            "Company", pe.company, ["abbr", "custom_basic_auth_from_production"]
        )
        if not csid:
            frappe.throw(_("Production CSID for company {0} not found.").format(pe.company))

        view, uuid1, encoded_hash, signed_file, qrcodeb64, simplified = build_signed_xml(pe)
        payload = {
            "invoiceHash": encoded_hash,
            "uuid": uuid1,
            "invoice": xml_base64_decode(signed_file),
        }
        headers = {
            "accept": "application/json",
            "accept-language": "en",
            "Clearance-Status": "0" if simplified else "1",
            "Accept-Version": "V2",
            "Authorization": "Basic " + csid,
            "Content-Type": "application/json",
        }
        endpoint = "invoices/reporting/single" if simplified else "invoices/clearance/single"
        try:
            response = requests.post(
                url=get_api_url(company_abbr, base_url=endpoint),
                headers=headers,
                json=payload,
                timeout=300,
            )
        except requests.RequestException as e:
            _set_not_submitted(pe, str(e))
            frappe.throw(_("ZATCA could not be reached: {0}").format(e))

        if response.status_code not in (200, 202):
            _set_not_submitted(pe, response.text)
            frappe.throw(
                _("ZATCA rejected {0}. Status code: {1}<br><br>{2}").format(
                    pe.name, response.status_code, response.text
                )
            )

        status = "REPORTED" if simplified else "CLEARED"
        prefix = "WITH WARNINGS: " if response.status_code == 202 else "SUCCESS: "
        # ERPGulf's QR step (tag8_publickey -> create_public_key) saves and commits
        # the Company while the XML is built, so a Company doc loaded before it is
        # stale ("Document has been modified"). Write the PIH directly instead.
        frappe.db.set_value("Company", pe.company, "custom_pih", encoded_hash)

        pe.db_set("custom_uuid", uuid1, update_modified=False)
        pe.db_set("custom_zatca_status", status, update_modified=False)
        pe.db_set(
            "custom_zatca_full_response",
            f"{prefix}Status Code: {response.status_code}<br><br>{response.text}",
            update_modified=False,
        )

        if simplified:
            with open(signed_file, encoding="utf-8") as f:
                xml_text = f.read()
            _attach_xml(pe, xml_text, "Reported")
        else:
            cleared = (response.json() or {}).get("clearedInvoice")
            xml_text = base64.b64decode(cleared).decode("utf-8") if cleared else ""
            if xml_text:
                _attach_xml(pe, xml_text, "Cleared")
        attach_qr_image_advance(qrcodeb64, view)
        return status


# --------------------------------------------------------------------------
# Payment Entry hooks
# --------------------------------------------------------------------------


def before_validate_payment_entry(doc, method=None):
    """With VAT included in the amount, the party is credited only the amount
    excluding VAT: cap the Sales Order allocation so the entry balances."""
    if not (is_enabled(doc.company) and is_advance(doc)):
        return
    row = (doc.get("taxes") or [None])[0]
    if not row or not cint(row.included_in_paid_amount) or not flt(row.rate):
        return
    net = flt(flt(doc.paid_amount) / (1 + flt(row.rate) / 100), 2)
    allocated = 0
    for ref in doc.get("references") or []:
        if ref.reference_doctype != "Sales Order":
            continue
        room = max(0, flt(net - allocated, 2))
        if flt(ref.allocated_amount) > room:
            ref.allocated_amount = room
        allocated += flt(ref.allocated_amount)


def validate_payment_entry(doc, method=None):
    if not is_enabled(doc.company):
        return
    if is_advance(doc):
        get_vat_row(doc)
    elif is_advance_refund(doc):
        get_vat_row(doc)
        original = frappe.get_doc(PAYMENT_ENTRY, doc.custom_advance_refund_against)
        if original.docstatus != 1 or original.party != doc.party:
            frappe.throw(_("The advance being refunded must be a submitted Payment Entry for the same customer."))
        if original.get("custom_zatca_status") not in DONE_STATUSES:
            frappe.throw(_("The advance {0} has not been sent to ZATCA.").format(original.name))
        available = flt(
            get_net_amount(original)
            - get_refunded_net(original.name, exclude=doc.name)
            - get_allocated_to_invoices(original.name),
            2,
        )
        if get_net_amount(doc) - available > 0.01:
            frappe.throw(
                _("Refund (excluding VAT) {0} is more than what is left on advance {1}: {2}.").format(
                    get_net_amount(doc), original.name, available
                )
            )


def on_submit_payment_entry(doc, method=None):
    if not is_enabled(doc.company):
        return
    if is_advance(doc) or is_advance_refund(doc):
        send_to_zatca(doc)


def before_cancel_payment_entry(doc, method=None):
    if is_enabled(doc.company) and doc.get("custom_zatca_status") in DONE_STATUSES:
        frappe.throw(
            _(
                "{0} has been sent to ZATCA and cannot be cancelled. Use Refund Advance to refund the customer."
            ).format(doc.name)
        )


@frappe.whitelist()
def resend_payment_entry(name):
    """Retry a submitted advance whose sending failed."""
    pe = frappe.get_doc(PAYMENT_ENTRY, name)
    pe.check_permission("submit")
    if pe.docstatus != 1:
        frappe.throw(_("Submit the Payment Entry first."))
    if not (is_enabled(pe.company) and (is_advance(pe) or is_advance_refund(pe))):
        frappe.throw(_("This Payment Entry is not an advance for ZATCA."))
    return send_to_zatca(pe)


@frappe.whitelist()
def make_advance_refund(source_name):
    """New draft Payment Entry paying back what is left of an advance, VAT included."""
    src = frappe.get_doc(PAYMENT_ENTRY, source_name)
    src.check_permission("read")
    if not is_advance(src) or src.get("custom_zatca_status") not in DONE_STATUSES:
        frappe.throw(_("Only an advance that has been sent to ZATCA can be refunded."))
    row = get_vat_row(src)
    left_net = flt(
        get_net_amount(src) - get_refunded_net(src.name) - get_allocated_to_invoices(src.name),
        2,
    )
    if left_net <= 0:
        frappe.throw(_("Nothing is left to refund on {0}.").format(src.name))

    pe = frappe.new_doc(PAYMENT_ENTRY)
    pe.payment_type = "Pay"
    pe.company = src.company
    pe.posting_date = frappe.utils.nowdate()
    pe.mode_of_payment = src.mode_of_payment
    pe.party_type = "Customer"
    pe.party = src.party
    pe.party_name = src.party_name
    pe.paid_from = src.paid_to
    pe.paid_to = src.paid_from
    pe.paid_from_account_currency = src.paid_to_account_currency
    pe.paid_to_account_currency = src.paid_from_account_currency
    pe.cost_center = src.cost_center
    pe.project = src.get("project")
    pe.custom_advance_refund_against = src.name
    pe.sales_taxes_and_charges_template = src.get("sales_taxes_and_charges_template")
    gross = flt(left_net * (1 + flt(row.rate) / 100), 2)
    pe.paid_amount = gross
    pe.received_amount = gross
    pe.source_exchange_rate = 1
    pe.target_exchange_rate = 1
    pe.append(
        "taxes",
        {
            "charge_type": "On Paid Amount",
            "account_head": row.account_head,
            "description": row.description,
            "rate": row.rate,
            "add_deduct_tax": "Add",
            "included_in_paid_amount": 1,
            "cost_center": row.cost_center,
        },
    )
    pe.remarks = _("Refund of advance {0}").format(src.name)
    pe.setup_party_account_field()
    pe.set_missing_values()
    return pe.as_dict()


# --------------------------------------------------------------------------
# Final Sales Invoice
# --------------------------------------------------------------------------


def get_allocated_to_invoices(advance_name):
    """Net amount of an advance used on submitted Sales Invoices."""
    total = frappe.db.sql(
        """
        select coalesce(sum(adv.allocated_amount), 0)
        from `tabSales Invoice Advance` adv
        join `tabSales Invoice` si on si.name = adv.parent
        where adv.reference_type = 'Payment Entry' and adv.reference_name = %s
          and si.docstatus = 1
        """,
        advance_name,
    )
    return flt(total[0][0] if total else 0, 2)


def get_prepayments(sales_invoice_doc):
    """Advances on this Sales Invoice that were sent to ZATCA as Payment Entries:
    one dict per advance with the amounts to report."""
    if sales_invoice_doc.doctype != "Sales Invoice" or not is_enabled(
        sales_invoice_doc.company
    ):
        return []
    result = []
    for adv in sales_invoice_doc.get("advances") or []:
        if adv.reference_type != PAYMENT_ENTRY or flt(adv.allocated_amount) <= 0:
            continue
        pe = frappe.get_doc(PAYMENT_ENTRY, adv.reference_name)
        if not is_advance(pe) or pe.get("custom_zatca_status") not in DONE_STATUSES:
            continue
        rate = get_vat_rate(pe)
        taxable = Decimal(str(flt(adv.allocated_amount))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        tax = (taxable * Decimal(str(rate)) / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        result.append(
            frappe._dict(
                name=pe.name,
                uuid=pe.custom_uuid,
                issue_date=str(pe.posting_date),
                issue_time=issue_time(pe),
                rate=rate,
                taxable=taxable,
                tax=tax,
                gross=taxable + tax,
                tax_account=get_vat_row(pe).account_head,
            )
        )
    return result


def get_prepaid_amount(sales_invoice_doc):
    """Total prepaid (VAT included) to report as PrepaidAmount, or None."""
    prepayments = get_prepayments(sales_invoice_doc)
    if not prepayments:
        return None
    return sum((p.gross for p in prepayments), Decimal("0"))


def add_prepayment_lines(invoice, sales_invoice_doc):
    """Append one zero-quantity prepayment InvoiceLine per advance (same layout as
    the claudion4saudi route) after the invoice's own item lines."""
    prepayments = get_prepayments(sales_invoice_doc)
    if not prepayments:
        return invoice
    currency = sales_invoice_doc.currency
    next_id = len(sales_invoice_doc.get("items") or []) + 1
    for i, p in enumerate(prepayments):
        line = ET.SubElement(invoice, "cac:InvoiceLine")
        ET.SubElement(line, "cbc:ID").text = str(next_id + i)
        ET.SubElement(line, "cbc:InvoicedQuantity", unitCode="EA").text = "0.000000"
        ET.SubElement(line, "cbc:LineExtensionAmount", currencyID=currency).text = "0.00"

        docref = ET.SubElement(line, "cac:DocumentReference")
        ET.SubElement(docref, "cbc:ID").text = p.name
        ET.SubElement(docref, "cbc:UUID").text = p.uuid
        ET.SubElement(docref, "cbc:IssueDate").text = p.issue_date
        ET.SubElement(docref, "cbc:IssueTime").text = p.issue_time
        ET.SubElement(docref, "cbc:DocumentTypeCode").text = PREPAYMENT_TYPE

        tax_total = ET.SubElement(line, "cac:TaxTotal")
        ET.SubElement(tax_total, "cbc:TaxAmount", currencyID=currency).text = "0"
        ET.SubElement(tax_total, "cbc:RoundingAmount", currencyID=currency).text = "0"
        subtotal = ET.SubElement(tax_total, "cac:TaxSubtotal")
        ET.SubElement(subtotal, "cbc:TaxableAmount", currencyID=currency).text = str(p.taxable)
        ET.SubElement(subtotal, "cbc:TaxAmount", currencyID=currency).text = str(p.tax)
        category = ET.SubElement(subtotal, "cac:TaxCategory")
        ET.SubElement(category, "cbc:ID").text = "S"
        ET.SubElement(category, "cbc:Percent").text = f"{p.rate:.2f}"
        ET.SubElement(ET.SubElement(category, "cac:TaxScheme"), "cbc:ID").text = "VAT"

        item = ET.SubElement(line, "cac:Item")
        ET.SubElement(item, "cbc:Name").text = _("Advance payment {0}").format(p.name)
        classified = ET.SubElement(item, "cac:ClassifiedTaxCategory")
        ET.SubElement(classified, "cbc:ID").text = "S"
        ET.SubElement(classified, "cbc:Percent").text = f"{p.rate:.2f}"
        ET.SubElement(ET.SubElement(classified, "cac:TaxScheme"), "cbc:ID").text = "VAT"

        price = ET.SubElement(line, "cac:Price")
        ET.SubElement(price, "cbc:PriceAmount", currencyID=currency).text = "0.00"
    return invoice


def validate_sales_invoice_advances(doc, method=None):
    """Before submit: only advances that reached ZATCA, and never more than is left."""
    if not is_enabled(doc.company):
        return
    for adv in doc.get("advances") or []:
        if adv.reference_type != PAYMENT_ENTRY or flt(adv.allocated_amount) <= 0:
            continue
        pe = frappe.get_doc(PAYMENT_ENTRY, adv.reference_name)
        if not is_advance(pe):
            continue
        if pe.get("custom_zatca_status") not in DONE_STATUSES:
            frappe.throw(
                _("Advance {0} has not been sent to ZATCA yet. Send it first.").format(pe.name)
            )
        left = flt(
            get_net_amount(pe) - get_refunded_net(pe.name) - get_allocated_to_invoices(pe.name),
            2,
        )
        if flt(adv.allocated_amount) - left > 0.01:
            frappe.throw(
                _("Advance {0} has only {1} left (excluding VAT).").format(pe.name, left)
            )


def reverse_advance_vat(doc, method=None):
    """After submit: the VAT on the allocated advances was declared when the
    customer paid. Post Dr VAT / Cr customer against this invoice so it is
    counted once and the invoice is settled."""
    if not is_vat_reversal_enabled(doc.company):
        return
    prepayments = get_prepayments(doc)
    if not prepayments:
        return
    by_account = {}
    for p in prepayments:
        by_account[p.tax_account] = by_account.get(p.tax_account, Decimal("0")) + p.tax
    total = sum(by_account.values(), Decimal("0"))
    if total <= 0:
        return

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = doc.company
    je.posting_date = doc.posting_date
    je.user_remark = _("Reversal of advance VAT already declared, for {0}").format(doc.name)
    for account, amount in by_account.items():
        je.append(
            "accounts",
            {
                "account": account,
                "debit_in_account_currency": flt(amount),
                "cost_center": doc.cost_center,
            },
        )
    je.append(
        "accounts",
        {
            "account": doc.debit_to,
            "party_type": "Customer",
            "party": doc.customer,
            "credit_in_account_currency": flt(total),
            "reference_type": "Sales Invoice",
            "reference_name": doc.name,
            "cost_center": doc.cost_center,
        },
    )
    je.flags.ignore_permissions = True
    je.insert()
    je.submit()
    doc.db_set("custom_advance_vat_reversal", je.name, update_modified=False)


def cancel_advance_vat_reversal(doc, method=None):
    """Before cancel: the reversal goes with the invoice."""
    name = doc.get("custom_advance_vat_reversal")
    if not name:
        return
    je = frappe.get_doc("Journal Entry", name)
    if je.docstatus == 1:
        je.flags.ignore_permissions = True
        je.cancel()
