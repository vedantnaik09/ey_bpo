from twilio.rest import Client
import os 
from dotenv import load_dotenv
load_dotenv()

# Your Twilio credentials
account_sid =os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)

def send_whatsapp(to_number):
    # customer_info = get_user_info(to_number)
    # name=customer_info['Name']
    message_body = f""""Hey Vivek! 👋

To celebrate Republic Day, we're offering a ₹500 OFF on all purchases above ₹1500! 🛍✨

This is the perfect time to grab your favorite clothes and accessories at amazing prices. Hurry, the sale ends soon! ⏳

Visit our store or shop online now and enjoy your discount! 💃🕺

Don't miss out! 💥

Cheers,
Powerlook 👗👚"""
    message = client.messages.create(
        from_='whatsapp:+14155238886',
        body=message_body,
        media_url=['https://assets.myntassets.com/h_720,q_90,w_540/v1/assets/images/productimage/2019/8/28/9c95aa26-c5e2-4de3-85b8-04636e598f281566987579954-1.jpg',
                   'https://assets.myntassets.com/h_720,q_90,w_540/v1/assets/images/19190350/2022/7/20/e92ac80d-3e04-4a8f-bd44-583e1aea8f3d1658325126516THREADCURRYAnimeBoysWhitePrintedRoundNeckT-shirt1.jpg'],
        to=f'whatsapp:{to_number}'
    )
    print(message.sid)
    return "success"