import sendgrid
from sendgrid.helpers.mail import Mail


def promotions(from_email, to_emails , subject, plain_text_content):
    sg = sendgrid.SendGridAPIClient(api_key="YOUR_API_KEY")
    email = Mail(
        from_email=from_email,
        to_emails=to_emails,
        subject=subject,
        plain_text_content=plain_text_content
        
    )
    response = sg.send(email)
    print(response.status_code)