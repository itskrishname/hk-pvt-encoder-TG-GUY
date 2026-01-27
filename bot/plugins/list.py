from pyrogram import filters
from bot import app, AUTH_USERS, BOT_USERNAME, data

@app.on_message(filters.command(["list", f"list@{BOT_USERNAME}"]) & filters.user(AUTH_USERS))
async def list_tasks(client, message):
    if not data:
        await message.reply_text("<blockquote>No active tasks in queue.</blockquote>")
        return

    text = "<b>📋 Active Task Queue:</b>\n\n"

    for i, item in enumerate(data):
        # data item structure: (message, mode) or message object directly in legacy cases?
        # We updated queue to store tuples (message, mode)
        if isinstance(item, tuple):
            msg_obj, mode = item
        else:
            msg_obj, mode = item, "Unknown"

        user = msg_obj.from_user.mention if msg_obj.from_user else "Unknown User"
        file_name = "Unknown File"

        if msg_obj.video:
            file_name = msg_obj.video.file_name or "Video"
        elif msg_obj.document:
            file_name = msg_obj.document.file_name or "Document"

        text += f"<b>{i+1}.</b> {user}\n   ├ <b>Mode:</b> {mode}\n   └ <b>File:</b> {file_name}\n\n"

    await message.reply_text(f"<blockquote>{text}</blockquote>")
