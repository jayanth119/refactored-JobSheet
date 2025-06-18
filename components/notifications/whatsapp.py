import requests

access_token = "YOUR_ACCESS_TOKEN"
phone_number_id = "YOUR_PHONE_NUMBER_ID"
recipient_number = "91XXXXXXXXXX"  # Include country code

def send_whatsapp_message(message, recipient_number):
    url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_number,
        "type": "text",
        "text": {"body": message}
    }

    response = requests.post(url, headers=headers, json=payload)
    print(response.status_code, response.json())

    if response.status_code == 200:
        print("Message sent successfully!")
    else:
        print("Failed to send message.")

    return True if response.status_code == 200 else  False
