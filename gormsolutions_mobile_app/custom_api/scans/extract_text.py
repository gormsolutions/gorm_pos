import pytesseract
from PIL import Image
import frappe
import os

@frappe.whitelist()
def extract_text_from_image(docname):
    doc = frappe.get_doc("Image OCR", docname)
    
    if not doc.image:
        frappe.throw("Please upload an image.")

    # Get full path of the uploaded image
    file_url = doc.image
    file_path = frappe.get_site_path("public", file_url.lstrip("/"))

    # Load the image
    image = Image.open(file_path)

    # Run OCR
    text = pytesseract.image_to_string(image)

    # Update the doc with extracted text
    doc.extracted_text = text
    doc.save()
    return text
