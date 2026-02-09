"""New function for print pdf a3"""

from datetime import datetime
import os
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
    frappe.local.lang = language

    # Generate HTML content for the invoice
    html = frappe.get_print(
        doctype="Sales Invoice",
        name=invoice_name,  # Use the invoice's name directly
        print_format=print_format,  # Use the selected print format
        no_letterhead=not bool(letterhead),  # Use letterhead only if specified
        letterhead=letterhead,  # Specify the letterhead if provided
    )

    # Revert back to the original language
    frappe.local.lang = original_language

    # Generate PDF content from the HTML
    pdf_content = get_pdf(html)

    # Set the path for saving the generated PDF
    site_path = frappe.local.site  # Get the site path
    file_name = f"{invoice_name}.pdf"
    file_path = os.path.join(site_path, "private", "files", file_name)

    # Write the PDF content to the file
    with open(file_path, "wb") as pdf_file:
        pdf_file.write(pdf_content)

    # Return the path of the generated PDF file
    return file_path


def embed_file_in_pdf_1(input_pdf, xml_file, output_pdf):
    """embed the pdf file"""
    app_path = frappe.get_app_path("zatca_erpgulf")
    icc_path = app_path + "/sRGB.icc"

    # frappe.throw(icc_path)
    with pikepdf.open(input_pdf, allow_overwriting_input=True) as pdf:
        # Open metadata for editing
        with pdf.open_metadata() as metadata:
            metadata["pdf:Trapped"] = "False"
            metadata["dc:creator"] = ["John Doe"]  # Example author name
            metadata["dc:title"] = "PDF/A-3 Example"
            metadata["dc:description"] = (
                "A sample PDF/A-3 compliant document with embedded XML."
            )
            metadata["dc:date"] = datetime.now().isoformat()


        # Create XMP metadata
        xmp_metadata = f"""<?xpacket begin='' id='W5M0MpCehiHzreSzNTczkc9d'?>
        <x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP toolkit 2.9.1-13, framework 1.6">
            <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
                <rdf:Description rdf:about=""
                    xmlns:dc="http://purl.org/dc/elements/1.1/"
                    xmlns:xmp="http://ns.adobe.com/xap/1.0/"
                    xmlns:pdf="http://ns.adobe.com/pdf/1.3/"
                    xmlns:xmpMM="http://ns.adobe.com/xap/1.0/mm/"
                    xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/">
                    <pdf:Producer>pikepdf</pdf:Producer>
                    <pdf:Trapped>False</pdf:Trapped>
                    <dc:creator>
                        <rdf:Seq>
                            <rdf:li>John Doe</rdf:li>
                        </rdf:Seq>
                    </dc:creator>
                    <dc:title>
                        <rdf:Alt>
                            <rdf:li xml:lang="x-default">PDF/A-3 Example</rdf:li>
                        </rdf:Alt>
                    </dc:title>
                    <dc:description>
                        <rdf:Alt>
                            <rdf:li xml:lang="x-default">A sample PDF/A-3 compliant document with embedded XML.</rdf:li>
                        </rdf:Alt>
                    </dc:description>
                    <xmp:CreateDate>{datetime.now().isoformat()}</xmp:CreateDate>
                    <pdfaid:part>3</pdfaid:part>
                    <pdfaid:conformance>B</pdfaid:conformance>
                </rdf:Description>
            </rdf:RDF>
        </x:xmpmeta>
        <?xpacket end="w"?>"""

        metadata_bytes = xmp_metadata.encode("utf-8")

        # Ensure the PDF has the necessary PDF/A-3 identifiers
        if "/StructTreeRoot" not in pdf.Root:
            pdf.Root["/StructTreeRoot"] = pikepdf.Dictionary()
        pdf.Root["/Metadata"] = pdf.make_stream(metadata_bytes)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary({"/Marked": True})
        pdf.Root["/Lang"] = pikepdf.String("en-US")

        # Embed the XML file
        with open(xml_file, "rb") as xml_f:
            xml_data = xml_f.read()

        embedded_file_stream = pdf.make_stream(xml_data)
        embedded_file_stream.Type = "/EmbeddedFile"
        embedded_file_stream.Subtype = "/application/xml"

        embedded_file_dict = pikepdf.Dictionary(
            {
                "/Type": "/Filespec",
                "/F": pikepdf.String(os.path.basename(xml_file)),
                "/EF": pikepdf.Dictionary({"/F": embedded_file_stream}),
                "/Desc": "XML Invoice",
            }
        )

        if "/Names" not in pdf.Root:
            pdf.Root.Names = pikepdf.Dictionary()
        if "/EmbeddedFiles" not in pdf.Root.Names:
            pdf.Root.Names.EmbeddedFiles = pikepdf.Dictionary()
        if "/Names" not in pdf.Root.Names.EmbeddedFiles:
            pdf.Root.Names.EmbeddedFiles.Names = pikepdf.Array()

        pdf.Root.Names.EmbeddedFiles.Names.append(
            pikepdf.String(os.path.basename(xml_file))
        )
        pdf.Root.Names.EmbeddedFiles.Names.append(embedded_file_dict)

        # Set OutputIntent
        with open(icc_path, "rb") as icc_file:
            icc_data = icc_file.read()
            output_intent_dict = pikepdf.Dictionary(
                {
                    "/Type": "/OutputIntent",
                    "/S": "/GTS_PDFA1",
                    "/OutputConditionIdentifier": "sRGB",
                    "/Info": "sRGB IEC61966-2.1",
                    "/DestOutputProfile": pdf.make_stream(icc_data),
                }
            )
            if "/OutputIntents" not in pdf.Root:
                pdf.Root["/OutputIntents"] = pikepdf.Array([output_intent_dict])
            else:
                pdf.Root.OutputIntents.append(output_intent_dict)

        # Add PDF/A-3 compliance information
        pdf.Root["/GTS_PDFA1"] = pikepdf.Name("/PDF/A-3B")
        pdf.docinfo["/GTS_PDFA1"] = "PDF/A-3B"
        pdf.docinfo["/Title"] = "PDF/A-3 Example"
        pdf.docinfo["/Author"] = "John Doe"  # Example author name
        pdf.docinfo["/Subject"] = "PDF/A-3 Example with Embedded XML"
        pdf.docinfo["/Creator"] = "Python pikepdf Library"
        pdf.docinfo["/Producer"] = "pikepdf"
        pdf.docinfo["/CreationDate"] = datetime.now().isoformat()

        # Save the PDF as PDF/A-3
        pdf.save(output_pdf)


@frappe.whitelist(allow_guest=False)
def embed_file_in_pdf(invoice_name, print_format=None, letterhead=None, language=None):
    """
    Embed XML into a PDF using pikepdf.
    """
    try:

        # frappe.throw(app_path)/opt/zatca/frappe-bench/apps/zatca_erpgulf/zatca_erpgulf
        if not language:
            language = "en"  # Default language
        invoice_number = frappe.get_doc("Sales Invoice", invoice_name)

        xml_file = None
        cleared_xml_file_name = "Cleared xml file " + invoice_name + ".xml"
        reported_xml_file_name = "Reported xml file " + invoice_name + ".xml"
        attachments = frappe.get_all(
            "File", filters={"attached_to_name": invoice_name}, fields=["file_name"]
        )

        # Find the XML file attachment
        for attachment in attachments:
            file_name = attachment.get("file_name", None)
            if file_name == cleared_xml_file_name:
                xml_file = os.path.join(
                    frappe.local.site, "private", "files", file_name
                )
                break
            elif file_name == reported_xml_file_name:
                xml_file = os.path.join(
                    frappe.local.site, "private", "files", file_name
                )
                break

        if not xml_file:
            frappe.throw(f"No XML file found for the invoice {invoice_name}!")
        input_pdf = generate_invoice_pdf(
            invoice_number,
            language=language,
            letterhead=letterhead,
            print_format=print_format,
        )

        # final_pdf = frappe.local.site + "/private/files/" + invoice_name + "output.pdf"
        final_pdf = (
            frappe.local.site + "/private/files/PDF-A3 " + invoice_name + " output.pdf"
        )
        # frappe.msgprint(f"Embedding XML into: {input_pdf}")
        with pikepdf.Pdf.open(input_pdf, allow_overwriting_input=True) as pdf:
            with open(xml_file, "rb") as xml_attachment:
                pdf.attachments["invoice.xml"] = xml_attachment.read()
            pdf.save(input_pdf)
            embed_file_in_pdf_1(input_pdf, xml_file, final_pdf)

            file_doc = frappe.get_doc(
                {
                    "doctype": "File",
                    "file_url": "/private/files/PDF-A3 " + invoice_name + " output.pdf",
                    "attached_to_doctype": "Sales Invoice",
                    "attached_to_name": invoice_name,
                    "is_private": 1,  # Make the file private
                }
            )
        file_doc.insert(ignore_permissions=True)
        # frappe.msgprint(f"XML successfully embedded into: {input_pdf}")
        # frappe.throw(file_doc.file_url)
        return get_url(file_doc.file_url)

    except pikepdf.PdfError as e:
        frappe.msgprint(_(f"Error processing the PDF: {e}"))
    except FileNotFoundError as e:
        frappe.msgprint(_(f"File not found: {e}"))
    except IOError as e:
        frappe.msgprint(_(f"I/O error: {e}"))  # Step 1: Embed the XML into the input
