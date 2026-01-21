from pyrogram import filters
from bot import app, AUTH_USERS, BOT_USERNAME
from bot.helper.database import db

@app.on_message(filters.command(["auth", "a", f"auth@{BOT_USERNAME}", f"a@{BOT_USERNAME}"]) & filters.user(AUTH_USERS))
async def authorize_user(client, message):
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user.id if message.reply_to_message.from_user else None
    elif len(message.command) > 1:
        try:
            target = int(message.command[1])
        except ValueError:
            target = None

    if target is None:
        target = message.chat.id

    try:
        await db.add_auth_user(target)
        if target not in AUTH_USERS:
            AUTH_USERS.append(target)
        await message.reply_text(f"<blockquote>Authorized Successfully: {target}</blockquote>")
    except Exception as e:
        await message.reply_text(f"<blockquote>Error: {str(e)}</blockquote>")
