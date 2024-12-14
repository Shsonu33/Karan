import subprocess
import json
import os
import random
import string
import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import BOT_TOKEN, ADMIN_IDS, OWNER_USERNAME

USER_FILE = "../users.json"
KEY_FILE = "../keys.json"

flooding_process = None
flooding_command = None
DEFAULT_THREADS = 800

users = {}
keys = {}

# Load data from JSON files
def load_data():
    global users, keys
    users = load_users()
    keys = load_keys()

def load_users():
    try:
        with open(USER_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Error loading users: {e}")
        return {}

def save_users():
    with open(USER_FILE, "w") as file:
        json.dump(users, file)

def load_keys():
    try:
        with open(KEY_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Error loading keys: {e}")
        return {}

def save_keys():
    with open(KEY_FILE, "w") as file:
        json.dump(keys, file)

def generate_key(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def add_time_to_current_date(hours=0, days=0):
    return (datetime.datetime.now() + datetime.timedelta(hours=hours, days=days)).strftime('%Y-%m-%d %H:%M:%S')

# Remove expired keys
def remove_expired_keys():
    global keys
    current_time = datetime.datetime.now()
    keys = {k: v for k, v in keys.items() if datetime.datetime.strptime(v, '%Y-%m-%d %H:%M:%S') > current_time}
    save_keys()

# Command to generate keys
async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    remove_expired_keys()  # Clean up expired keys first
    user_id = str(update.message.from_user.id)
    if user_id in ADMIN_IDS:
        command = context.args
        if len(command) == 2:
            try:
                time_amount = int(command[0])
                time_unit = command[1].lower()
                if time_unit == 'hours':
                    expiration_date = add_time_to_current_date(hours=time_amount)
                elif time_unit == 'days':
                    expiration_date = add_time_to_current_date(days=time_amount)
                else:
                    raise ValueError("Invalid time unit")
                key = generate_key()
                keys[key] = expiration_date
                save_keys()
                response = f"Key generated: {key}\nExpires on: {expiration_date}"
            except ValueError:
                response = "Please specify a valid number and unit of time (hours/days)."
        else:
            response = "Usage: /genkey <amount> <hours/days>"
    else:
        response = "ONLY OWNER CAN USE."

    await update.message.reply_text(response)

# Command to redeem keys
async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    command = context.args
    if len(command) == 1:
        key = command[0]
        if key in keys:
            expiration_date = keys[key]
            if user_id in users:
                user_expiration = datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S')
                new_expiration_date = max(user_expiration, datetime.datetime.now()) + datetime.timedelta(hours=1)
                users[user_id] = new_expiration_date.strftime('%Y-%m-%d %H:%M:%S')
            else:
                users[user_id] = expiration_date
            save_users()
            del keys[key]
            save_keys()
            response = f"✅Key redeemed successfully! Access granted until: {users[user_id]}"
        else:
            response = "Invalid or expired key."
    else:
        response = "Usage: /redeem <key>"

    await update.message.reply_text(response)

# Command to start flooding
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global flooding_process, flooding_command
    user_id = str(update.message.from_user.id)

    if user_id not in users or datetime.datetime.now() > datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S'):
        await update.message.reply_text("❌ Access expired or unauthorized. Please redeem a valid key.")
        return

    if flooding_process is not None:
        await update.message.reply_text("❌ An attack is already running.")
        return

    if flooding_command is None:
        await update.message.reply_text("No flooding parameters set. Use /bgmi to set parameters.")
        return

    flooding_process = subprocess.Popen(flooding_command)
    await update.message.reply_text("🚀 Attack started successfully! 🚀")

# Command to stop flooding
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global flooding_process
    user_id = str(update.message.from_user.id)

    if user_id not in users or datetime.datetime.now() > datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S'):
        await update.message.reply_text("❌ Access expired or unauthorized. Please redeem a valid key.")
        return

    if flooding_process is None:
        await update.message.reply_text("No flooding process is running.")
        return

    flooding_process.terminate()
    flooding_process = None
    await update.message.reply_text("✅ Attack stopped successfully!")

# Command to display help with Keyboard Buttons
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("/start"), KeyboardButton("/stop")],
         [KeyboardButton("/genkey"), KeyboardButton("/redeem")]],
        resize_keyboard=True,
    )
    response = (
        "Welcome to the Flooding Bot by @{Shsonu}! Here are the available commands:\n\n"
        "- /genkey <amount> <hours/days>: Generate a key with a specified validity period.\n"
        "- /redeem <key>: Redeem a key to gain access.\n"
        "- /start: Start the flooding process.\n"
        "- /stop: Stop the flooding process.\n"
    )
    await update.message.reply_text(response, reply_markup=keyboard)

# Main function
def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("genkey", genkey))
    application.add_handler(CommandHandler("redeem", redeem))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("help", help_command))

    load_data()
    application.run_polling()

if __name__ == '__main__':
    main()