import asyncio
import sys
import os
import sqlite3
import json
from datetime import datetime, timedelta

# ===== FIX FOR RENDER PYTHON 3.14 =====
try:
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
except:
    pass

try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

# Now import pyrogram
from pyrogram import Client, filters
from pyrogram.types import Message

# ===== YOUR API CREDENTIALS =====
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
PHONE_NUMBER = os.environ.get("PHONE_NUMBER", "")

# ===== CUSTOMIZE AUTO-REPLY MESSAGES =====
SAVED_MESSAGES = {
    "default": "🤖 *Hi! I'm offline right now.*\n\nI'm an AI agent and will respond as soon as I'm back. Thanks for your message! 👍",
    "work": "💼 *Office Hours* - I'm currently away from my desk. Will get back to you within 24 hours.",
    "vacation": "🏖️ *On vacation* - I'll be back on Monday. For urgent matters, please email me.",
    "custom1": "✨ Thanks for reaching out! Maxx is offline at the moment. Your message has been saved.",
    "custom2": "🎯 *Auto Reply Active*\n\nI'll respond to your message as soon as possible. Have a great day!"
}

CURRENT_MESSAGE = "default"
AUTO_REPLY_ENABLED = True

# Database setup
conn = sqlite3.connect('auto_reply.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS replied_users 
             (user_id INTEGER PRIMARY KEY, last_reply_time TEXT)''')
conn.commit()

def has_replied_recently(user_id, cooldown_minutes=30):
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
app = Client("telegram_bot", 
             api_id=API_ID, 
             api_hash=API_HASH, 
             phone_number=PHONE_NUMBER,
             sleep_threshold=60,
             no_updates=True)

@app.on_message(filters.private & filters.incoming)
async def auto_reply_to_all(client: Client, message: Message):
    global AUTO_REPLY_ENABLED
    
    if not AUTO_REPLY_ENABLED:
        return
    
    if not message.text:
        return
    
    if has_replied_recently(message.from_user.id, cooldown_minutes=30):
        return
    
    try:
        await client.send_chat_action(message.chat.id, "typing")
        await asyncio.sleep(1.5)
        
        reply_text = SAVED_MESSAGES.get(CURRENT_MESSAGE, SAVED_MESSAGES["default"])
        await message.reply_text(reply_text, parse_mode="Markdown")
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Replied to: {message.from_user.first_name}")
        
    except Exception as e:
        print(f"Error: {e}")

@app.on_message(filters.text & filters.me)
async def control_bot(client: Client, message: Message):
    global AUTO_REPLY_ENABLED, CURRENT_MESSAGE
    
    text = message.text.lower().strip()
    
    if text == ".on":
        if not AUTO_REPLY_ENABLED:
            AUTO_REPLY_ENABLED = True
            await message.edit_text("✅ *Auto-reply is now ON* 🔛")
            print("🟢 Auto-reply turned ON")
        else:
            await message.edit_text("ℹ️ Auto-reply is already ON")
        return
    
    if text == ".off":
        if AUTO_REPLY_ENABLED:
            AUTO_REPLY_ENABLED = False
            await message.edit_text("❌ *Auto-reply is now OFF* 🔴")
            print("🔴 Auto-reply turned OFF")
        else:
            await message.edit_text("ℹ️ Auto-reply is already OFF")
        return
    
    if text == ".status":
        me = await client.get_me()
        status_text = "🟢 *ON*" if AUTO_REPLY_ENABLED else "🔴 *OFF*"
        await message.edit_text(
            f"🤖 *Auto-Reply Bot Status*\n\n"
            f"📱 Account: {me.first_name}\n"
            f"🎛️ Status: {status_text}\n"
            f"📝 Current Reply: `{CURRENT_MESSAGE}`\n"
            f"💾 Saved Messages: {len(SAVED_MESSAGES)}\n\n"
            f"*Commands:*\n"
            f"  `.on` - Turn ON\n"
            f"  `.off` - Turn OFF\n"
            f"  `.listmsg` - See all messages\n"
            f"  `.use name` - Switch message\n"
            f"  `.preview` - See current message\n"
            f"  `.addmsg name content` - Add new\n"
            f"  `.delmsg name` - Delete"
        )
        return
    
    if text == ".listmsg" or text == ".messages":
        msg_list = "\n".join([f"  • {k}" for k in SAVED_MESSAGES.keys()])
        status_icon = "🟢 ON" if AUTO_REPLY_ENABLED else "🔴 OFF"
        await message.edit_text(
            f"📝 *Saved Messages*\n{msg_list}\n\n"
            f"Current: `{CURRENT_MESSAGE}`\n"
            f"Auto-reply: {status_icon}\n\n"
            f"Use `.use name` to switch\n"
            f"Use `.preview` to see current message"
        )
        return
    
    if text.startswith(".use "):
        new_msg = text.replace(".use ", "").strip()
        if new_msg in SAVED_MESSAGES:
            CURRENT_MESSAGE = new_msg
            await message.edit_text(f"✅ Now using message: *{new_msg}*")
        else:
            await message.edit_text(f"❌ Message '{new_msg}' not found")
        return
    
    if text == ".preview" or text == ".showmsg":
        preview = SAVED_MESSAGES[CURRENT_MESSAGE]
        await message.edit_text(f"📄 *Current Auto-Reply*\n\n{preview}")
        return
    
    if text.startswith(".addmsg "):
        parts = message.text.split(maxsplit=2)
        if len(parts) >= 3:
            msg_name = parts[1]
            msg_content = parts[2]
            SAVED_MESSAGES[msg_name] = msg_content
            await message.edit_text(f"✅ Added new message: *{msg_name}*")
            
            with open("saved_messages.json", "w") as f:
                json.dump(SAVED_MESSAGES, f)
        else:
            await message.edit_text("Usage: `.addmsg name Your message content here`")
        return
    
    if text.startswith(".delmsg "):
        msg_name = text.replace(".delmsg ", "").strip()
        if msg_name in SAVED_MESSAGES and msg_name not in ["default", "work", "vacation"]:
            del SAVED_MESSAGES[msg_name]
            await message.edit_text(f"✅ Deleted message: *{msg_name}*")
            with open("saved_messages.json", "w") as f:
                json.dump(SAVED_MESSAGES, f)
        elif msg_name in ["default", "work", "vacation"]:
            await message.edit_text("❌ Cannot delete default messages")
        else:
            await message.edit_text(f"❌ Message '{msg_name}' not found")
        return

# Load saved messages
try:
    with open("saved_messages.json", "r") as f:
        loaded = json.load(f)
        SAVED_MESSAGES.update(loaded)
        print("📂 Loaded saved messages")
except FileNotFoundError:
    print("📝 No saved messages file found, using defaults")

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 AUTO-REPLY BOT RUNNING ON RENDER")
    print(f"🐍 Python version: {sys.version}")
    print("=" * 50)
    app.run()
