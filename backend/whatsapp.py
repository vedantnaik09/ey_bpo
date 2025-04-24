from twilio.rest import Client
import os 
from dotenv import load_dotenv
load_dotenv('.env.local')

# Your Twilio credentials
account_sid =os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)

def send_whatsapp(to_number,confirmation_message):
    # customer_info = get_user_info(to_number)
    # name=customer_info['Name']
    message_body = confirmation_message
    message = client.messages.create(
        from_='whatsapp:+14155238886',
        body=message_body,
        to=f'whatsapp:{to_number}'
    )
    print(message.sid)
    return "success"