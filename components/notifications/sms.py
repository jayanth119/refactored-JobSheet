from twilio.rest import Client


def send_sms_message(message, phone ):
    account_sid = 'YOUR_TWILIO_SID'
    auth_token = 'YOUR_TWILIO_AUTH_TOKEN'
    client = Client(account_sid, auth_token)

    message = client.messages.create(
        body= message,
        from_='+1234567890',  # Twilio phone number
        to= phone    # Your verified number
    )

    print("Message SID:", message.sid)
    return True if message.sid else False