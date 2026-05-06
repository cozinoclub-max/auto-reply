import asyncio
import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta

# Set event loop policy for Windows compatibility
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Apply nest_asyncio if available
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

# ===== IMPORT PYROGRAM (SAHI WALA) =====
from pyrogram import Client, filters
from pyrogram.types import Message

# ===== ENVIRONMENT VARIABLES =====
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

# ===== VALIDATION =====
if not SESSION_STRING:
    print("❌ CRITICAL ERROR: SESSION_STRING not found in environment variables!")
    print("Please add SESSION_STRING to your Render environment variables")
    sys.exit(1)

if not API_ID or not API_HASH:
    print("❌ CRITICAL ERROR: API_ID or API_HASH not found!")
    sys.exit(1)

print("✅ Environment variables loaded successfully")

# ===== CONFIGURATION =====
SAVED_MESSAGES = {
    "default": "🤖 *Hi! I'm offline right now.*\n\nI'm an AI agent and will respond as soon as I'm back. Thanks for your message! 👍",
    "work": "💼 *Office Hours* - I'm currently away from my desk. Will get back to you within 24 hours.",
    "vacation": "🏖️ *On vacation* - I'll be back on Monday.",
}

CURRENT_MESSAGE = "default"
AUTO_REPLY_ENABLED = True

# Database for cooldown
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

# Create client using session string
print("🔐 Creating client with session string...")
app = Client(
    "telegram_bot",
    session_string=SESSION_STRING,
    api_id=API_ID,
    api_hash=API_HASH,
    no_updates=True,
    sleep_threshold=60
)

@app.on_message(filters.private & filters.incoming)
async def auto_reply_handler(client: Client, message: Message):
    """Auto-reply to private messages"""
    global AUTO_REPLY_ENABLED
    
    if not AUTO_REPLY_ENABLED:
        return
    
    if not message.text or message.text.startswith('.'):
        return
    
    if has_replied_recently(message.from_user.id):
        return
    
    try:
        # Simulate typing
        await client.send_chat_action(message.chat.id, "typing")
        await asyncio.sleep(1)
        
        reply_text = SAVED_MESSAGES.get(CURRENT_MESSAGE, SAVED_MESSAGES["default"])
        await message.reply_text(reply_text, parse_mode="Markdown")
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Replied to: {message.from_user.first_name}")
        
    except Exception as e:
        print(f"❌ Error replying: {e}")

@app.on_message(filters.text & filters.me)
async def control_handler(client: Client, message: Message):
    """Control commands for the bot"""
    global AUTO_REPLY_ENABLED, CURRENT_MESSAGE
    
    text = message.text.lower().strip()
    
    if text == ".on":
        AUTO_REPLY_ENABLED = True
        await message.edit_text("✅ **Auto-reply is now ON**")
        print("🟢 Auto-reply turned ON")
        
    elif text == ".off":
        AUTO_REPLY_ENABLED = False
        await message.edit_text("❌ **Auto-reply is now OFF**")
        print("🔴 Auto-reply turned OFF")
        
    elif text == ".status":
        status = "🟢 ON" if AUTO_REPLY_ENABLED else "🔴 OFF"
        await message.edit_text(
            f"**🤖 Bot Status**\n\n"
            f"Status: {status}\n"
            f"Message: `{CURRENT_MESSAGE}`\n"
            f"Session: Active"
        )
        
    elif text.startswith(".use "):
        new_msg = text.replace(".use ", "").strip()
        if new_msg in SAVED_MESSAGES:
            CURRENT_MESSAGE = new_msg
            await message.edit_text(f"✅ Now using message: **{new_msg}**")
        else:
            await message.edit_text(f"❌ Message '{new_msg}' not found. Use `.listmsg` to see all")
            
    elif text == ".listmsg":
        msgs = "\n".join([f"• `{k}`" for k in SAVED_MESSAGES.keys()])
        await message.edit_text(f"**📝 Saved Messages:**\n{msgs}\n\nCurrent: `{CURRENT_MESSAGE}`")
    
    elif text == ".help":
        await message.edit_text(
            "**📌 Commands:**\n"
            "• `.on` - Turn ON auto-reply\n"
            "• `.off` - Turn OFF auto-reply\n"
            "• `.status` - Check status\n"
            "• `.use name` - Change message\n"
            "• `.listmsg` - Show messages\n"
            "• `.help` - This menu"
        )

# Load saved messages from file (optional)
try:
    with open("saved_messages.json", "r") as f:
        loaded = json.load(f)
        SAVED_MESSAGES.update(loaded)
        print("📂 Loaded custom messages")
except FileNotFoundError:
    pass

print("=" * 50)
print("🤖 AUTO-REPLY BOT RUNNING ON RENDER")
print(f"🐍 Python: {sys.version}")
print(f"📱 Account: Connected via session")
print(f"🎛️ Status: {'ON' if AUTO_REPLY_ENABLED else 'OFF'}")
print("=" * 50)
print("Bot is ready! Waiting for messages...")
print("=" * 50)

if __name__ == "__main__":
    try:
        app.run()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
