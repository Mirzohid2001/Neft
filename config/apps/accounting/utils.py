import requests

TOKEN = "7627739630:AAFovXPKpGI-ztN-sLE9BfwLX6_jsVBb2_I"
CHAT_ID = "6286760403"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'HTML'
    }
    response = requests.post(url, data=payload)
    return response.json()
