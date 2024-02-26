import logging
import arrow, datetime
import requests
import json
import properties as properties
from email.mime.text import MIMEText
import smtplib



BASE_URL = 'https://playtomic.io'
USER = None
PASSWORD = None

#Returns the access token use in the API
def login():
    global USER, PASSWORD    
    if USER is None:
        USER = properties.get_property('username')
    if PASSWORD is None:
        PASSWORD = properties.get_property('password')
   
    try:
        response = requests.request("POST", url=f"{BASE_URL}/api/v3/auth/login", headers={'Content-Type': 'application/json'}, data=json.dumps({"email": USER,"password": PASSWORD}))
        return response.json()['access_token']
    except Exception as e:
        logging.error(f"Error generating access token")
        return ''
    
#Returns the access token use in the API
def get_user_id():
    global USER, PASSWORD    
    if USER is None:
        USER = properties.get_property('username')
    if PASSWORD is None:
        PASSWORD = properties.get_property('password')
   
    try:
        response = requests.request("POST", url=f"{BASE_URL}/api/v3/auth/login", headers={'Content-Type': 'application/json'}, data=json.dumps({"email": USER,"password": PASSWORD}))
        return response.json()['user_id']
    except Exception as e:
        logging.error(f"Error generating access token")
        return ''

#Gets tenant (Club)
def get_tenant(tenant_id):
    try:
        response = requests.request("GET", url=f"{BASE_URL}/api/v1/tenants/{tenant_id}", headers={'Content-Type': 'application/json', 'Authorization': f"Bearer {login()}"})
        return response.json()
    except Exception as e:
        logging.error(f"Error returning tenant")
        return ''

def get_tenant_availability(tenant_id, start_min, start_max):
    try:
        response = requests.request("GET", url=f"{BASE_URL}/api/v1/availability", headers={'Content-Type': 'application/json', 'Authorization': f"Bearer {login()}"}, params={'user_id': 'me', 'tenant_id': {tenant_id}, 'sport_id': 'PADEL', 'local_start_min': start_min, 'local_start_max': start_max})
        return response.json()
    except Exception as e:
        logging.error(f"Error returning tenant availability")
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
        
        
        response = requests.request("POST", url=f"{BASE_URL}/api/v1/payment_intents", headers={'Content-Type': 'application/json', 'Accept': 'application/json, text/plain, */*', 'Authorization': f"Bearer {login()}"}, json=body)
        if response.status_code == 200:
            #we update the order to pay with the wallet (Monedero)
            payment_intent = response.json()
            
            
            payment_method_id = None
            for payment_method in payment_intent['available_payment_methods']:
                if 'MERCHANT_WALLET' == payment_method['method_type']:
                    payment_method_id = payment_method['payment_method_id']
                    
                    try:
                        balance = float(payment_method['data']['balance'].split(' ')[0]) - (float(payment_intent['price'].split(' ')[0]) - float(payment_intent['commission'].split(' ')[0]))
                        logging.info(f"----------Current Balance {payment_method['data']['balance']} before payment----------")    
                        send_mail_notification(sender=properties.get_property('username'), to=properties.get_property('username'), subject=f"Playtomic Wallet Ballance: {payment_method['data']['balance']}", body=f"Your wallete balance is {payment_method['data']['balance']}.")
                        
                    except Exception as e:
                        logging.error(f"Error calculating remaining balance")
                    
                    break
                    
            
            body = {"selected_payment_method_id":f"{payment_method_id}","selected_payment_method_data": None}
            response = requests.request("PATCH", url=f"{BASE_URL}/api/v1/payment_intents/{payment_intent['payment_intent_id']}", headers={'Content-Type': 'application/json', 'Accept': 'application/json, text/plain, */*', 'Authorization': f"Bearer {login()}"}, json=body)
            payemnt_intent_modified =  response.json()
            if response.status_code == 200:
                
                response = requests.request("POST", url=f"{BASE_URL}/api/v1/payment_intents/{payment_intent['payment_intent_id']}/confirmation", headers={'Content-Type': 'application/json', 'Accept': 'application/json, text/plain, */*', 'Authorization': f"Bearer {login()}"}, data=None)
                if response.status_code == 200:
                    send_mail_notification(sender=properties.get_property('username'), to=properties.get_property('username'), subject=f"Playtomic Bot: Court Booked: {start}", body=f"Hi, The following court has been booked {start}")
                    return response.json()
    except Exception as e:
        logging.error(f"Error returning tenant availability")
        return ''
    
    
def send_mail_notification(sender, to, subject, body):
    email_html = f"""
    <html>
        <body>
            <p>{body}</p>
        </body>
    </html>"""
    
    msg = MIMEText(body, 'html')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to
    smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    smtp_server.login(sender, properties.get_property('gmail_app_password'))
    smtp_server.sendmail(sender, [to], msg.as_string())
    smtp_server.quit()
    
    pass
    
    

    