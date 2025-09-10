# core/utils.py

import random
import requests

def send_authkey_otp(phone_number):
    otp = str(random.randint(1000, 9999))  # 4-digit OTP
    api_url = f"https://api.authkey.io/request?authkey=28d7629dee12e54c&mobile={phone_number}&country_code=91&sid=7326&name=StreetLearning&otp={otp}"

    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            return otp  # OTP sent successfully
        else:
            return None
    except Exception as e:
        print("Error sending OTP:", e)
        return None
