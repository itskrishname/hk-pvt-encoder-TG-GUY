import datetime
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
LOGGER = logging.getLogger(__name__)
import os, time, asyncio, json
from bot.localisation import Localisation
from bot import (
  DOWNLOAD_LOCATION, 
  AUTH_USERS,
  LOG_CHANNEL,
  UPDATES_CHANNEL,
  SESSION_NAME,
  data,
  app  
)
from bot.helper_funcs.ffmpeg import (
  convert_video,
  media_info,
  take_screen_shot
)
from bot.helper_funcs.display_progress import (
  progress_for_pyrogram,
  TimeFormatter,
  humanbytes
)

from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, UsernameNotOccupied, ChatAdminRequired, PeerIdInvalid


os.system("wget https://files.catbox.moe/6ntaju.png -O thumb.jpg")

CURRENT_PROCESSES = {}
CHAT_FLOOD = {}
broadcast_ids = {}
bot = app

async def incoming_start_message_f(bot, update):
    """/start command"""
    
    await bot.send_message(
        chat_id=update.chat.id,
        text=Localisation.START_TEXT,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton('👨‍💻 Oᴡɴᴇʀ 👨‍💻', url='https://t.me/itsme123c')
                ]
            ]
        ),
        reply_to_message_id=update.id,
    )

async def incoming_compress_message_f(update):
    """/compress command"""

    if not (update.video or update.document):
        await update.reply_text("<blockquote>Please send a video or document to compress.</blockquote>")
        return

    d_start = time.time()
    status = os.path.join(DOWNLOAD_LOCATION, "status.json")

    sent_message = await bot.send_message(
        chat_id=update.chat.id,
        text=Localisation.DOWNLOAD_START,
        reply_to_message_id=update.id
    )
    utc_now = datetime.datetime.utcnow()
    ist_now = utc_now + datetime.timedelta(minutes=30, hours=5)
    ist = ist_now.strftime("%d/%m/%Y, %H:%M:%S")
    bst_now = utc_now + datetime.timedelta(minutes=0, hours=6)
    bst = bst_now.strftime("%d/%m/%Y, %H:%M:%S")
    now = f"\n{ist} (GMT+05:30)\n{bst} (GMT+06:00)"
    download_start = await bot.send_message(
        chat_id=LOG_CHANNEL,
        text=f"<blockquote>**𝙱𝚘𝚝 𝙱𝚎𝚌𝚘𝚖𝚎 𝙱𝚞𝚜𝚢 𝙽𝚘𝚠...**{now}</blockquote>"
    )

    file_name = update.video.file_name if update.video else update.document.file_name
    if not file_name:
        file_name = f"{update.id}.mkv"
    extension = file_name.split('.')[-1] if '.' in file_name else 'mkv'
    download_path = os.path.join(DOWNLOAD_LOCATION, file_name)

    try:
        video = await bot.download_media(
            message=update,
            file_name=download_path,
            progress=progress_for_pyrogram,
            progress_args=(bot, Localisation.DOWNLOAD_START, sent_message, d_start)
        )
        if not video or not os.path.exists(video):
            await sent_message.edit_text("Download Stopped")
            await bot.send_message(LOG_CHANNEL, f"<blockquote>**File Download Stopped**{now}</blockquote>")
            await download_start.delete()
            return
    except Exception as e:
        LOGGER.error(f"Download failed: {e}")
        await sent_message.edit_text(f"<blockquote>Error: {str(e)}</blockquote>")
        await bot.send_message(LOG_CHANNEL, f"<blockquote>**File Download Error!**{now}</blockquote>")
        await download_start.delete()
        return

    await sent_message.edit_text(Localisation.SAVED_RECVD_DOC_FILE)

    duration, bitrate = await media_info(video)
    if duration is None or bitrate is None:
        LOGGER.error("Failed to get video metadata")
        await sent_message.edit_text("Getting Video Meta Data Failed")
        await bot.send_message(LOG_CHANNEL, f"<blockquote>**File Download Failed**{now}</blockquote>")
        await download_start.delete()
        if os.path.exists(video):
            os.remove(video)
        return

    thumb_image_path = await take_screen_shot(
        video,
        os.path.dirname(os.path.abspath(video)),
        duration / 2
    )

    await download_start.delete()
    compress_start = await bot.send_message(
        chat_id=LOG_CHANNEL,
        text=f"<blockquote>**Encoding Video...**{now}</blockquote>"
    )
    await sent_message.edit_text(Localisation.COMPRESS_START)

    with open(status, 'w') as f:
        json.dump({"running": True, "message": sent_message.id}, f, indent=2)

    c_start = time.time()
    encoded_file = await convert_video(
        video_file=video,
        output_directory=DOWNLOAD_LOCATION,
        total_time=duration,
        bot=bot,
        message=sent_message,
        chan_msg=compress_start
    )

    compressed_time = TimeFormatter((time.time() - c_start) * 1000)
    if not encoded_file or not os.path.exists(encoded_file):
        LOGGER.error("Compression failed")
        await sent_message.edit_text("Compression Failed")
        await bot.send_message(LOG_CHANNEL, f"<blockquote>**Video Compression Failed**{now}</blockquote>")
        await compress_start.delete()
        if os.path.exists(video):
            os.remove(video)
        return

    u_start = time.time()
    await compress_start.delete()
    upload_start = await bot.send_message(
        chat_id=LOG_CHANNEL,
        text=f"<blockquote>**Uploading Video on TG...**{now}</blockquote>"
    )
    await sent_message.edit_text(Localisation.UPLOAD_START)

    caption = update.caption if update.caption else "Encoded by @Animes_Guy"

    # === AUTO-RETRY UPLOAD (3 TIMES) ===
    max_retries = 3
    uploaded = False
    for attempt in range(1, max_retries + 1):
        try:
            await sent_message.edit_text(f"{Localisation.UPLOAD_START}\n\nRetry {attempt}/{max_retries}...")
            upload = await bot.send_document(
                chat_id=update.chat.id,
                document=encoded_file,
                caption=caption,
                force_document=True,
                thumb=thumb_image_path if os.path.exists(thumb_image_path) else "thumb.jpg",
                reply_to_message_id=update.id,
                progress=progress_for_pyrogram,
                progress_args=(bot, Localisation.UPLOAD_START, sent_message, u_start)
            )
            if upload:
                uploaded = True
                break
        except Exception as e:
            LOGGER.error(f"Upload attempt {attempt} failed: {e}")
            if attempt < max_retries:
                await asyncio.sleep(5 * attempt)  # 5s, 10s, 20s
                await bot.send_message(LOG_CHANNEL, f"<blockquote>**Upload Retry {attempt}/{max_retries}...**{now}</blockquote>")
            else:
                await sent_message.edit_text(f"<blockquote>Upload Failed After {max_retries} Attempts\nError: {str(e)}</blockquote>")
                await bot.send_message(LOG_CHANNEL, f"<blockquote>**File Upload Failed After {max_retries} Tries**{now}</blockquote>")

    if not uploaded:
        await upload_start.delete()
        if os.path.exists(video):
            os.remove(video)
        if os.path.exists(encoded_file):
            os.remove(encoded_file)
        return

    # === SUCCESS ===
    uploaded_time = TimeFormatter((time.time() - u_start) * 1000)
    await sent_message.delete()
    await upload_start.delete()
    await bot.send_message(
        chat_id=LOG_CHANNEL,
        text=f"<blockquote>**ENCODED UPLOAD Done**{now}</blockquote>"
    )

    try:
        await upload.edit_caption(
            caption=f"{caption}\n\n🕛 <b>Compressed in:</b> {compressed_time}\n📤 <b>Uploaded in:</b> {uploaded_time}"
        )
    except:
        pass

    if os.path.exists(video):
        os.remove(video)
    if os.path.exists(encoded_file):
        os.remove(encoded_file)
    if os.path.exists(thumb_image_path):
        os.remove(thumb_image_path)

async def incoming_cancel_message_f(bot, update):
  """/cancel command"""
  #if update.from_user.id != 1391975600 or 888605132 or 1760568371:
  if update.from_user.id not in AUTH_USERS:      
        
    try:
      await update.message.delete()
    except:
      pass
    return

  status = DOWNLOAD_LOCATION + "/status.json"
  if os.path.exists(status):
    inline_keyboard = []
    ikeyboard = []
    ikeyboard.append(InlineKeyboardButton("Yᴇꜱ 🚫", callback_data=("fuckingdo").encode("UTF-8")))
    ikeyboard.append(InlineKeyboardButton("Nᴏ 🤗", callback_data=("fuckoff").encode("UTF-8")))
    inline_keyboard.append(ikeyboard)
    reply_markup = InlineKeyboardMarkup(inline_keyboard)
    await update.reply_text("Aʀᴇ Yᴏᴜ Sᴜʀᴇ? 🚫 Tʜɪꜱ ᴡɪʟʟ Sᴛᴏᴘ ᴛʜᴇ Cᴏᴍᴘʀᴇꜱꜱɪᴏɴ!", reply_markup=reply_markup, quote=True)
  else:
   # delete_downloads()
    await bot.send_message(
      chat_id=update.chat.id,
      text="<blockquote>No active compression exists</blockquote>",
      reply_to_message_id=update.id
    )
