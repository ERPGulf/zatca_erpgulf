from decimal import Decimal, ROUND_HALF_UP
from num2words import num2words

def arabic_money_in_words(amount):
    try:
        if amount in (None, ""):
            return ""

        amount = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        main_val = int(amount)
        fractional_val = int((amount - main_val) * 100)

        main_words = num2words(main_val, lang="ar")

        if fractional_val > 0:
            fraction_words = num2words(fractional_val, lang="ar")
            return f"{main_words} ريال سعودي و {fraction_words} هللة فقط"

        return f"{main_words} ريال سعودي فقط"

    except Exception:
        return ""


def arabic_number(value):
    if value in (None, ""):
        return ""

    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    english_digits = "0123456789"

    value = str(value)

    # Replace decimal point with Arabic decimal
    value = value.replace(".", "٫")

    trans = str.maketrans(english_digits, arabic_digits)
    return value.translate(trans)



import frappe
import qrcode
from io import BytesIO
from frappe.utils import now_datetime
def generate_qr_and_attach_doctype(doctype, docname, url, file_field=None):
    if not url:
        frappe.throw("QR URL is required")

    doc = frappe.get_doc(doctype, docname)

    filename = f"{doctype}-{docname}-QR.png".replace(" ", "_")

    existing = frappe.db.exists("File", {
        "attached_to_doctype": doctype,
        "attached_to_name": docname,
        "file_name": filename
    })

    if existing:
        return frappe.db.get_value("File", existing, "file_url")

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": filename,
        "attached_to_doctype": doctype,
        "attached_to_name": docname,
        "content": buffer.getvalue(),
        "is_private": 0
    })
    file_doc.insert(ignore_permissions=True)

    if file_field and doc.meta.has_field(file_field):
        doc.set(file_field, file_doc.file_url)
        doc.save(ignore_permissions=True)

    return file_doc.file_url


@frappe.whitelist()
def generate_qr_for_doc(doctype, docname, url, file_field=None):
    return generate_qr_and_attach_doctype(
        doctype=doctype,
        docname=docname,
        url=url,
        file_field=file_field
    )
