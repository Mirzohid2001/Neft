import requests

def send_telegram_message(message):
    token = '7627739630:AAFovXPKpGI-ztN-sLE9BfwLX6_jsVBb2_I'
    chat_id = '6286760403'
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {'chat_id': chat_id, 'text': message}
    response = requests.post(url, data=data)
    return response.json()
