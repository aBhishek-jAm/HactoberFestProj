"""InvoicePilot AI — Generate synthetic sample documents for demo and testing.

Creates sample PDF invoices and PNG receipts in the demo_samples/ directory
using PyMuPDF (fitz) and Pillow (PIL).
"""

import os
from pathlib import Path
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "demo_samples"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def create_invoice_acme_pdf():
    """Create a clean, professional PDF invoice for Acme Design Studio."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4 points

    # Header background banner
    page.draw_rect(fitz.Rect(0, 0, 595, 90), color=(0.08, 0.12, 0.2), fill=(0.08, 0.12, 0.2))

    # Header text
    page.insert_text(fitz.Point(50, 45), "INVOICE", fontsize=24, color=(1, 1, 1))
    page.insert_text(fitz.Point(50, 68), "InvoicePilot Verified Sample Document", fontsize=10, color=(0.7, 0.75, 0.85))

    # Vendor Details (Left)
    page.insert_text(fitz.Point(50, 125), "From:", fontsize=11, color=(0.4, 0.45, 0.5))
    page.insert_text(fitz.Point(50, 142), "Acme Design Studio LLC", fontsize=13, color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(50, 158), "123 Creative Avenue, Suite 400", fontsize=10, color=(0.3, 0.3, 0.3))
    page.insert_text(fitz.Point(50, 172), "San Francisco, CA 94105, USA", fontsize=10, color=(0.3, 0.3, 0.3))
    page.insert_text(fitz.Point(50, 186), "billing@acmedesign.example.com", fontsize=10, color=(0.3, 0.3, 0.3))

    # Invoice Metadata (Right)
    page.insert_text(fitz.Point(360, 125), "Invoice Details:", fontsize=11, color=(0.4, 0.45, 0.5))
    page.insert_text(fitz.Point(360, 142), "Invoice #: INV-2026-0042", fontsize=11, color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(360, 158), "Date: 2026-10-01", fontsize=10, color=(0.2, 0.2, 0.2))
    page.insert_text(fitz.Point(360, 172), "Due Date: 2026-10-31", fontsize=10, color=(0.2, 0.2, 0.2))
    page.insert_text(fitz.Point(360, 186), "Payment Status: UNPAID", fontsize=10, color=(0.8, 0.2, 0.1))

    # Bill To Box
    page.draw_rect(fitz.Rect(50, 215, 545, 275), color=(0.9, 0.92, 0.95), fill=(0.96, 0.97, 0.98))
    page.insert_text(fitz.Point(65, 235), "BILL TO:", fontsize=9, color=(0.4, 0.45, 0.5))
    page.insert_text(fitz.Point(65, 252), "Freelance Corp / Side Hustle Labs", fontsize=12, color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(65, 266), "456 Side Hustle Lane, Austin, TX 78701", fontsize=10, color=(0.3, 0.3, 0.3))

    # Table Header
    page.draw_rect(fitz.Rect(50, 305, 545, 330), color=(0.15, 0.2, 0.3), fill=(0.15, 0.2, 0.3))
    page.insert_text(fitz.Point(65, 322), "Description", fontsize=10, color=(1, 1, 1))
    page.insert_text(fitz.Point(320, 322), "Qty", fontsize=10, color=(1, 1, 1))
    page.insert_text(fitz.Point(390, 322), "Unit Price", fontsize=10, color=(1, 1, 1))
    page.insert_text(fitz.Point(480, 322), "Amount (USD)", fontsize=10, color=(1, 1, 1))

    # Table Rows
    rows = [
        ("Web Application UX/UI Redesign Sprint", "1", "$2,400.00", "$2,400.00"),
        ("Design System Token & Component Tokens", "1", "$850.00", "$850.00"),
        ("Interactive Prototype & Motion Design", "1", "$600.00", "$600.00"),
        ("Developer Handoff Documentation & Specs", "1", "$350.00", "$350.00"),
    ]

    y = 355
    for i, (desc, qty, unit, amt) in enumerate(rows):
        if i % 2 == 1:
            page.draw_rect(fitz.Rect(50, y - 16, 545, y + 8), color=None, fill=(0.97, 0.98, 0.99))
        page.insert_text(fitz.Point(65, y), desc, fontsize=10, color=(0.15, 0.15, 0.15))
        page.insert_text(fitz.Point(325, y), qty, fontsize=10, color=(0.2, 0.2, 0.2))
        page.insert_text(fitz.Point(395, y), unit, fontsize=10, color=(0.2, 0.2, 0.2))
        page.insert_text(fitz.Point(485, y), amt, fontsize=10, color=(0.15, 0.15, 0.15))
        y += 28

    # Totals Section
    page.draw_line(fitz.Point(350, y + 5), fitz.Point(545, y + 5), color=(0.8, 0.8, 0.8))
    y += 25
    page.insert_text(fitz.Point(360, y), "Subtotal:", fontsize=10, color=(0.3, 0.3, 0.3))
    page.insert_text(fitz.Point(485, y), "$4,200.00", fontsize=10, color=(0.2, 0.2, 0.2))
    y += 20
    page.insert_text(fitz.Point(360, y), "Tax (8.25%):", fontsize=10, color=(0.3, 0.3, 0.3))
    page.insert_text(fitz.Point(485, y), "$346.50", fontsize=10, color=(0.2, 0.2, 0.2))
    y += 25
    page.draw_rect(fitz.Rect(350, y - 16, 545, y + 14), color=(0.08, 0.12, 0.2), fill=(0.08, 0.12, 0.2))
    page.insert_text(fitz.Point(360, y), "Total Due (USD):", fontsize=11, color=(1, 1, 1))
    page.insert_text(fitz.Point(480, y), "$4,546.50", fontsize=12, color=(1, 1, 1))

    # Notes & Payment info
    y += 60
    page.insert_text(fitz.Point(50, y), "Payment Instructions:", fontsize=10, color=(0.2, 0.2, 0.2))
    page.insert_text(fitz.Point(50, y + 16), "Direct ACH or Wire: Bank of America | Routing: 121000358 | Account: 987654321", fontsize=9, color=(0.4, 0.4, 0.4))
    page.insert_text(fitz.Point(50, y + 30), "Thank you for partnering with Acme Design Studio!", fontsize=9, color=(0.4, 0.4, 0.4))

    out_path = OUTPUT_DIR / "sample_invoice_01_acme_design.pdf"
    doc.save(str(out_path))
    doc.close()
    print(f"Created: {out_path}")


def create_invoice_gst_inr_pdf():
    """Create a GST compliant tax invoice in INR."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    page.draw_rect(fitz.Rect(0, 0, 595, 75), color=(0.05, 0.35, 0.25), fill=(0.05, 0.35, 0.25))
    page.insert_text(fitz.Point(50, 42), "TAX INVOICE (GST)", fontsize=22, color=(1, 1, 1))
    page.insert_text(fitz.Point(50, 60), "GSTIN: 29AADCG1234R1ZP | HSN/SAC: 998314", fontsize=9, color=(0.85, 0.95, 0.9))

    # Vendor info
    page.insert_text(fitz.Point(50, 110), "Supplier:", fontsize=10, color=(0.4, 0.45, 0.5))
    page.insert_text(fitz.Point(50, 126), "Global Tech Solutions Private Limited", fontsize=12, color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(50, 140), "42 MG Road, Bengaluru, Karnataka 560001", fontsize=9, color=(0.3, 0.3, 0.3))
    page.insert_text(fitz.Point(50, 154), "support@globaltechsolutions.example.in", fontsize=9, color=(0.3, 0.3, 0.3))

    # Meta
    page.insert_text(fitz.Point(360, 110), "Invoice Details:", fontsize=10, color=(0.4, 0.45, 0.5))
    page.insert_text(fitz.Point(360, 126), "Invoice No: GST/2026/0198", fontsize=11, color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(360, 140), "Date: 15/09/2026", fontsize=9, color=(0.2, 0.2, 0.2))
    page.insert_text(fitz.Point(360, 154), "Due Date: 15/10/2026", fontsize=9, color=(0.2, 0.2, 0.2))

    # Customer
    page.draw_rect(fitz.Rect(50, 175, 545, 230), color=(0.9, 0.93, 0.9), fill=(0.96, 0.98, 0.96))
    page.insert_text(fitz.Point(65, 195), "BILL TO:", fontsize=9, color=(0.4, 0.45, 0.5))
    page.insert_text(fitz.Point(65, 210), "IndieDevs Technologies LLP", fontsize=11, color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(65, 222), "88 Koramangala 4th Block, Bengaluru 560034", fontsize=9, color=(0.3, 0.3, 0.3))

    # Table
    page.draw_rect(fitz.Rect(50, 255, 545, 278), color=(0.05, 0.35, 0.25), fill=(0.05, 0.35, 0.25))
    page.insert_text(fitz.Point(65, 271), "Service Description", fontsize=9, color=(1, 1, 1))
    page.insert_text(fitz.Point(340, 271), "SAC", fontsize=9, color=(1, 1, 1))
    page.insert_text(fitz.Point(400, 271), "Rate (INR)", fontsize=9, color=(1, 1, 1))
    page.insert_text(fitz.Point(480, 271), "Amount (INR)", fontsize=9, color=(1, 1, 1))

    items = [
        ("Cloud Infrastructure Architecture Setup", "998314", "45,000.00", "45,000.00"),
        ("Microservice Performance Tuning & Audit", "998314", "30,000.00", "30,000.00"),
    ]

    y = 300
    for desc, sac, rate, amt in items:
        page.insert_text(fitz.Point(65, y), desc, fontsize=9, color=(0.15, 0.15, 0.15))
        page.insert_text(fitz.Point(340, y), sac, fontsize=9, color=(0.2, 0.2, 0.2))
        page.insert_text(fitz.Point(400, y), rate, fontsize=9, color=(0.2, 0.2, 0.2))
        page.insert_text(fitz.Point(480, y), amt, fontsize=9, color=(0.15, 0.15, 0.15))
        y += 25

    # GST Calculation
    page.draw_line(fitz.Point(330, y + 5), fitz.Point(545, y + 5), color=(0.8, 0.8, 0.8))
    y += 24
    page.insert_text(fitz.Point(340, y), "Taxable Amount:", fontsize=9, color=(0.3, 0.3, 0.3))
    page.insert_text(fitz.Point(480, y), "INR 75,000.00", fontsize=9, color=(0.2, 0.2, 0.2))
    y += 18
    page.insert_text(fitz.Point(340, y), "CGST @ 9%:", fontsize=9, color=(0.3, 0.3, 0.3))
    page.insert_text(fitz.Point(480, y), "INR  6,750.00", fontsize=9, color=(0.2, 0.2, 0.2))
    y += 18
    page.insert_text(fitz.Point(340, y), "SGST @ 9%:", fontsize=9, color=(0.3, 0.3, 0.3))
    page.insert_text(fitz.Point(480, y), "INR  6,750.00", fontsize=9, color=(0.2, 0.2, 0.2))
    y += 24
    page.draw_rect(fitz.Rect(330, y - 14, 545, y + 12), color=(0.05, 0.35, 0.25), fill=(0.05, 0.35, 0.25))
    page.insert_text(fitz.Point(340, y), "Total Invoice Value:", fontsize=10, color=(1, 1, 1))
    page.insert_text(fitz.Point(475, y), "INR 88,500.00", fontsize=11, color=(1, 1, 1))

    out_path = OUTPUT_DIR / "sample_invoice_02_global_tech_gst.pdf"
    doc.save(str(out_path))
    doc.close()
    print(f"Created: {out_path}")


def create_receipt_cloudstack_png():
    """Create a digital receipt PNG image for software SaaS expense."""
    width, height = 700, 800
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Top Header
    draw.rectangle([0, 0, width, 110], fill=(30, 41, 59))
    draw.text((40, 25), "CloudStack Technologies Inc.", fill=(255, 255, 255))
    draw.text((40, 50), "Payment Receipt - Thank You For Your Subscription", fill=(203, 213, 225))
    draw.text((40, 75), "support@cloudstack.example.com | https://cloudstack.example.com", fill=(148, 163, 184))

    # Meta
    y = 140
    draw.text((40, y), "Receipt Number: REC-78234", fill=(30, 41, 59))
    draw.text((420, y), "Date: 2026-09-15", fill=(30, 41, 59))
    y += 28
    draw.text((40, y), "Billed To: Freelance Studio", fill=(71, 85, 105))
    draw.text((420, y), "Payment Method: Visa ending 4242", fill=(71, 85, 105))
    y += 28
    draw.text((40, y), "Status: PAID (Approved)", fill=(16, 185, 129))

    # Divider
    y += 35
    draw.line([(40, y), (660, y)], fill=(226, 232, 240), width=2)
    y += 25

    # Table Header
    draw.rectangle([(40, y), (660, y + 35)], fill=(241, 245, 249))
    draw.text((55, y + 10), "Item / Description", fill=(15, 23, 42))
    draw.text((540, y + 10), "Amount", fill=(15, 23, 42))
    y += 50

    # Items
    items = [
        ("CloudStack Pro Developer Plan (Monthly)", "$49.99"),
        ("Additional High-IOPS Cloud Storage (100GB)", "$19.99"),
        ("Automated Daily Backup Add-on", "$9.99"),
    ]
    for desc, amt in items:
        draw.text((55, y), desc, fill=(51, 65, 85))
        draw.text((540, y), amt, fill=(15, 23, 42))
        y += 38

    # Totals
    y += 15
    draw.line([(350, y), (660, y)], fill=(226, 232, 240), width=1)
    y += 20
    draw.text((360, y), "Subtotal:", fill=(100, 116, 139))
    draw.text((540, y), "$79.97", fill=(51, 65, 85))
    y += 28
    draw.text((360, y), "Tax (0.00% Software Exemption):", fill=(100, 116, 139))
    draw.text((540, y), "$0.00", fill=(51, 65, 85))
    y += 32
    draw.rectangle([(350, y), (660, y + 42)], fill=(248, 250, 252), outline=(203, 213, 225))
    draw.text((365, y + 12), "Total Amount Charged:", fill=(15, 23, 42))
    draw.text((535, y + 12), "$79.97 USD", fill=(15, 23, 42))

    # Footer
    y = height - 90
    draw.line([(40, y), (660, y)], fill=(226, 232, 240), width=1)
    draw.text((40, y + 20), "This receipt confirms your monthly subscription payment.", fill=(148, 163, 184))
    draw.text((40, y + 40), "InvoicePilot AI Sample Synthetic Receipt - No Financial Value", fill=(148, 163, 184))

    out_path = OUTPUT_DIR / "sample_receipt_03_cloudstack_pro.png"
    img.save(str(out_path))
    print(f"Created: {out_path}")


def create_receipt_coffee_png():
    """Create a cafe receipt PNG image for business meeting expense."""
    width, height = 500, 750
    img = Image.new("RGB", (width, height), color=(250, 250, 248))
    draw = ImageDraw.Draw(img)

    y = 30
    draw.text((150, y), "*** BLUE BOTTLE COFFEE ***", fill=(20, 20, 20))
    y += 24
    draw.text((140, y), "Coworking & Specialty Roasters", fill=(80, 80, 80))
    y += 20
    draw.text((160, y), "San Francisco, CA 94103", fill=(80, 80, 80))
    y += 20
    draw.text((170, y), "Tel: (415) 555-0199", fill=(80, 80, 80))

    y += 30
    draw.text((30, y), "Order #2847", fill=(40, 40, 40))
    draw.text((320, y), "Date: 2026-10-08", fill=(40, 40, 40))
    y += 20
    draw.text((30, y), "Server: Alex M.", fill=(60, 60, 60))
    draw.text((320, y), "Time: 14:22 PST", fill=(60, 60, 60))

    y += 25
    draw.text((30, y), "--------------------------------------------------", fill=(150, 150, 150))
    y += 20
    draw.text((30, y), "ITEM                          QTY       AMOUNT", fill=(30, 30, 30))
    y += 20
    draw.text((30, y), "--------------------------------------------------", fill=(150, 150, 150))

    items = [
        ("Oat Milk Latte 12oz", "2", "$13.00"),
        ("Cold Brew Single Origin", "1", "$6.50"),
        ("Almond Croissant", "2", "$11.00"),
        ("Day Coworking Pass", "1", "$25.00"),
    ]

    for name, qty, amt in items:
        y += 25
        draw.text((30, y), name, fill=(30, 30, 30))
        draw.text((260, y), qty, fill=(30, 30, 30))
        draw.text((380, y), amt, fill=(30, 30, 30))

    y += 35
    draw.text((30, y), "--------------------------------------------------", fill=(150, 150, 150))
    y += 25
    draw.text((220, y), "SUBTOTAL:        $55.50", fill=(30, 30, 30))
    y += 22
    draw.text((220, y), "TAX (8.5%):       $4.72", fill=(30, 30, 30))
    y += 22
    draw.text((220, y), "TIP:              $8.00", fill=(30, 30, 30))
    y += 25
    draw.text((220, y), "TOTAL (USD):     $68.22", fill=(0, 0, 0))

    y += 35
    draw.text((30, y), "--------------------------------------------------", fill=(150, 150, 150))
    y += 25
    draw.text((30, y), "Card: ************9102 (Apple Pay)", fill=(60, 60, 60))
    y += 20
    draw.text((30, y), "Auth Code: 094812 | Status: APPROVED", fill=(60, 60, 60))

    y += 40
    draw.text((120, y), "Thank you for visiting! Keep this receipt", fill=(100, 100, 100))
    draw.text((150, y + 20), "for tax and expense reporting.", fill=(100, 100, 100))

    out_path = OUTPUT_DIR / "sample_receipt_04_cafe_meeting.png"
    img.save(str(out_path))
    print(f"Created: {out_path}")


if __name__ == "__main__":
    create_invoice_acme_pdf()
    create_invoice_gst_inr_pdf()
    create_receipt_cloudstack_png()
    create_receipt_coffee_png()
    print("All sample synthetic documents generated in demo_samples/")
