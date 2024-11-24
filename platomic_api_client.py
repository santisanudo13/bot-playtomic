import logging
import arrow, datetime
import requests
import json
import properties as properties
from email.mime.text import MIMEText
import smtplib
import time
import random

BASE_URL = 'https://playtomic.io'
USER = None
PASSWORD = None

HEADER_APPLICATION_JSON = 'application/json'
HEADER_ACCEPT_ALL = 'application/json, text/plain, */*'

#Returns the access token use in the API
def login():
    global USER, PASSWORD    
    if USER is None:
        USER = properties.get_property('username')
    if PASSWORD is None:
        PASSWORD = properties.get_property('password')
   
    try:
        random_delay()
        response = requests.request("POST", url=f"{BASE_URL}/api/v3/auth/login", headers={'Content-Type': HEADER_APPLICATION_JSON}, data=json.dumps({"email": USER,"password": PASSWORD}))
        return response.json()['access_token']
    except Exception as e:
        logging.error(f"Error generating access token: {e}")
        return ''
    
#Returns the access token use in the API
def get_user_id():
    global USER, PASSWORD    
    if USER is None:
        USER = properties.get_property('username')
    if PASSWORD is None:
        PASSWORD = properties.get_property('password')
   
    try:
        random_delay()
        response = requests.request("POST", url=f"{BASE_URL}/api/v3/auth/login", headers={'Content-Type': HEADER_APPLICATION_JSON}, data=json.dumps({"email": USER,"password": PASSWORD}))
        return response.json()['user_id']
    except Exception as e:
        logging.error(f"Error generating access token: {e}")
        return ''

#Gets tenant (Club)
def get_tenant(tenant_id):
    try:
        random_delay()
        response = requests.request("GET", url=f"{BASE_URL}/api/v1/tenants/{tenant_id}", headers={'Content-Type': HEADER_APPLICATION_JSON, 'Authorization': f"Bearer {login()}"})
        return response.json()
    except Exception as e:
        logging.error(f"Error returning tenant {e}")
        return ''

def get_tenant_availability(tenant_id, start_min, start_max):
    try:
        random_delay()
        response = requests.request("GET", url=f"{BASE_URL}/api/v1/availability", headers={'Content-Type': HEADER_APPLICATION_JSON, 'Authorization': f"Bearer {login()}"}, params={'user_id': 'me', 'tenant_id': {tenant_id}, 'sport_id': 'PADEL', 'local_start_min': start_min, 'local_start_max': start_max})
        return response.json()
    except Exception as e:
        logging.error(f"Error returning tenant availability {e}")
        return ''
    
def book_court(tenant_id, resource_id, start):
    
    try:     
        user_id = get_user_id()
        body = {
            "allowed_payment_method_types": [
            "OFFER",
            "CASH",
            "MERCHANT_WALLET",
            "DIRECT",
            "SWISH",
            "IDEAL",
            "BANCONTACT",
            "PAYTRAIL",
            "CREDIT_CARD",
            "QUICK_PAY"
            ],
            "user_id": user_id,
            "cart": {
                "requested_item": {
                    "cart_item_type": "CUSTOMER_MATCH",
                    "cart_item_voucher_id": None,
                    "cart_item_data": {
                        "supports_split_payment": True,
                        "number_of_players": 4,
                        "tenant_id": tenant_id,
                        "resource_id": resource_id,
                        "start": start,
                        "duration": 90,
                        "match_registrations": [
                            {
                                "user_id": user_id,
                                "pay_now": True
                            }
                        ]
                    }
                }
            }
        }
        
        random_delay()
        response = requests.request("POST", url=f"{BASE_URL}/api/v1/payment_intents", headers={'Content-Type': HEADER_APPLICATION_JSON, 'Accept': HEADER_ACCEPT_ALL, 'Authorization': f"Bearer {login()}"}, json=body)
        if response.status_code == 200:
            #we update the order to pay with the wallet (Monedero)
            payment_intent = response.json()
            
            
            payment_method_id = None
            for payment_method in payment_intent['available_payment_methods']:
                if 'MERCHANT_WALLET' == payment_method['method_type']:
                    payment_method_id = payment_method['payment_method_id']
                    
                    try:
                        logging.info(f"----------Current Balance {payment_method['data']['balance']} before payment----------")    
                        send_mail_notification(sender=properties.get_property('username'), to=properties.get_property('username'), subject=f"Playtomic Wallet Ballance: {payment_method['data']['balance']}", body=f"Your wallete balance is {payment_method['data']['balance']}.")
                        
                    except Exception as e:
                        logging.error(f"Error calculating remaining balance: {e}")
                    
                    break
                    
            
            body = {"selected_payment_method_id":f"{payment_method_id}","selected_payment_method_data": None}
            random_delay()
            response = requests.request("PATCH", url=f"{BASE_URL}/api/v1/payment_intents/{payment_intent['payment_intent_id']}", headers={'Content-Type': HEADER_APPLICATION_JSON, 'Accept': HEADER_ACCEPT_ALL, 'Authorization': f"Bearer {login()}"}, json=body)
            if response.status_code == 200:
                
                random_delay()
                response = requests.request("POST", url=f"{BASE_URL}/api/v1/payment_intents/{payment_intent['payment_intent_id']}/confirmation", headers={'Content-Type': HEADER_APPLICATION_JSON, 'Accept': HEADER_ACCEPT_ALL, 'Authorization': f"Bearer {login()}"}, data=None)
                if response.status_code == 200:
                    send_mail_notification(sender=properties.get_property('username'), to=properties.get_property('username'), subject=f"Playtomic Bot: Court Booked: {start}", body=f"Hi, The following court has been booked {start}")
                    return response.json()
    except Exception as e:
        logging.error(f"Error returning tenant availability: {e}")
        return ''
    
    
def send_mail_notification(sender, to, subject, body):   
    msg = MIMEText(body, 'html')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to
    smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    smtp_server.login(sender, properties.get_property('gmail_app_password'))
    smtp_server.sendmail(sender, [to], msg.as_string())
    smtp_server.quit()
    
    
def random_delay():
    MAX_WAIT_SECONDS = 4
    time.sleep(random.randrange(1,10)*MAX_WAIT_SECONDS/10)
    

    