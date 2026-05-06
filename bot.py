import sys
import asyncio
import os
import json
import sqlite3
from datetime import datetime, timedelta

# ===== FIX FOR ASYNCIO ON RENDER =====
if sys.version_info[0] == 3 and sys.version_info[1] >= 14:
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass

try:
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
except:
    pass

# Import pyrogram
from pyrogram import Client, filters
from pyrogram.types import Message

# ===== ENVIRONMENT VARIABLES =====
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

if not SESSION_STRING:
    print("❌ SESSION_STRING not found!")
    sys.exit(1)

if not API_ID or not API_HASH:
    print("❌ API_ID or API_HASH not found!")
    sys.exit(1)

print("✅ Environment variables loaded")

# ===== SAVED MESSAGES (You can add more) =====
SAVED_MESSAGES = {
    "default": "🤖 *Hi! I'm offline right now.*\n\nI'm an AI agent and will respond as soon as I'm back. Thanks for your message! 👍",
    
    "work": "💼 *Office Hours* - I'm currently away from my desk. Will get back to you within 24 hours.",
    
    "vacation": "🏖️ *On vacation* - I'll be back on Monday. For urgent matters, please email me.",
    
    "meeting": "📅 *In a meeting* - I'll get back to you after the meeting. Thanks for understanding!",
    
    "sleep": "😴 *Sleeping* - I'm offline right now. Will reply in the morning!",
    
    "busy": "🔴 *Busy* - I'll respond when I'm free. Thanks for your patience!",
    
    "thankyou": "🙏 Thanks for your message! I'll get back to you soon.",
}

# ===== CONFIGURATION =====
CURRENT_MESSAGE = "default"
AUTO_REPLY_ENABLED = True
COOLDOWN_MINUTES = 10  # Don't reply to same person within 10 minutes

# Database for cooldown
conn = sqlite3.connect('auto_reply.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS replied_users 
             (user_id INTEGER PRIMARY KEY, last_reply_time TEXT)''')
conn.commit()

def has_replied_recently(user_id):
    c.execute("SELECT last_reply_time FROM replied_users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    
    if result:
        last_time = datetime.fromisoformat(result[0])
        if datetime.now() - last_time < timedelta(minutes=COOLDOWN_MINUTES):
            return True
    
    c.execute("REPLACE INTO replied_users (user_id, last_reply_time) VALUES (?, ?)",
              (user_id, datetime.now().isoformat()))
    conn.commit()
    return False

# Create client
print("🔐 Creating client with session string...")
app = Client(
    "telegram_bot",
    session_string=SESSION_STRING,
    api_id=API_ID,
    api_hash=API_HASH,
    no_updates=True,
    sleep_threshold=60
)

# ===== AUTO-REPLY HANDLER =====
@app.on_message(filters.private & filters.incoming)
async def auto_reply_handler(client: Client, message: Message):
    global AUTO_REPLY_ENABLED, CURRENT_MESSAGE
    
    # Check if auto-reply is ON
    if not AUTO_REPLY_ENABLED:
        print(f"⏸️ Auto-reply OFF - No reply to {message.from_user.first_name}")
        return
    
    # Don't reply to commands or empty messages
    if not message.text or message.text.startswith('.'):
        return
    
    # Cooldown check
    if has_replied_recently(message.from_user.id):
        print(f"⏭️ Cooldown - Skipped {message.from_user.first_name}")
        return
    
    try:
        # Show typing indicator
        await client.send_chat_action(message.chat.id, "typing")
        await asyncio.sleep(1.5)
        
        # Get reply message
        reply_text = SAVED_MESSAGES.get(CURRENT_MESSAGE, SAVED_MESSAGES["default"])
        
        # Send reply
        await message.reply_text(reply_text, parse_mode="Markdown")
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Replied to: {message.from_user.first_name} (@{message.from_user.username or 'no username'})")
        
    except Exception as e:
        print(f"❌ Error replying to {message.from_user.first_name}: {e}")

# ===== COMMANDS TO CONTROL BOT (Send these in any chat) =====
@app.on_message(filters.text & filters.me)
async def control_handler(client: Client, message: Message):
    global AUTO_REPLY_ENABLED, CURRENT_MESSAGE, COOLDOWN_MINUTES
    text = message.text.lower().strip()
    
    # ===== ON / OFF COMMANDS =====
    if text == ".on":
        if not AUTO_REPLY_ENABLED:
            AUTO_REPLY_ENABLED = True
            await message.edit_text("✅ **Auto-reply is now ON** 🔛\n\nI will automatically reply to everyone who messages you.")
            print("🟢 Auto-reply turned ON")
        else:
            await message.edit_text("ℹ️ Auto-reply is already ON")
        return
    
    if text == ".off":
        if AUTO_REPLY_ENABLED:
            AUTO_REPLY_ENABLED = False
            await message.edit_text("❌ **Auto-reply is now OFF** 🔴\n\nNo automatic replies will be sent.")
            print("🔴 Auto-reply turned OFF")
        else:
            await message.edit_text("ℹ️ Auto-reply is already OFF")
        return
    
    # ===== STATUS COMMAND =====
    if text == ".status":
        status_text = "🟢 *ON*" if AUTO_REPLY_ENABLED else "🔴 *OFF*"
        me = await client.get_me()
        await message.edit_text(
            f"🤖 *Auto-Reply Bot Status*\n\n"
            f"📱 Account: {me.first_name}\n"
            f"🆔 User ID: `{me.id}`\n"
            f"🎛️ Status: {status_text}\n"
            f"📝 Current Message: `{CURRENT_MESSAGE}`\n"
            f"⏰ Cooldown: {COOLDOWN_MINUTES} minutes\n"
            f"💾 Saved Messages: {len(SAVED_MESSAGES)}\n\n"
            f"Use `.help` for all commands"
        )
        return
    
    # ===== LIST ALL SAVED MESSAGES =====
    if text == ".listmsg" or text == ".messages":
        msg_list = "\n".join([f"  • `{k}`" for k in SAVED_MESSAGES.keys()])
        await message.edit_text(
            f"📝 *Saved Messages*\n{msg_list}\n\n"
            f"Current: `{CURRENT_MESSAGE}`\n"
            f"Auto-reply: {'🟢 ON' if AUTO_REPLY_ENABLED else '🔴 OFF'}\n\n"
            f"Use `.use <name>` to switch\n"
            f"Use `.preview` to see current message"
        )
        return
    
    # ===== PREVIEW CURRENT MESSAGE =====
    if text == ".preview" or text == ".showmsg":
        preview = SAVED_MESSAGES[CURRENT_MESSAGE]
        await message.edit_text(
            f"📄 *Current Auto-Reply Message*\n\n"
            f"*Name:* `{CURRENT_MESSAGE}`\n\n"
            f"{preview}\n\n"
            f"Use `.use <name>` to change"
        )
        return
    
    # ===== SWITCH TO DIFFERENT MESSAGE =====
    if text.startswith(".use "):
        new_msg = text.replace(".use ", "").strip()
        if new_msg in SAVED_MESSAGES:
            CURRENT_MESSAGE = new_msg
            await message.edit_text(
                f"✅ Now using message: *{new_msg}*\n\n"
                f"Preview: {SAVED_MESSAGES[new_msg][:100]}..."
            )
            print(f"📝 Switched to message: {new_msg}")
        else:
            await message.edit_text(f"❌ Message '{new_msg}' not found.\n\nUse `.listmsg` to see all available messages")
        return
    
    # ===== ADD NEW CUSTOM MESSAGE =====
    if text.startswith(".addmsg "):
        parts = message.text.split(maxsplit=2)
        if len(parts) >= 3:
            msg_name = parts[1]
            msg_content = parts[2]
            
            if msg_name in SAVED_MESSAGES:
                await message.edit_text(f"⚠️ Message '{msg_name}' already exists. Use `.delmsg {msg_name}` first to delete it.")
            else:
                SAVED_MESSAGES[msg_name] = msg_content
                await message.edit_text(f"✅ Added new message: *{msg_name}*\n\nContent: {msg_content[:100]}...")
                
                # Save to file
                with open("saved_messages.json", "w") as f:
                    json.dump(SAVED_MESSAGES, f)
                print(f"➕ Added new message: {msg_name}")
        else:
            await message.edit_text("📝 *Usage:* `.addmsg name Your message content here`\n\nExample: `.addmsg hello Hello! How can I help you?`")
        return
    
    # ===== DELETE A SAVED MESSAGE =====
    if text.startswith(".delmsg "):
        msg_name = text.replace(".delmsg ", "").strip()
        
        # Prevent deletion of default messages
        if msg_name in ["default", "work", "vacation", "meeting", "sleep", "busy", "thankyou"]:
            await message.edit_text(f"❌ Cannot delete default message `{msg_name}`.\n\nYou can delete only custom messages you added.")
        elif msg_name in SAVED_MESSAGES:
            del SAVED_MESSAGES[msg_name]
            await message.edit_text(f"✅ Deleted message: *{msg_name}*")
            
            # Save to file
            with open("saved_messages.json", "w") as f:
                json.dump(SAVED_MESSAGES, f)
            print(f"🗑️ Deleted message: {msg_name}")
            
            # If current message was deleted, switch to default
            if CURRENT_MESSAGE == msg_name:
                CURRENT_MESSAGE = "default"
                await message.edit_text(f"ℹ️ Current message was deleted. Switched to `default`")
        else:
            await message.edit_text(f"❌ Message '{msg_name}' not found.\n\nUse `.listmsg` to see all messages")
        return
    
    # ===== SET COOLDOWN TIME =====
    if text.startswith(".cooldown "):
        try:
            new_cooldown = int(text.replace(".cooldown ", "").strip())
            if 1 <= new_cooldown <= 60:
                COOLDOWN_MINUTES = new_cooldown
                await message.edit_text(f"✅ Cooldown set to *{COOLDOWN_MINUTES} minutes*")
                print(f"⏰ Cooldown changed to {COOLDOWN_MINUTES} minutes")
            else:
                await message.edit_text("❌ Cooldown must be between 1 and 60 minutes")
        except:
            await message.edit_text("❌ Invalid value. Use: `.cooldown 10` (for 10 minutes)")
        return
    
    # ===== HELP COMMAND =====
    if text == ".help" or text == ".commands":
        await message.edit_text(
            "📌 *Auto-Reply Bot Commands*\n\n"
            "*Control:*\n"
            "  `.on` - Turn ON auto-reply\n"
            "  `.off` - Turn OFF auto-reply\n"
            "  `.status` - Show bot status\n\n"
            
            "*Messages:*\n"
            "  `.listmsg` - List all saved messages\n"
            "  `.preview` - Preview current message\n"
            "  `.use <name>` - Switch to different message\n"
            "  `.addmsg <name> <content>` - Add custom message\n"
            "  `.delmsg <name>` - Delete custom message\n\n"
            
            "*Settings:*\n"
            "  `.cooldown <minutes>` - Set cooldown (1-60 min)\n"
            "  `.help` - Show this menu\n\n"
            
            "*Available Messages:*\n" + 
            "\n".join([f"  • `{k}`" for k in list(SAVED_MESSAGES.keys())[:5]]) + 
            f"\n  ... and {len(SAVED_MESSAGES)-5} more\n\n"
            "_Send .listmsg to see all_"
        )
        return
    
    # ===== RELOAD MESSAGES FROM FILE =====
    if text == ".reload":
        try:
            with open("saved_messages.json", "r") as f:
                loaded = json.load(f)
                SAVED_MESSAGES.update(loaded)
            await message.edit_text(f"✅ Reloaded {len(loaded)} custom messages from file")
            print("📂 Reloaded messages from file")
        except:
            await message.edit_text("ℹ️ No saved messages file found")
        return

# Load saved messages from file
try:
    with open("saved_messages.json", "r") as f:
        loaded = json.load(f)
        SAVED_MESSAGES.update(loaded)
        print(f"📂 Loaded {len(loaded)} custom messages from file")
except FileNotFoundError:
    print("📝 No saved messages file found, using defaults")

print("=" * 55)
print("🤖 AUTO-REPLY BOT RUNNING ON RENDER")
print(f"🐍 Python: {sys.version}")
print(f"📱 Account: Connected via session")
print(f"🎛️ Status: {'ON' if AUTO_REPLY_ENABLED else 'OFF'}")
print(f"📝 Current Message: {CURRENT_MESSAGE}")
print(f"⏰ Cooldown: {COOLDOWN_MINUTES} minutes")
print("=" * 55)
print("Bot is ready! Waiting for messages...")
print("Send .help in any chat for commands")
print("=" * 55)

if __name__ == "__main__":
    try:
        app.run()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import time
        time.sleep(5)
