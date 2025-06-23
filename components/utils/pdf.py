from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import ImageReader
from io import BytesIO
import qrcode
import sqlite3
import os
import sys
from datetime import datetime

# Optional: for converting number to words
try:
    from num2words import num2words
except ImportError:
    def num2words(n):
        return f"{n} Only"

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.datamanager.databasemanger import DatabaseManager


def generate_invoice_pdf_stream(job_id: int,  status:str,  base_url="http://localhost:8501/repair_status?" ) -> BytesIO:
    """
    Generate invoice PDF for a job with improved error handling
    """
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()

        # First, check if job exists
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE id = ?", (job_id,))
        if cursor.fetchone()[0] == 0:
            raise ValueError(f"No job found with ID {job_id}")

        # Fetch job + customer + store info + dates
        cursor.execute('''
            SELECT j.id, j.device_type, j.device_model, j.problem_description, 
                   j.actual_cost, j.status, j.created_at, j.completed_at,
                   c.name, c.address, c.phone,
                   s.name, s.location, s.phone
            FROM jobs j
            JOIN customers c ON j.customer_id = c.id
            LEFT JOIN stores s ON j.store_id = s.id
            WHERE j.id = ?
        ''', (job_id,))
        
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"No complete job data found for job_id {job_id}")

        (
            job_id, device_type, device_model, problem, cost, status,
            created_at, completed_at,
            cust_name, cust_addr, cust_phone,
            store_name, store_addr, store_phone
        ) = row

        # Handle None values with better defaults
        device_type = device_type or "Device"
        device_model = device_model or "N/A"
        problem = problem or "N/A"
        cost = cost or 0
        cust_name = cust_name or "Customer"
        cust_addr = cust_addr or "N/A"
        cust_phone = cust_phone or "N/A"
        store_name = store_name or "RepairPro"
        store_addr = store_addr or "Store Address"
        store_phone = store_phone or "Store Phone"

        # Format dates safely
        try:
            issue_date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d") if created_at else "N/A"
        except (ValueError, TypeError):
            issue_date = "N/A"
            
        try:
            delivery_date = datetime.strptime(completed_at, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d") if completed_at else "Pending"
        except (ValueError, TypeError):
            delivery_date = "Pending"

        # Generate QR code
        qr_url = f"{base_url}job_id={job_id}"
        qr_img = qrcode.make(qr_url)
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        qr_reader = ImageReader(qr_buffer)

        # Create PDF
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(30, height - 50, store_name)
        c.setFont("Helvetica", 10)
        c.drawString(30, height - 65, store_addr)
        c.drawString(30, height - 80, f"Phone: {store_phone}")
        
        # Add QR code with error handling
        try:
            c.drawImage(qr_reader, width - 110, height - 120, 80, 80)
        except Exception as e:
            print(f"Warning: Could not add QR code to PDF: {e}")

        # Invoice Info
        c.setFont("Helvetica-Bold", 14)
        c.drawString(30, height - 100, f"INVOICE #{job_id}")
        c.setFont("Helvetica", 10)
        c.drawString(30, height - 115, f"Date: {issue_date}")

        # Customer Info
        c.setFont("Helvetica-Bold", 11)
        c.drawString(30, height - 140, "Bill To:")
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 155, f"Name: {cust_name}")
        c.drawString(50, height - 170, f"Address: {cust_addr}")
        c.drawString(50, height - 185, f"Phone: {cust_phone}")

        # Device & Problem Details Table
        device_info = f"{device_type} {device_model}".strip()
        table1_data = [
            ["Device", "Problem Description", "Delivery Date"],
            [device_info, problem[:50] + "..." if len(problem) > 50 else problem, delivery_date]
        ]
        
        table1 = Table(table1_data, colWidths=[150, 250, 100])
        table1.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        table1.wrapOn(c, width, height)
        table1.drawOn(c, 30, height - 250)

        # Cost Breakdown Table
        table2_data = [
            ["Service Description", "Amount"],
            [f"Repair: {problem[:30]}..." if len(problem) > 30 else f"Repair: {problem}", f"${cost:.2f}"]
        ]
        
        table2 = Table(table2_data, colWidths=[350, 150])
        table2.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        table2.wrapOn(c, width, height)
        table2.drawOn(c, 30, height - 320)

        # Totals section
        c.setFont("Helvetica", 10)
        c.drawRightString(width - 180, height - 350, "Subtotal:")
        c.drawRightString(width - 80, height - 350, f"${cost:.2f}")
        c.drawRightString(width - 180, height - 365, "Tax:")
        c.drawRightString(width - 80, height - 365, "$0.00")
        
        # Total line
        c.setFont("Helvetica-Bold", 12)
        c.line(width - 500, height - 375, width - 30, height - 375)
        c.drawRightString(width - 180, height - 390, "TOTAL:")
        c.drawRightString(width - 80, height - 390, f"${cost:.2f}")

        # Amount in words
        c.setFont("Helvetica", 10)
        c.drawString(30, height - 420, "Total Amount in Words:")
        c.setFont("Helvetica-Bold", 10)
        try:
            amount_words = num2words(int(cost)).title() + " Dollars Only"
        except:
            amount_words = f"{cost} Only"
        c.drawString(30, height - 435, amount_words)

        # Payment status
        if status == "Completed":
                c.setFont("Helvetica", 10)
                c.drawString(30, height - 460, f"Status: {status}")
                c.drawString(30, height - 475, "Payment: PAID" if status == "Completed" else "Payment: PENDING")

                # Footer
                c.line(30, height - 500, width - 30, height - 500)
                c.setFont("Helvetica", 8)
                c.drawString(30, height - 515, "Thank you for your business!")
                
                # Signature line
                c.line(width - 200, height - 540, width - 50, height - 540)
                c.drawString(width - 150, height - 555, "Authorized Signature")

        c.save()
        buffer.seek(0)
        
        # Close database connection
        conn.close()
        
        return buffer
        
    except Exception as e:
        print(f"Error generating PDF for job {job_id}: {e}")
        # Create a simple error PDF
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 100, "Error Generating Invoice")
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 130, f"Job ID: {job_id}")
        c.drawString(50, height - 150, f"Error: {str(e)}")
        c.drawString(50, height - 170, "Please contact support for assistance.")
        
        c.save()
        buffer.seek(0)
        return buffer