import requests

TELEGRAM_TOKEN = "8259612868:AAG6NyXf79hW4JB1ZkQNIViMTDBFd6hE0WE"
TELEGRAM_CHAT_ID = "6952647629"   # nhớ thay nếu khác

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    response = requests.post(url, data=data)
    print("Status code:", response.status_code)
    print("Response:", response.text)

send_telegram("✅ Test gửi tin nhắn từ Python thành công!")
