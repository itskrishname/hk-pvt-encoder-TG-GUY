from pyrogram import filters
from bot import app, AUTH_USERS, BOT_USERNAME
from bot.helper.database import db

@app.on_message(filters.command(["unauth", "un", f"unauth@{BOT_USERNAME}", f"un@{BOT_USERNAME}"]) & filters.user(AUTH_USERS))
async def unauthorize_user(client, message):
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user.id if message.reply_to_message.from_user else None
    elif len(message.command) > 1:
        try:
            target = int(message.command[1])
        except ValueError:
            target = None

    if target is None:
        await message.reply_text("<blockquote>Please reply to a user or provide an ID to unauthorize.</blockquote>")
        return

    try:
        await db.remove_auth_user(target)
        if target in AUTH_USERS:
            AUTH_USERS.remove(target)
        await message.reply_text(f"<blockquote>Unauthorized Successfully: {target}</blockquote>")
    except Exception as e:
        await message.reply_text(f"<blockquote>Error: {str(e)}</blockquote>")
