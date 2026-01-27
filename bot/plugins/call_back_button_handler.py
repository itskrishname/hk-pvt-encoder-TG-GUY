from bot.helper_funcs.utils import on_task_complete, add_task
from bot import (
    AUTH_USERS,
    DOWNLOAD_LOCATION,
    LOG_CHANNEL,
    data,
    pid_list,
    LOG_FILE_ZZGEVC,
    user_states
)
from pyrogram.types import CallbackQuery
import datetime
import logging
import os, signal
import json
import shutil
from bot.plugins.incoming_message_fn import process_encoding, bot

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
LOGGER = logging.getLogger(__name__)

#from bot.helper_funcs.admin_check import AdminCheck


async def button(bot, update: CallbackQuery):
    cb_data = update.data
    try:
        g = await AdminCheck(bot, update.message.chat.id, update.from_user.id)
        print(g)
    except:
        pass
    LOGGER.info(update.message.reply_to_message.from_user.id)
    if (update.from_user.id == update.message.reply_to_message.from_user.id) or g:
        print(cb_data)

        if cb_data == "log_file":
            if update.from_user.id in AUTH_USERS:
                await update.message.reply_document(LOG_FILE_ZZGEVC)
                await update.message.delete()
            else:
                await update.answer("Not Authorized", show_alert=True)

        elif cb_data == "log_text":
            if update.from_user.id in AUTH_USERS:
                with open(LOG_FILE_ZZGEVC, "r") as f:
                    content = f.read()
                if len(content) > 4000:
                    content = content[-4000:]
                    content = f"...\n{content}"
                await update.message.reply_text(f"<blockquote>{content}</blockquote>")
                await update.message.delete()
            else:
                await update.answer("Not Authorized", show_alert=True)

        elif cb_data.startswith("enc_"):
            if update.from_user.id in AUTH_USERS:
                mode_map = {
                    "enc_480": "480p",
                    "enc_720": "720p",
                    "enc_1080": "1080p"
                }
                mode = mode_map.get(cb_data)
                if mode:
                    await update.message.edit_text(f"Queueing for {mode}...")
                    # Pass the original message (reply_to_message) which contains the file
                    # We need to call process_encoding with the original message
                    original_message = update.message.reply_to_message
                    if original_message:
                        data.append((original_message, mode))
                        if len(data) == 1:
                             await add_task(original_message, mode)
                    else:
                        await update.message.edit_text("Original message not found.")
            else:
                await update.answer("Not Authorized", show_alert=True)

        elif cb_data.startswith("edit_"):
            if update.from_user.id in AUTH_USERS:
                # edit_crf_720p or edit_crf or edit_audio_b_1080p
                raw_setting = cb_data[5:] # Remove "edit_"

                mode = None
                setting = raw_setting

                if raw_setting.endswith("_720p"):
                    mode = "720p"
                    setting = raw_setting[:-6] # Remove "_720p" (length 5) -> wait, "_720p" length is 5
                elif raw_setting.endswith("_1080p"):
                    mode = "1080p"
                    setting = raw_setting[:-7] # Remove "_1080p" (length 6) -> wait, "_1080p" len 6

                # Double check length stripping
                if mode == "720p":
                     setting = raw_setting[:-5]
                elif mode == "1080p":
                     setting = raw_setting[:-6]

                user_states[update.from_user.id] = {"setting": setting, "mode": mode}
                mode_str = mode if mode else "default/480p"
                await update.message.reply_text(f"Send new value for {setting} ({mode_str}):")
            else:
                await update.answer("Not Authorized", show_alert=True)

        elif cb_data == "fuckingdo":
            if update.from_user.id in AUTH_USERS:
                status = DOWNLOAD_LOCATION + "/status.json"
                with open(status, 'r+') as f:
                    statusMsg = json.load(f)
                    statusMsg['running'] = False
                    f.seek(0)
                    json.dump(statusMsg, f, indent=2)
                    if 'pid' in statusMsg.keys():
                        try:
                            os.kill(statusMsg["pid"], signal.SIGSTOP)
                            os.kill(pid_list[0], signal.SIGSTOP) 
                            del pid_list[0]
                            os.system("rm -rf downloads/*")
                            await bot.delete_messages(update.message.chat.id, statusMsg["message"])
                            #await on_task_complete()
                        except Exception as e:
                            print(e)
                            pass
                        
                        chat_id = LOG_CHANNEL
                        utc_now = datetime.datetime.utcnow()
                        ist_now = utc_now + \
                            datetime.timedelta(minutes=30, hours=5)
                        ist = ist_now.strftime("%d/%m/%Y, %H:%M:%S")
                        bst_now = utc_now + \
                            datetime.timedelta(minutes=00, hours=6)
                        bst = bst_now.strftime("%d/%m/%Y, %H:%M:%S")
                        now = f"\n{ist} (GMT+05:30)`\n`{bst} (GMT+06:00)"
                        await bot.send_message(chat_id, f"<blockquote>**𝙻𝚊𝚜𝚝 𝙿𝚛𝚘𝚌𝚎𝚜𝚜 𝙲𝚊𝚗𝚌𝚎𝚕𝚕𝚎𝚍.\n.....𝙱𝚘𝚝 𝚒𝚜 𝙵𝚛𝚎𝚎 𝙽𝚘𝚠.....🥀**</blockquote>")
            else:
                try:
                    await update.message.edit_text("<blockquote>Yᴏᴜ ᴀʀᴇ Nᴏᴛ Aʟʟᴏᴡᴇᴅ ᴛᴏ ᴅᴏ Tʜᴀᴛ 🤭</blockquote>")
                except:
                    pass

        elif cb_data == "fuckoff":
            try:
                await update.message.edit_text("Oᴋᴀʏ! Fɪɴᴇ ☠️")
            except:
                pass
