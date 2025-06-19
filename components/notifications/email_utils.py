import sqlite3
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_job_status_email(conn: str, job_id: int):
    """
    Fetch a job by ID from the given SQLite DB and email the customer
    an update based on the job's status.

    Args:
        conn (str): The SQLite DB connection string.
        job_id (int): The ID of the job to notify about.
    """
    # --- SMTP CONFIG ---
    SMTP_SERVER   = "smtp.gmail.com"
    SMTP_PORT     = 587
    SENDER_EMAIL  = "jayanthunofficial@gmail.com"
    SENDER_PASS   = "qxhx qwhd aobk xgqf"  # replace with your Gmail app password

    # --- Connect & fetch ---
    cur  = conn.cursor()
    cur.execute("""
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
    row = cur.fetchone()
    

    if not row:
        print(f"[!] No job found with ID={job_id}")
        return

    status, device_type, device_model, problem, created_at, cust_name, cust_email = row
    if not cust_email:
        print(f"[!] Customer '{cust_name}' has no email on file.")
        return

    # --- Prepare message based on status ---
    subject = f"Update on your {device_type} repair (Job #{job_id})"
    plain_text = f"Hello {cust_name}, there is an update on your repair job #{job_id}."
    if status == "New":
        html = f"""
        <p>Dear {cust_name},</p>
        <p>We’ve <strong>received</strong> your <em>{device_type} ({device_model})</em> for the issue:
           “{problem}” on {created_at}.</p>
        <p>Our technician will begin working shortly. We’ll keep you posted!</p>
        """
    elif status == "In Progress":
        html = f"""
        <p>Hi {cust_name},</p>
        <p>Your <em>{device_type} ({device_model})</em> is now <strong>in progress</strong> with our technician.</p>
        <p>We’ll notify you as soon as it’s ready for pickup.</p>
        """
    elif status == "Completed":
        html = f"""
        <p>Hi {cust_name},</p>
        <p>Great news! Your <em>{device_type} ({device_model})</em> repair is <strong>complete</strong>.</p>
        <p>Please stop by to collect your device at your convenience.</p>
        <p>Thank you for choosing us!</p>
        """
    else:
        html = f"""
        <p>Hi {cust_name},</p>
        <p>There’s an update on your <em>{device_type} ({device_model})</em> repair job:</p>
        <p><strong>Status:</strong> {status}</p>
        <p>We’ll follow up with any further updates.</p>
        """

    # --- Build MIME message ---
    msg = MIMEMultipart("alternative")
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = cust_email
    msg["Subject"] = subject

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html, "html"))

    # --- Send via SMTP with STARTTLS ---
    try:
        smtp = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        smtp.ehlo()
        smtp.starttls()
        smtp.login(SENDER_EMAIL, SENDER_PASS)
        smtp.sendmail(SENDER_EMAIL, [cust_email], msg.as_string())
        smtp.quit()
        print(f"✅ Email sent to {cust_email}")
    except Exception as e:
        print(f"[!] Failed to send email: {e}")

# --- Example usage ---
if __name__ == "__main__":
    conn = sqlite3.connect("/Users/jayanth/Documents/GitHub/refactored-JobSheet/repairpro.db")
    JOB_ID  = 7
    send_job_status_email(conn, JOB_ID)
