from twilio.rest import Client

# Your Twilio credentials
account_sid = "AC794a6d3c32085192652213cd6e12073b"
auth_token = "cc943a33bcae8fe6f07cc18721692075"
client = Client(account_sid, auth_token)

def send_whatsapp_image(to_number, message_body):
    message = client.messages.create(
        from_='whatsapp:+14155238886',
        body=message_body,
        to=f'whatsapp:{to_number}'
    )
    print(message.sid)

# Usage
send_whatsapp_image('+917769915068', 'Check out this image!')
