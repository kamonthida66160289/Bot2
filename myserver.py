from flask import Flask
from threading import Thread

app = Flask('')  # แก้ชื่อแอปพลิเคชันให้ถูกต้อง

@app.route('/')
def home():
    return "Server is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def server_on():
    t = Thread(target=run)  # แก้ชื่อฟังก์ชันและพารามิเตอร์ให้ถูกต้อง
    t.start()