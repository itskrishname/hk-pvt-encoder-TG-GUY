import os
import sys
import subprocess
from datetime import datetime
from pyrogram import filters
import heroku3
from bot import app, AUTH_USERS, BOT_USERNAME
from bot.config import Config

def run_command(command):
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return True, result.decode("utf-8").strip()
    except subprocess.CalledProcessError as e:
        return False, e.output.decode("utf-8").strip()

def get_ordinal_date(dt):
    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(dt.day % 10 if dt.day % 10 < 4 and not 10 < dt.day % 100 < 20 else 0, 'th')
    return dt.strftime(f"%d{suffix} %b, %Y")

@app.on_message(filters.command(["update", f"update@{BOT_USERNAME}"]) & filters.user(AUTH_USERS))
async def update_bot(client, message):
    msg = await message.reply_text("Checking for updates...")

    try:
        # Fetch updates
        success, output = run_command("git fetch origin")
        if not success:
            await msg.edit(f"Error fetching updates:\n{output}")
            return

        # Get current branch
        success, branch = run_command("git rev-parse --abbrev-ref HEAD")
        if not success or not branch:
            await msg.edit("Could not determine current branch.")
            return

        # Check for updates
        success, count_str = run_command(f"git rev-list HEAD..origin/{branch} --count")
        if not success:
            await msg.edit(f"Error checking update count:\n{count_str}")
            return

        count = int(count_str) if count_str.isdigit() else 0

        if count == 0:
            await msg.edit("No updates available.")
            return

        # Get updates details
        # Format: hash|||message|||author|||timestamp
        success, logs = run_command(f'git log HEAD..origin/{branch} --pretty=format:"%h|||%s|||%an|||%ct"')
        if not success:
            await msg.edit(f"Error getting update logs:\n{logs}")
            return

        update_text = "ᴀ ɴᴇᴡ ᴜᴩᴅᴀᴛᴇ ɪs ᴀᴠᴀɪʟᴀʙʟᴇ ғᴏʀ ᴛʜᴇ ʙᴏᴛ !\n\n➓ ᴩᴜsʜɪɴɢ ᴜᴩᴅᴀᴛᴇs ɴᴏᴡ\n\nᴜᴩᴅᴀᴛᴇs:\n\n"

        for line in logs.split("\n"):
            if not line: continue
            parts = line.split("|||")
            if len(parts) == 4:
                chash, cmsg, author, timestamp = parts
                dt_obj = datetime.fromtimestamp(int(timestamp))
                date_str = get_ordinal_date(dt_obj)

                update_text += f"➓ #{chash}: {cmsg} ʙʏ -> {author}\n"
                update_text += f"    ➞ ᴄᴏᴍᴍɪᴛᴇᴅ ᴏɴ : {date_str}\n\n"

        await msg.edit(update_text)

        # Pull changes
        success, output = run_command(f"git pull origin {branch}")
        if not success:
            await msg.edit(f"Error pulling updates:\n{output}\n\nPlease resolve manually.")
            return

        # Install requirements if any
        success, output = run_command("pip install -r requirements.txt")
        if not success:
            await msg.edit(f"Error installing requirements:\n{output}\n\nBot will try to restart anyway.")

        # Check if Heroku vars are present and valid
        heroku_api = Config.HEROKU_API_KEY
        heroku_app_name = Config.HEROKU_APP_NAME

        is_heroku = False
        if heroku_api and heroku_app_name:
            if heroku_api != "0" and heroku_app_name != "0" and heroku_api.strip() and heroku_app_name.strip():
                is_heroku = True

        if is_heroku:
             final_text = update_text + "» ʙᴏᴛ ᴜᴩᴅᴀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ ! ɴᴏᴡ ᴡᴀɪᴛ ғᴏʀ ғᴇᴡ ᴍɪɴᴜᴛᴇs ᴜɴᴛɪʟ ᴛʜᴇ ʙᴏᴛ ʀᴇsᴛᴀʀᴛs ᴏɴ ʜᴇʀᴏᴋᴜ !"
             await msg.edit(final_text)

             try:
                 conn = heroku3.from_key(heroku_api)
                 app_conn = conn.app(heroku_app_name)
                 app_conn.restart()
             except Exception as e:
                 await msg.reply_text(f"Heroku restart failed: {str(e)}\nTrying local restart...")
                 os.execl(sys.executable, sys.executable, "-m", "bot")
        else:
            final_text = update_text + "» ʙᴏᴛ ᴜᴩᴅᴀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ ! ɴᴏᴡ ᴡᴀɪᴛ ғᴏʀ ғᴇᴡ ᴍɪɴᴜᴛᴇs ᴜɴᴛɪʟ ᴛʜᴇ ʙᴏᴛ ʀᴇsᴛᴀʀᴛs ᴀɴᴅ ᴩᴜsʜ ᴄʜᴀɴɢᴇs !"
            await msg.edit(final_text)

            # Restart
            os.execl(sys.executable, sys.executable, "-m", "bot")

    except Exception as e:
        await msg.edit(f"An error occurred: {str(e)}")
