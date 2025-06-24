import sqlite3
import smtplib
from io import BytesIO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import sys 
import os 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.datamanager.databasemanger import DatabaseManager
from components.utils.pdf import generate_invoice_pdf_stream 

def send_job_status_email(conn: sqlite3.Connection, job_id: int, base_url="https://jayanth119-refactored-jobsheet-main-vtllnj.streamlit.app//repair_status?job_id="):
    """
    Sends a repair job status email with a PDF invoice if completed.

    Args:
        conn (sqlite3.Connection): Active DB connection
        job_id (int): Job ID to send email for
        base_url (str): Base URL to generate repair tracking link
    """
    # --- SMTP CONFIG ---
    SMTP_SERVER   = "smtp.gmail.com"
    SMTP_PORT     = 587
    SENDER_EMAIL  = "jayanthunofficial@gmail.com"
    SENDER_PASS   = "qxhx qwhd aobk xgqf"  # App password

    # --- Fetch job + customer data ---
    cursor = conn.cursor()
    cursor.execute("""
        SELECT j.status,
               j.device_type,
               j.device_model,
               j.problem_description,
               j.created_at,
               c.name,
               c.email
          FROM jobs j
     LEFT JOIN customers c ON j.customer_id = c.id
         WHERE j.id = ?
    """, (job_id,))
    
    row = cursor.fetchone()
    if not row:
        print(f"[❌] No job found with ID = {job_id}")
        return

    status, device_type, device_model, problem, created_at, cust_name, cust_email = row

    if not cust_email:
        print(f"[⚠️] No email available for customer: {cust_name}")
        return

    # --- Generate email content ---
    subject = f"🔧 Repair Update: {device_type} ({device_model}) - Job #{job_id}"
    status_link = f"{base_url}{job_id}"

    html = ""
    plain_text = f"Hello {cust_name},\n\nYour repair job #{job_id} is now '{status}'.\nTrack here: {status_link}"

    if status == "New":
        html = f"""
        <p>Dear {cust_name},</p>
        <p>We’ve <strong>received</strong> your <em>{device_type} ({device_model})</em> with the issue: “{problem}” on {created_at}.</p>
        <p>We’ll notify you once our technician begins work.</p>
        <p><a href="{status_link}">Track Repair Status</a></p>
        """
    elif status == "In Progress":
        html = f"""
        <p>Hi {cust_name},</p>
        <p>Your <em>{device_type} ({device_model})</em> is <strong>currently being repaired</strong>.</p>
        <p>We'll update you once it's completed.</p>
        <p><a href="{status_link}">Track Repair Status</a></p>
        """
    elif status == "Completed":
        html = f"""
        <p>Hi {cust_name},</p>
        <p>🎉 Great news! Your <strong>{device_type} ({device_model})</strong> repair is complete.</p>
        <p>You may collect your device at your convenience.</p>
        <p><strong>Invoice attached.</strong></p>
        <p><a href="{status_link}">Track Repair Status</a></p>
        <p>Thank you for choosing us!</p>
        """
    else:
        html = f"""
        <p>Hi {cust_name},</p>
        <p>Your repair job status is: <strong>{status}</strong></p>
        <p><a href="{status_link}">Track Repair Status</a></p>
        """

    # --- Build MIME email ---
    msg = MIMEMultipart("mixed")
    msg["From"] = SENDER_EMAIL
    msg["To"] = cust_email
    msg["Subject"] = subject

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html, "html"))

    # --- If status is "Completed", attach PDF ---
    if status == "Completed":
        try:
            pdf_buffer = generate_invoice_pdf_stream(job_id,status=status)
            invoice = MIMEApplication(pdf_buffer.read(), _subtype="pdf")
            invoice.add_header("Content-Disposition", "attachment", filename=f"invoice_job_{job_id}.pdf")
            msg.attach(invoice)
            print("✅ Attached PDF invoice.")
        except Exception as e:
            print(f"[⚠️] Failed to attach PDF invoice: {e}")

    # --- Send email ---
    try:
        smtp = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        smtp.starttls()
        smtp.login(SENDER_EMAIL, SENDER_PASS)
        smtp.sendmail(SENDER_EMAIL, [cust_email], msg.as_string())
        smtp.quit()
        print(f"✅ Email sent to {cust_email}")
    except Exception as e:
        print(f"[❌] Failed to send email: {e}")
