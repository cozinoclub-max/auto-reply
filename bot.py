from pyrogram import Client, filters
from pyrogram.types import Message
import asyncio
import sqlite3
import json
import os
from datetime import datetime, timedelta

# ===== RENDER ENVIRONMENT VARIABLES =====
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
PHONE_NUMBER = os.environ.get("PHONE_NUMBER", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")  # Optional: Use session string instead of phone

# ===== CUSTOMIZE AUTO-REPLY MESSAGES =====
SAVED_MESSAGES = {
    "default": "🤖 *Hi! I'm offline right now.*\n\nI'm an AI agent and will respond as soon as I'm back. Thanks for your message! 👍",
    "work": "💼 *Office Hours* - I'm currently away from my desk. Will get back to you within 24 hours.",
    "vacation": "🏖️ *On vacation* - I'll be back on Monday. For urgent matters, please email me.",
}

CURRENT_MESSAGE = "default"
AUTO_REPLY_ENABLED = True

# Database setup
conn = sqlite3.connect('auto_reply.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS replied_users 
             (user_id INTEGER PRIMARY KEY, last_reply_time TEXT)''')
conn.commit()

def has_replied_recently(user_id, cooldown_minutes=10):
    c.execute("SELECT last_reply_time FROM replied_users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    
    if result:
        last_time = datetime.fromisoformat(result[0])
        if datetime.now() - last_time < timedelta(minutes=cooldown_minutes):
            return True
    
    c.execute("REPLACE INTO replied_users (user_id, last_reply_time) VALUES (?, ?)",
              (user_id, datetime.now().isoformat()))
    conn.commit()
    return False

# Create client
app = Client("telegram_bot", api_id=API_ID, api_hash=API_HASH, phone_number=PHONE_NUMBER)

@app.on_message(filters.private & filters.incoming)
async def auto_reply_to_all(client: Client, message: Message):
    global AUTO_REPLY_ENABLED
    
    if not AUTO_REPLY_ENABLED:
        return
    
    if not message.text:
        return
    
    if has_replied_recently(message.from_user.id, cooldown_minutes=10):
        return
    
    try:
        await client.send_chat_action(message.chat.id, "typing")
        await asyncio.sleep(1)
        
        reply_text = SAVED_MESSAGES.get(CURRENT_MESSAGE, SAVED_MESSAGES["default"])
        await message.reply_text(reply_text, parse_mode="Markdown")
        
        print(f"[{datetime.now()}] Replied to: {message.from_user.first_name}")
        
    except Exception as e:
        print(f"Error: {e}")

@app.on_message(filters.text & filters.me)
async def control_bot(client: Client, message: Message):
    global AUTO_REPLY_ENABLED, CURRENT_MESSAGE
    
    text = message.text.lower().strip()
    
    if text == ".on":
        AUTO_REPLY_ENABLED = True
        await message.edit_text("✅ Auto-reply is now ON")
        
    elif text == ".off":
        AUTO_REPLY_ENABLED = False
        await message.edit_text("❌ Auto-reply is now OFF")
        
    elif text == ".status":
        status = "ON" if AUTO_REPLY_ENABLED else "OFF"
        await message.edit_text(f"🤖 *Bot Status*\nStatus: {status}\nMessage: {CURRENT_MESSAGE}")
        
    elif text.startswith(".use "):
        new_msg = text.replace(".use ", "").strip()
        if new_msg in SAVED_MESSAGES:
            CURRENT_MESSAGE = new_msg
            await message.edit_text(f"✅ Using message: {new_msg}")

print("🤖 Bot is running on Render...")
app.run()
