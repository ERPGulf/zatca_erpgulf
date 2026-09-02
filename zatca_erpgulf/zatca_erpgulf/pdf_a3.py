"""New function for print pdf a3"""

from datetime import datetime
import hashlib
import os
import tempfile
import pikepdf
import frappe
import frappe.utils
from frappe.utils.pdf import get_pdf
from frappe import _
from frappe.utils import get_site_path, get_url
from frappe.model.document import Document


def generate_invoice_pdf(invoice, language, letterhead=None, print_format=None):
    """Function for generating invoice PDF based on the provided print format, letterhead, and language."""

    # Set the language for the PDF generation
    invoice_name = invoice.name
    original_language = frappe.local.lang
    try:
        frappe.local.lang = language
        html = frappe.get_print(
            doctype="Sales Invoice",
            name=invoice_name,  # Use the invoice's name directly
            print_format=print_format,  # Use the selected print format
            no_letterhead=not bool(letterhead),  # Use letterhead only if specified
            letterhead=letterhead,  # Specify the letterhead if provided
        )
    finally:
        # restore even if get_print raises
        frappe.local.lang = original_language

    # Generate PDF content from the HTML
    pdf_content = get_pdf(html)
    safe_invoice_name = invoice_name.replace("/", "-")
    # Set the path for saving the generated PDF
    site_path = frappe.local.site_path  # sites/<site>, not just the site name
    file_name = f"{safe_invoice_name}-src.pdf"
    file_path = os.path.join(site_path, "private", "files", file_name)

    # Write the PDF content to the file
    # nosemgrep: frappe-semgrep-rules.rules.security.frappe-security-file-traversal
    with open(file_path, "wb") as pdf_file: 
        pdf_file.write(pdf_content)

    # Return the path of the generated PDF file
    return file_path


def embed_file_in_pdf_1(
    input_pdf, xml_file, output_pdf, invoice_name=None, company_name=""
):
    """Embed the cleared ZATCA XML and finish the file as real PDF/A-3B."""
    app_path = frappe.get_app_path("zatca_erpgulf")
    icc_path = app_path + "/sRGB.icc"

    if not invoice_name:
        invoice_name = os.path.splitext(os.path.basename(output_pdf))[0]
    # plain ASCII, no spaces: some portal parsers choke on the old
    # "Cleared xml file SI-AO-SA-07774.xml"
    xml_name = invoice_name.replace("/", "-").replace(" ", "-") + ".xml"
    now = datetime.now().replace(microsecond=0)
    pdf_now = now.strftime("D:%Y%m%d%H%M%S")
    title = f"Tax Invoice {invoice_name}"
    subject = "ZATCA e-invoice (PDF/A-3 with embedded UBL 2.1 XML)"
    producer = "ERPGulf ZATCA e-Invoice"


    # frappe.throw(icc_path)
    with pikepdf.open(input_pdf, allow_overwriting_input=True) as pdf:
        # XMP written ONCE (the old code wrote open_metadata() and then
        # overwrote /Metadata with a hand-built string, so the placeholder
        # "John Doe" / "PDF/A-3 Example" values were the ones that shipped).
        with pdf.open_metadata(
            set_pikepdf_as_editor=False, update_docinfo=False
        ) as metadata:
            metadata.clear()
            metadata["pdfaid:part"] = "3"
            metadata["pdfaid:conformance"] = "B"
            metadata["dc:title"] = title
            metadata["dc:creator"] = [company_name]
            metadata["dc:description"] = subject
            metadata["dc:format"] = "application/pdf"
            metadata["pdf:Producer"] = producer
            metadata["xmp:CreatorTool"] = producer
            metadata["xmp:CreateDate"] = now.isoformat()
            metadata["xmp:ModifyDate"] = now.isoformat()

        # PDF/A-3B is not a tagged flavour. Do not claim /Marked true with an
        # empty structure tree, and /GTS_PDFA1 is not a catalog key at all.
        for junk in ("/MarkInfo", "/StructTreeRoot", "/GTS_PDFA1"):
            if junk in pdf.Root:
                del pdf.Root[junk]
        pdf.Root["/Lang"] = pikepdf.String("en-US")


        # Embed the XML file
        # nosemgrep: frappe-semgrep-rules.rules.security.frappe-security-file-traversal
        with open(xml_file, "rb") as xml_f:
            xml_data = xml_f.read()

        embedded_file_stream = pdf.make_stream(xml_data)
        # A plain str becomes a PDF *string*: "/Type (/EmbeddedFile)". These
        # must be Names. Pass the real MIME type and let pikepdf escape the
        # slash -> /text#2fxml. Do NOT pre-escape as "/text#2Fxml".
        embedded_file_stream.Type = pikepdf.Name("/EmbeddedFile")
        embedded_file_stream.Subtype = pikepdf.Name("/text/xml")
        # /Params with /ModDate is mandatory in PDF/A-3
        embedded_file_stream.Params = pikepdf.Dictionary(
            {
                "/ModDate": pikepdf.String(pdf_now),
                "/Size": len(xml_data),
                "/CheckSum": pikepdf.String(hashlib.md5(xml_data).digest()),
            }
        )

        embedded_file_dict = pdf.make_indirect(
            pikepdf.Dictionary(
                {
                    "/Type": pikepdf.Name("/Filespec"),
                    "/F": pikepdf.String(xml_name),
                    "/UF": pikepdf.String(xml_name),
                    "/Desc": pikepdf.String(
                        f"ZATCA cleared e-invoice XML for {invoice_name}"
                    ),
                    "/AFRelationship": pikepdf.Name("/Alternative"),
                    "/EF": pikepdf.Dictionary(
                        {"/F": embedded_file_stream, "/UF": embedded_file_stream}
                    ),
                }
            )
        )

        # Rebuild the name tree, never append. Appending is how a second
        # copy of the XML survived, and it left the tree unsorted, which
        # breaks readers that binary-search it.
        pdf.Root.Names = pdf.make_indirect(
            pikepdf.Dictionary(
                {
                    "/EmbeddedFiles": pdf.make_indirect(
                        pikepdf.Dictionary(
                            {
                                "/Names": pikepdf.Array(
                                    [pikepdf.String(xml_name), embedded_file_dict]
                                )
                            }
                        )
                    )
                }
            )
        )

        # Associated File. Without /AF the XML is only an attachment and an
        # e-invoice parser will not recognise it as the invoice payload.
        pdf.Root["/AF"] = pdf.make_indirect(pikepdf.Array([embedded_file_dict]))

        # Set OutputIntent
        with open(icc_path, "rb") as icc_file:  # nosemgrep: frappe-semgrep-rules.rules.security.frappe-security-file-traversal
            icc_data = icc_file.read()
            icc_stream = pdf.make_stream(icc_data)
            icc_stream.N = 3
            output_intent_dict = pikepdf.Dictionary(
                {
                    "/Type": pikepdf.Name("/OutputIntent"),
                    "/S": pikepdf.Name("/GTS_PDFA1"),
                    "/OutputConditionIdentifier": pikepdf.String("sRGB IEC61966-2.1"),
                    "/Info": pikepdf.String("sRGB IEC61966-2.1"),
                    "/RegistryName": pikepdf.String("http://www.color.org"),
                    "/DestOutputProfile": icc_stream,
                }
            )
            # exactly one output intent; appending could leave a stale one
            pdf.Root["/OutputIntents"] = pikepdf.Array([output_intent_dict])


        # DocInfo must agree with the XMP above or PDF/A validation fails.
        for key in list(pdf.docinfo.keys()):
            del pdf.docinfo[key]
        pdf.docinfo["/Title"] = pikepdf.String(title)
        pdf.docinfo["/Author"] = pikepdf.String(company_name)
        pdf.docinfo["/Subject"] = pikepdf.String(subject)
        pdf.docinfo["/Creator"] = pikepdf.String(producer)
        pdf.docinfo["/Producer"] = pikepdf.String(producer)
        pdf.docinfo["/CreationDate"] = pikepdf.String(pdf_now)
        pdf.docinfo["/ModDate"] = pikepdf.String(pdf_now)

        # PDF/A-3 is built on PDF 1.7; the old files went out as %PDF-1.3
        pdf.save(
            output_pdf,
            min_version="1.7",
            object_stream_mode=pikepdf.ObjectStreamMode.disable,
        )


@frappe.whitelist(allow_guest=False)
def embed_file_in_pdf(invoice_name :str, print_format :str | None = None, letterhead:str | None = None, language :str | None = None):
    """
    Embed XML into a PDF using pikepdf.
    """
    try:

        # frappe.throw(app_path)/opt/zatca/frappe-bench/apps/zatca_erpgulf/zatca_erpgulf
        if not language:
            language = "en"  # Default language
        invoice_number = frappe.get_doc("Sales Invoice", invoice_name)
        # whitelisted method: without this, any logged-in user can render any
        # invoice's PDF and its embedded XML
        invoice_number.check_permission("read")

        safe_invoice_name = invoice_name.replace("/", "")

        cleared_xml_file_name = f"Cleared xml file {safe_invoice_name}.xml"
        reported_xml_file_name = f"Reported xml file {safe_invoice_name}.xml"


        attachments = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "Sales Invoice",
                "attached_to_name": invoice_name,
            },
            fields=["file_name", "file_url"],
        )

        xml_file = None

        for att in attachments:
            file_name = att["file_name"]

            if file_name == cleared_xml_file_name or file_name == reported_xml_file_name:
                xml_file = os.path.join(frappe.local.site_path, "private", "files", file_name)
                break

        if not xml_file:
            frappe.throw(_(f"No XML file found for the invoice {invoice_name}!"))
            
        # Find the XML file attachment
        # for attachment in attachments:
        #     file_name = attachment.get("file_name", None)
        #     if file_name == cleared_xml_file_name:
        #         xml_file = os.path.join(
        #             frappe.local.site, "private", "files", file_name
        #         )
        #         break
        #     elif file_name == reported_xml_file_name:
        #         xml_file = os.path.join(
        #             frappe.local.site, "private", "files", file_name
        #         )
        #         break
        # frappe.throw(str(attachments))
        if not xml_file:
            frappe.throw(_(f"No XML file found for the invoice {invoice_name}!"))
        input_pdf = generate_invoice_pdf(
            invoice_number,
            language=language,
            letterhead=letterhead,
            print_format=print_format,
        )

        final_name = f"{safe_invoice_name}-PDFA3.pdf"
        # Drop earlier PDF/A-3 copies first, otherwise Frappe appends a random
        # suffix (…-PDFA33d217d.pdf) and they pile up on the invoice. Must run
        # before the new file is written, since this deletes the file on disk.
        for old_file in frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "Sales Invoice",
                "attached_to_name": invoice_name,
                "file_name": ["like", f"{safe_invoice_name}-PDFA3%"],
            },
            pluck="name",
        ):
            frappe.delete_doc(
                "File", old_file, ignore_permissions=True, delete_permanently=True
            )

        # Build it in a temp dir, not in private/files. Frappe appends a random
        # suffix (…-PDFA3a75d10.pdf) whenever the target path already exists on
        # disk at insert time, so we must not pre-write it there.
        with tempfile.TemporaryDirectory() as tmp_dir:
            final_pdf = os.path.join(tmp_dir, final_name)
            # embed_file_in_pdf_1 does the attaching; do not pre-attach here,
            # or every invoice ends up with two identical XMLs.
            embed_file_in_pdf_1(
                input_pdf, xml_file, final_pdf, invoice_name, invoice_number.company
            )
            # nosemgrep: frappe-semgrep-rules.rules.security.frappe-security-file-traversal
            with open(final_pdf, "rb") as final_fh:
                pdf_bytes = final_fh.read()

        # the intermediate render is no longer needed
        if os.path.exists(input_pdf):
            os.unlink(input_pdf)

        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": final_name,
                "attached_to_doctype": "Sales Invoice",
                "attached_to_name": invoice_name,
                "is_private": 1,  # Make the file private
                "content": pdf_bytes,
            }
        )
        file_doc.insert(ignore_permissions=True)
        # frappe.msgprint(f"XML successfully embedded into: {input_pdf}")
        # frappe.throw(file_doc.file_url)
        return get_url(file_doc.file_url)

    except (pikepdf.PdfError, OSError) as e:
        # Log and re-raise. Swallowing these returned None to the caller, so
        # both the client and the on_submit hook thought it had succeeded.
        frappe.log_error(frappe.get_traceback(), "PDF-A3 XML Embed Error")
        frappe.throw(_("Could not build the PDF/A-3: {0}").format(str(e)))





def call_embed_pdf_on_submit(doc, method=None):
    """Run on Sales Invoice submit only if Company setting is enabled"""

    company_doc = frappe.get_doc("Company", doc.company)

    # Check if auto PDF-A3 creation is enabled
    if not company_doc.custom_auto_create_pdfa3:
        return

    print_format = company_doc.custom_print_format
    letterhead = company_doc.custom_letterhead
    language = company_doc.custom_language

    # Validate required fields
    if not print_format:
        frappe.msgprint(_("Company Print Format is not set. PDF-A3 creation skipped."))
        return

    if not language:
        frappe.msgprint(_("Company Language is not set. PDF-A3 creation skipped."))
        return

    try:
        embed_file_in_pdf(
            invoice_name=doc.name,
            print_format=print_format,
            letterhead=letterhead,
            language=language
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "PDF-A3 XML Embed Error")