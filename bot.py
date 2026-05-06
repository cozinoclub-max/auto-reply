import asyncio
import sys
import os
from datetime import datetime, timedelta

# ===== FIX FOR RENDER PYTHON 3.14 =====
try:
    # Try to use alternative event loop
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
except:
    pass

# Apply nest_asyncio if available
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

# ===== CONFIGURATION =====
SAVED_MESSAGES = {
    "default": "🤖 *Hi! I'm offline right now.*\n\nI'm an AI agent and will respond as soon as I'm back.",
    "work": "💼 *Office Hours* - I'm currently away from my desk.",
    "vacation": "🏖️ *On vacation* - I'll be back on Monday."
}

CURRENT_MESSAGE = "default"
AUTO_REPLY_ENABLED = True

# Create client with proper settings
app = Client(
    "telegram_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    phone_number=PHONE_NUMBER,
    sleep_threshold=60,
    no_updates=True  # Important for Render
)

@app.on_message(filters.private & filters.incoming)
async def auto_reply_to_all(client: Client, message: Message):
    global AUTO_REPLY_ENABLED
    
    if not AUTO_REPLY_ENABLED:
        return
    
    if not message.text:
        return
    
    try:
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

if __name__ == "__main__":
    print("🤖 Bot starting on Render...")
    print(f"Python version: {sys.version}")
    app.run()
