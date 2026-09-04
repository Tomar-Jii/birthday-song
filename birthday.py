#!/usr/bin/env python3
# Birthday Song Bot - Python 
# Developer: Tomar Ji

import requests
import json
import os
import time
import logging
from flask import Flask, request, jsonify
import threading

# ============== CONFIGURATION ==============
BOT_TOKEN = "8924634458:AAGJSKntWnJYyFEik07ELwAK28HPu-uRro8"
ADMIN_ID = 8970921994

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

# Files
USERS_FILE = "users.txt"
BROADCAST_FILE = "broadcast.txt"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Flask app for webhook
app = Flask(__name__)

# ============== HELPER FUNCTIONS ==============

def send_message(chat_id, text, reply_markup=None):
    """Send text message to user"""
    url = API_URL + "sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Send message error: {e}")

def send_audio(chat_id, audio_url, caption):
    """Send audio file"""
    url = API_URL + "sendAudio"
    payload = {
        "chat_id": chat_id,
        "audio": audio_url,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        logging.error(f"Send audio error: {e}")

def save_user(user_id):
    """Save user to file if not exists"""
    if not os.path.exists(USERS_FILE):
        open(USERS_FILE, 'w').close()
    
    with open(USERS_FILE, 'r') as f:
        users = [line.strip() for line in f.readlines()]
    
    if str(user_id) not in users:
        with open(USERS_FILE, 'a') as f:
            f.write(f"{user_id}\n")
        logging.info(f"New user saved: {user_id}")

def get_birthday_song(name):
    """Get birthday song URL for given name"""
    name = name.lower().capitalize()
    mp3_url = f"https://s3-us-west-2.amazonaws.com/1hbcf/{name}.mp3"
    
    try:
        resp = requests.head(mp3_url, timeout=10)
        if resp.status_code == 200:
            return mp3_url
        return None
    except:
        return None

def broadcast_message(message):
    """Send broadcast to all users"""
    if not os.path.exists(USERS_FILE):
        return
    
    with open(USERS_FILE, 'r') as f:
        users = [line.strip() for line in f.readlines()]
    
    success = 0
    for user_id in users:
        try:
            send_message(user_id, message)
            success += 1
            time.sleep(0.05)
        except Exception as e:
            logging.error(f"Broadcast to {user_id} failed: {e}")
    
    logging.info(f"Broadcast sent to {success} users")

# ============== MESSAGE HANDLER ==============

def handle_message(update):
    """Process incoming messages"""
    if "message" not in update:
        return
    
    message = update["message"]
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "").strip()
    
    # Save user
    save_user(user_id)
    
    # Handle /start command
    if text == "/start":
        send_message(
            chat_id,
            "🎉 *Welcome to Birthday Song Bot* 🎶\n\n"
            "👉 *Send Name*\n"
            "_The name on which the birthday song is to be made_ 🎂\n\n"
            "👨‍💻 *Developer:* Tomar Ji"
        )
        return
    
    # Handle /broadcast command (admin only)
    if text == "/broadcast" and user_id == ADMIN_ID:
        with open(BROADCAST_FILE, 'w') as f:
            f.write("waiting")
        send_message(chat_id, "📢 Send message to broadcast:")
        return
    
    # Handle broadcast message (admin only)
    if os.path.exists(BROADCAST_FILE):
        with open(BROADCAST_FILE, 'r') as f:
            status = f.read()
        if status == "waiting" and user_id == ADMIN_ID:
            os.remove(BROADCAST_FILE)
            broadcast_message(text)
            send_message(chat_id, "✅ Broadcast sent successfully!")
            return
    
    # Handle normal name input
    if text:
        mp3_url = get_birthday_song(text)
        
        if mp3_url:
            send_audio(
                chat_id,
                mp3_url,
                f"🎂 Happy Birthday *{text.capitalize()}* 🎉\n_Generated via Tomar Ji's Bot_"
            )
        else:
            send_message(
                chat_id,
                f"❌ *Sorry!*\n\n"
                f"The birthday song for the name *{text.capitalize()}* is not available.\n"
                f"Please try another name."
            )

# ============== WEBHOOK ENDPOINT ==============

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    """Handle incoming updates from Telegram"""
    try:
        update = request.get_json()
        if "message" in update:
            handle_message(update)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500

@app.route("/", methods=["GET"])
def index():
    return "Birthday Bot is running by Tomar Ji!", 200

# ============== SET WEBHOOK ==============

def set_webhook():
    """Set webhook for Telegram bot"""
    public_url = os.environ.get("PUBLIC_URL", "https://your-domain.com")
    webhook_url = f"{public_url}/webhook/{BOT_TOKEN}"
    
    url = API_URL + "setWebhook"
    payload = {"url": webhook_url}
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if data.get("ok"):
            logging.info(f"Webhook set successfully: {webhook_url}")
        else:
            logging.error(f"Failed to set webhook: {data}")
    except Exception as e:
        logging.error(f"Set webhook error: {e}")

# ============== POLLING MODE ==============

def polling_mode():
    """Use polling instead of webhook"""
    logging.info("Starting polling mode by Tomar Ji...")
    offset = 0
    
    while True:
        try:
            url = API_URL + "getUpdates"
            params = {"offset": offset, "timeout": 30}
            resp = requests.get(url, params=params, timeout=35)
            data = resp.json()
            
            if data.get("ok"):
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    if "message" in update:
                        handle_message(update)
            
            time.sleep(1)
        except Exception as e:
            logging.error(f"Polling error: {e}")
            time.sleep(5)

# ============== MAIN ==============

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════╗
    ║          BIRTHDAY SONG BOT            ║
    ║         Created by Tomar Ji           ║
    ╚═══════════════════════════════════════╝
    """)
    
    polling_mode()
  
