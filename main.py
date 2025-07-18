import os
import time
import zipfile
import rarfile
from datetime import datetime, timedelta
from telegram import Update, ForceReply
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes
)

# CONFIG
BOT_TOKEN = "8145249462:AAHvrQEhXaW8O1-UkK4TPwg5pKiHk1VNCmw"
ADMIN_ID = 7695401278  # Replace with your Telegram user ID
CHANNELS = ["https://t.me/+2j4Bc7duxg8yYWI1", "https://t.me/+qLlrDUYrqOk3YWE1"]

# DATA STORE
USERS = {}
VALID_KEYS = {}
KEY_USAGE = {}  # key: user_id
STATS = {"total_users": 0, "key_uses": 0, "extracts": 0}
BANNED_USERS = set()

def check_channels(user):
    return True

def save_combo_by_domain(lines):
    domain_dict = {}
    for line in lines:
        parts = line.strip().split(":")
        if len(parts) >= 3 and "@" in parts[1]:
            domain = parts[1].split("@")[1]
            domain_dict.setdefault(domain, []).append(line)

    saved_files = []
    for domain, entries in domain_dict.items():
        filename = f"{domain}.txt"
        with open(filename, "w") as f:
            f.write("\n".join(entries))
            f.write(f"\n\nTotal line found:{len(entries)}")
            f.write("\nBot by @atoniz715")
        saved_files.append(filename)
    return saved_files

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in BANNED_USERS:
        return await update.message.reply_text("⛔ You are banned from using this bot.")
    if user.id not in USERS:
        USERS[user.id] = {"joined": True, "name": user.username or user.full_name}
        STATS["total_users"] += 1

    await update.message.reply_text(
        f"👋 Welcome, {user.first_name}!\n\n"
        "Before using this bot, please join the following channels:\n" +
        "\n".join([f"👉 {ch}" for ch in CHANNELS]) +
        "\n\nOnce done, you can use the following commands:\n"
        "/extract - Extract combos from ulps file\n"
        "/help - Show command list"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 Available Commands:\n"
        "/start - Start and get instructions\n"
        "/extract - Extract target combos from uploaded .zip or .rar file\n"
        "/help - Show this help message"
    )

async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("⛔ You are not allowed.")

    key = os.urandom(4).hex()
    VALID_KEYS[key] = datetime.now() + timedelta(days=1)
    await update.message.reply_text(f"✅ Key generated (valid 1 day): `{key}`", parse_mode="Markdown")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("⛔ Not allowed.")
    await update.message.reply_text(
        f"📊 Bot Stats:\n"
        f"Total Users: {STATS['total_users']}\n"
        f"Key Uses: {STATS['key_uses']}\n"
        f"Extractions: {STATS['extracts']}"
    )

async def all_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not USERS:
        await update.message.reply_text("❌ No users yet.")
        return
    msg = "👥 All Users:\n"
    for uid, data in USERS.items():
        msg += f"- ID: `{uid}` | Name: {data.get('name', 'Unknown')}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        return await update.message.reply_text("❗ Usage: /ban <user_id>")
    user_id = int(context.args[0])
    BANNED_USERS.add(user_id)
    await update.message.reply_text(f"✅ Banned user {user_id}")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        return await update.message.reply_text("❗ Usage: /unban <user_id>")
    user_id = int(context.args[0])
    BANNED_USERS.discard(user_id)
    await update.message.reply_text(f"✅ Unbanned user {user_id}")

async def keys_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not VALID_KEYS:
        return await update.message.reply_text("❌ No active keys.")
    msg = "🔐 Active Keys:\n"
    for k, exp in VALID_KEYS.items():
        user = KEY_USAGE.get(k, "Unused")
        msg += f"`{k}` → Expires: {exp.strftime('%Y-%m-%d %H:%M')} | Used by: {user}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def extract_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in BANNED_USERS:
        return await update.message.reply_text("⛔ You are banned from using this bot.")
    await update.message.reply_text("📤 Please send a `.zip` or `.rar` file containing ulps combo (url:login:pass)...")
    context.user_data["awaiting_file"] = True

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_file"):
        return

    file = update.message.document
    if not (file.file_name.endswith(".zip") or file.file_name.endswith(".rar")):
        return await update.message.reply_text("❌ Only .zip or .rar files are supported!")

    user = update.effective_user
    context.user_data["awaiting_file"] = False
    STATS["extracts"] += 1

    await update.message.reply_text("📥 Downloading file...")
    new_file = await file.get_file()
    downloaded = f"{file.file_id}_{file.file_name}"
    await new_file.download_to_drive(downloaded)

    await update.message.reply_text("🛠️ Extracting combo from file...")
    lines = []
    try:
        if downloaded.endswith(".zip"):
            with zipfile.ZipFile(downloaded, 'r') as zf:
                for name in zf.namelist():
                    with zf.open(name) as f:
                        lines += [l.decode("utf-8", errors="ignore") for l in f.readlines()]
        else:
            with rarfile.RarFile(downloaded) as rf:
                for name in rf.namelist():
                    with rf.open(name) as f:
                        lines += [l.decode("utf-8", errors="ignore") for l in f.readlines()]
    except Exception as e:
        return await update.message.reply_text(f"❌ Error extracting: {str(e)}")

    result_files = save_combo_by_domain(lines)
    for file in result_files:
        await update.message.reply_document(document=open(file, "rb"))
        os.remove(file)

    os.remove(downloaded)
    await update.message.reply_text("✅ Done extracting combos!")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("genkey", genkey))
    app.add_handler(CommandHandler("extract", extract_cmd))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("all", all_users))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("keys", keys_list))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
