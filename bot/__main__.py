import logging
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("motor").setLevel(logging.WARNING)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)

import os
import asyncio
import platform
from datetime import datetime as dt

import pyrogram
import psutil
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message
from psutil import disk_usage, cpu_percent, virtual_memory, Process as psprocess

from bot import (
    APP_ID,
    API_HASH,
    AUTH_USERS,
    DOWNLOAD_LOCATION,
    LOGGER,
    TG_BOT_TOKEN,
    BOT_USERNAME,
    SESSION_NAME,
    data,
    app,
    user_states
)
from bot.helper_funcs.utils import add_task, on_task_complete, sysinfo
from bot.helper_funcs.set_commands import set_bot_commands
from bot.plugins.incoming_message_fn import (
    incoming_start_message_f,
    incoming_compress_message_f,
    incoming_cancel_message_f
)
from bot.plugins.status_message_fn import (
    eval_message_f,
    exec_message_f,
    upload_log_file
)
from bot.commands import Command
from bot.plugins.call_back_button_handler import button
import bot.plugins.update
import bot.plugins.authorize
from bot.helper.database import db
from pyrogram.errors import FloodWait
from pymongo.errors import PyMongoError

logging.basicConfig(    
    level=logging.INFO,    
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",    
    handlers=[logging.StreamHandler()]    
)    
logger = logging.getLogger(__name__)    

# ----------------------------------------------------------------------
# Global vars
# ----------------------------------------------------------------------
sudo_users = "7660990923"          # <-- sudo user ID
uptime = dt.now()

def ts(milliseconds: int) -> str:    
    seconds, milliseconds = divmod(int(milliseconds), 1000)    
    minutes, seconds = divmod(seconds, 60)    
    hours, minutes = divmod(minutes, 60)    
    days, hours = divmod(hours, 24)    
    tmp = (    
        ((str(days) + "d, ") if days else "")    
        + ((str(hours) + "h, ") if hours else "")    
        + ((str(minutes) + "m, ") if minutes else "")    
        + ((str(seconds) + "s, ") if seconds else "")    
        + ((str(milliseconds) + "ms") if milliseconds else "")    
    )    
    return tmp.rstrip(", ")

# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
#  ALL YOUR HANDLERS (unchanged)
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------

# create download directory, if not exist    
if not os.path.isdir(DOWNLOAD_LOCATION):    
    os.makedirs(DOWNLOAD_LOCATION)    

# START command    
incoming_start_message_handler = MessageHandler(    
    incoming_start_message_f,    
    filters=filters.command(["start", f"start@{BOT_USERNAME}"])    
)    
app.add_handler(incoming_start_message_handler)    

# --- Helper to parse command suffix ---
def get_mode_from_command(command_str):
    if command_str.endswith("1"):
        return "720p"
    if command_str.endswith("2"):
        return "1080p"
    return None

# ------------------- CRF -------------------
@app.on_message(filters.incoming & filters.command(["crf", "crf1", "crf2"]))
async def changecrf(app, message):    
    if message.from_user.id in AUTH_USERS:
        mode = get_mode_from_command(message.command[0])
        try:    
            cr = message.text.split(" ", maxsplit=1)[1]    
            cr_int = int(cr)    
            await db.set_crf(cr_int, mode)
            mode_str = mode if mode else "default/480p"
            OUT = f"<blockquote>I will be using : {cr} crf for {mode_str}</blockquote>"
            await message.reply_text(OUT)    
        except IndexError:    
            await message.reply_text("<blockquote>Please provide a CRF value, e.g., /crf 24</blockquote>")    
        except ValueError:    
            await message.reply_text("<blockquote>CRF must be an integer, e.g., 24</blockquote>")    
        except PyMongoError as e:    
            await message.reply_text("<blockquote>Database error: Could not save CRF value. Please try again later.</blockquote>")    
            logger.error(f"DB Error in /crf: {e}")    
        except FloodWait as e:    
            await asyncio.sleep(e.value)    
            await message.reply_text("<blockquote>Rate limit hit, please try again shortly.</blockquote>")    
        except Exception as e:    
            await message.reply_text("<blockquote>An unexpected error occurred. Please try again.</blockquote>")    
            logger.error(f"Unexpected error in /crf: {e}")    
    else:    
        await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ</blockquote>")    

# ------------------- RESOLUTION -------------------
@app.on_message(filters.incoming & filters.command(["resolution", "resolution1", "resolution2"]))
async def changer(app, message):    
    if message.from_user.id in AUTH_USERS:
        mode = get_mode_from_command(message.command[0])
        try:    
            res = message.text.split(" ", maxsplit=1)[1]    
            await db.set_resolution(res, mode)
            mode_str = mode if mode else "default/480p"
            OUT = f"<blockquote>I will be using : {res} for {mode_str}</blockquote>"
            await message.reply_text(OUT)    
        except IndexError:    
            await message.reply_text("<blockquote>Please provide a resolution value, e.g., /resolution 640x360</blockquote>")    
        except PyMongoError as e:    
            await message.reply_text("<blockquote>Database error: Could not save resolution value. Please try again later.</blockquote>")    
            logger.error(f"DB Error in /resolution: {e}")    
        except FloodWait as e:    
            await asyncio.sleep(e.value)    
            await message.reply_text("<blockquote>Rate limit hit, please try again shortly.</blockquote>")    
        except Exception as e:    
            await message.reply_text("<blockquote>An unexpected error occurred. Please try again.</blockquote>")    
            logger.error(f"Unexpected error in /resolution: {e}")    
    else:    
        await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ</blockquote>")    

# ------------------- PRESET -------------------
@app.on_message(filters.incoming & filters.command(["preset", "preset1", "preset2"]))
async def changepr(app, message):    
    if message.from_user.id in AUTH_USERS:
        mode = get_mode_from_command(message.command[0])
        try:    
            preset_val = message.text.split(" ", maxsplit=1)[1]    
            await db.set_preset(preset_val, mode)
            mode_str = mode if mode else "default/480p"
            OUT = f"<blockquote>I will be using : {preset_val} preset for {mode_str}</blockquote>"
            await message.reply_text(OUT)    
        except IndexError:    
            await message.reply_text("<blockquote>Please provide a preset value, e.g., /preset veryfast</blockquote>")    
        except PyMongoError as e:    
            await message.reply_text("<blockquote>Database error: Could not save preset value. Please try again later.</blockquote>")    
            logger.error(f"DB Error in /preset: {e}")    
        except FloodWait as e:    
            await asyncio.sleep(e.value)    
            await message.reply_text("<blockquote>Rate limit hit, please try again shortly.</blockquote>")    
        except Exception as e:    
            await message.reply_text("<blockquote>An unexpected error occurred. Please try again.</blockquote>")    
            logger.error(f"Unexpected error in /preset: {e}")    
    else:    
        await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ</blockquote>")    

# ------------------- V_CODEC -------------------
@app.on_message(filters.incoming & filters.command(["v_codec", "v_codec1", "v_codec2"]))
async def changevcodec(app, message):    
    if message.from_user.id in AUTH_USERS:
        mode = get_mode_from_command(message.command[0])
        try:    
            codec_val = message.text.split(" ", maxsplit=1)[1]    
            await db.set_video_codec(codec_val, mode)
            mode_str = mode if mode else "default/480p"
            OUT = f"<blockquote>I will be using : {codec_val} video codec for {mode_str}</blockquote>"
            await message.reply_text(OUT)    
        except IndexError:    
            await message.reply_text("<blockquote>Please provide a video codec value, e.g., /v_codec libx264</blockquote>")    
        except PyMongoError as e:    
            await message.reply_text("<blockquote>Database error: Could not save video codec value. Please try again later.</blockquote>")    
            logger.error(f"DB Error in /v_codec: {e}")    
        except FloodWait as e:    
            await asyncio.sleep(e.value)    
            await message.reply_text("<blockquote>Rate limit hit, please try again shortly.</blockquote>")    
        except Exception as e:    
            await message.reply_text("<blockquote>An unexpected error occurred. Please try again.</blockquote>")    
            logger.error(f"Unexpected error in /v_codec: {e}")    
    else:    
        await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ</blockquote>")    

# ------------------- A_CODEC -------------------
@app.on_message(filters.incoming & filters.command(["a_codec", "a_codec1", "a_codec2"]))
async def changeacodec(app, message):    
    if message.from_user.id in AUTH_USERS:
        mode = get_mode_from_command(message.command[0])
        try:    
            codec_val = message.text.split(" ", maxsplit=1)[1]    
            await db.set_audio_codec(codec_val, mode)
            mode_str = mode if mode else "default/480p"
            OUT = f"<blockquote>I will be using : {codec_val} audio codec for {mode_str}</blockquote>"
            await message.reply_text(OUT)    
        except IndexError:    
            await message.reply_text("<blockquote>Please provide an audio codec value, e.g., /a_codec aac</blockquote>")    
        except PyMongoError as e:    
            await message.reply_text("<blockquote>Database error: Could not save audio codec value. Please try again later.</blockquote>")    
            logger.error(f"DB Error in /a_codec: {e}")    
        except FloodWait as e:    
            await asyncio.sleep(e.value)    
            await message.reply_text("<blockquote>Rate limit hit, please try again shortly.</blockquote>")    
        except Exception as e:    
            await message.reply_text("<blockquote>An unexpected error occurred. Please try again.</blockquote>")    
            logger.error(f"Unexpected error in /a_codec: {e}")    
    else:    
        await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ</blockquote>")    

# ------------------- AUDIO_B -------------------
@app.on_message(filters.incoming & filters.command(["audio_b", "audio_b1", "audio_b2"]))
async def changeab(app, message):    
    if message.from_user.id in AUTH_USERS:
        mode = get_mode_from_command(message.command[0])
        try:    
            aud = message.text.split(" ", maxsplit=1)[1]    
            await db.set_audio_b(aud, mode)
            mode_str = mode if mode else "default/480p"
            OUT = f"<blockquote>I will be using : {aud} audio bitrate for {mode_str}</blockquote>"
            await message.reply_text(OUT)    
        except IndexError:    
            await message.reply_text("<blockquote>Please provide an audio bitrate value, e.g., /audio_b 64k</blockquote>")    
        except PyMongoError as e:    
            await message.reply_text("<blockquote>Database error: Could not save audio bitrate value. Please try again later.</blockquote>")    
            logger.error(f"DB Error in /audio_b: {e}")    
        except FloodWait as e:    
            await asyncio.sleep(e.value)    
            await message.reply_text("<blockquote>Rate limit hit, please try again shortly.</blockquote>")    
        except Exception as e:    
            await message.reply_text("<blockquote>An unexpected error occurred. Please try again.</blockquote>")    
            logger.error(f"Unexpected error in /audio_b: {e}")    
    else:    
        await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ</blockquote>")    

# ------------------- V_BITRATE -------------------
@app.on_message(filters.incoming & filters.command(["v_bitrate", "v_bitrate1", "v_bitrate2"]))
async def changevbitrate(app, message):    
    if message.from_user.id in AUTH_USERS:
        mode = get_mode_from_command(message.command[0])
        try:    
            br = message.text.split(" ", maxsplit=1)[1]    
            br_int = int(br)    
            await db.set_video_bitrate(br_int, mode)
            display = "no video bitrate (auto)" if br_int == 0 else f"{br_int}"    
            mode_str = mode if mode else "default/480p"
            OUT = f"<blockquote>I will be using : {display} video bitrate for {mode_str}</blockquote>"
            await message.reply_text(OUT)    
        except IndexError:    
            await message.reply_text("<blockquote>Please provide a video bitrate value, e.g., /v_bitrate 1000 (or 0 for none/auto)</blockquote>")    
        except ValueError:    
            await message.reply_text("<blockquote>Video bitrate must be an integer, e.g., 1000 or 0</blockquote>")    
        except PyMongoError as e:    
            await message.reply_text("<blockquote>Database error: Could not save video bitrate value. Please try again later.</blockquote>")    
            logger.error(f"DB Error in /v_bitrate: {e}")    
        except FloodWait as e:    
            await asyncio.sleep(e.value)    
            await message.reply_text("<blockquote>Rate limit hit, please try again shortly.</blockquote>")    
        except Exception as e:    
            await message.reply_text("<blockquote>An unexpected error occurred. Please try again.</blockquote>")    
            logger.error(f"Unexpected error in /v_bitrate: {e}")    
    else:    
        await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ</blockquote>")    

# ------------------- BITS -------------------
@app.on_message(filters.incoming & filters.command(["bits", "bits1", "bits2"]))
async def changebits(app, message):    
    if message.from_user.id in AUTH_USERS:
        mode = get_mode_from_command(message.command[0])
        try:    
            bits_val = message.text.split(" ", maxsplit=1)[1]    
            if bits_val not in ["8", "10"]:    
                await message.reply_text("<blockquote>Bits must be either 8 or 10, e.g., /bits 10</blockquote>")    
                return    
            await db.set_bits(bits_val, mode)
            mode_str = mode if mode else "default/480p"
            OUT = f"<blockquote>I will be using : {bits_val}-bit video encoding for {mode_str}</blockquote>"
            await message.reply_text(OUT)    
        except IndexError:    
            await message.reply_text("<blockquote>Please provide a bits value, e.g., /bits 10</blockquote>")    
        except PyMongoError as e:    
            await message.reply_text("<blockquote>Database error: Could not save bits value. Please try again later.</blockquote>")    
            logger.error(f"DB Error in /bits: {e}")    
        except FloodWait as e:    
            await asyncio.sleep(e.value)    
            await message.reply_text("<blockquote>Rate limit hit, please try again shortly.</blockquote>")    
        except Exception as e:    
            await message.reply_text("<blockquote>An unexpected error occurred. Please try again.</blockquote>")    
            logger.error(f"Unexpected error in /bits: {e}")    
    else:    
        await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ</blockquote>")     

# ------------------- WATERMARK -------------------
@app.on_message(filters.incoming & filters.command(["watermark", "watermark1", "watermark2"]))
async def changewatermark(app, message):    
    if message.from_user.id in AUTH_USERS:
        mode = get_mode_from_command(message.command[0])
        try:    
            wm = message.text.split(" ", maxsplit=1)[1]    
            if wm.strip().lower() in ["0", "none", ""]:    
                await db.set_watermark(0, mode)
                mode_str = mode if mode else "default/480p"
                OUT = f"<blockquote>I will be using : no watermark for {mode_str}</blockquote>"
            else:    
                await db.set_watermark(wm, mode)
                mode_str = mode if mode else "default/480p"
                OUT = f"<blockquote>I will be using : {wm} as watermark for {mode_str}</blockquote>"
            await message.reply_text(OUT)    
        except IndexError:    
            await message.reply_text("<blockquote>Please provide a watermark value, e.g., /watermark My Text Here (or 0/none for no watermark)</blockquote>")    
        except PyMongoError as e:    
            await message.reply_text("<blockquote>Database error: Could not save watermark value. Please try again later.</blockquote>")    
            logger.error(f"DB Error in /watermark: {e}")    
        except FloodWait as e:    
            await asyncio.sleep(e.value)    
            await message.reply_text("<blockquote>Rate limit hit, please try again shortly.</blockquote>")    
        except Exception as e:    
            await message.reply_text("<blockquote>An unexpected error occurred. Please try again.</blockquote>")    
            logger.error(f"Unexpected error in /watermark: {e}")    
    else:    
        await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ</blockquote>")    

@app.on_message(filters.incoming & filters.command(["size", "size1", "size2"]))
async def changecrf(app, message):    
    if message.from_user.id in AUTH_USERS:
        mode = get_mode_from_command(message.command[0])
        try:    
            wm_size = message.text.split(" ", maxsplit=1)[1]    
            wm_int = int(wm_size)    
            await db.set_size(wm_int, mode)
            mode_str = mode if mode else "default/480p"
            OUT = f"<blockquote>I will be using : {wm_size} for watermark text size for {mode_str}</blockquote>"
            await message.reply_text(OUT)    
        except IndexError:    
            await message.reply_text("<blockquote>Please provide a size value, e.g., /size 24</blockquote>")    
        except ValueError:    
            await message.reply_text("<blockquote>wm size must be an integer, e.g., 24</blockquote>")    
        except PyMongoError as e:    
            await message.reply_text("<blockquote>Database error: Could not save size value. Please try again later.</blockquote>")    
            logger.error(f"DB Error in /size: {e}")    
        except FloodWait as e:    
            await asyncio.sleep(e.value)    
            await message.reply_text("<blockquote>Rate limit hit, please try again shortly.</blockquote>")    
        except Exception as e:    
            await message.reply_text("<blockquote>An unexpected error occurred. Please try again.</blockquote>")    
            logger.error(f"Unexpected error in /size: {e}")    
    else:    
        await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ</blockquote>")    
    
# ------------------- SETTINGS -------------------
@app.on_message(filters.incoming & filters.command(["settings", "settings1", "settings2"]))
async def settings(app, message):    
    if message.from_user.id in AUTH_USERS:
        mode = None
        if message.command[0].endswith("1"):
            mode = "720p"
        elif message.command[0].endswith("2"):
            mode = "1080p"

        try:    
            crf_val = await db.get_crf(mode)
            preset_val = await db.get_preset(mode)
            resolution_val = await db.get_resolution(mode)
            audio_b_val = await db.get_audio_b(mode)
            audio_codec_val = await db.get_audio_codec(mode)
            video_codec_val = await db.get_video_codec(mode)
            video_bitrate_val = await db.get_video_bitrate(mode)
            watermark_val = await db.get_watermark(mode)
            bits_val = await db.get_bits(mode)
            size_val = await db.get_size(mode)

            video_bitrate_display = "Auto/None" if video_bitrate_val is None else f"{video_bitrate_val}"    
            watermark_display = "None" if watermark_val is None else f"{watermark_val}"
            mode_display = mode if mode else "480p (Default)"

            reply_text = (    
                f"<b>Tʜᴇ Cᴜʀʀᴇɴᴛ Sᴇᴛᴛɪɴɢꜱ ᴡɪʟʟ ʙᴇ Aᴅᴅᴇᴅ Yᴏᴜʀ Vɪᴅᴇᴏ Fɪʟᴇ ({mode_display}):</b>\n"
                f"<blockquote><b>Video Codec</b> : <code>{video_codec_val}</code> \n"    
                f"<b>Audio Codec</b> : <code>{audio_codec_val}</code> \n"    
                f"<b>Crf</b> : <code>{crf_val}</code> \n"    
                f"<b>Resolution</b> : <code>{resolution_val}</code> \n"    
                f"<b>Preset</b> : <code>{preset_val}</code> \n"    
                f"<b>Audio Bitrate</b> : <code>{audio_b_val}</code> \n"    
                f"<b>Video Bitrate</b> : <code>{video_bitrate_display}</code> \n"    
                f"<b>Bits</b> : <code>{bits_val} bits</code> \n"    
                f"<b>Watermark</b> : <code>{watermark_display}</code></blockquote>\n"
                f"<b>WM Size</b> : <code>{size_val}</code> \n"
                f"<b>The Ability to Change Settings is Only for Admin</b>"    
            )    

            # Interactive buttons
            m_suffix = f"_{mode}" if mode else ""
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Edit CRF", callback_data=f"edit_crf{m_suffix}"),
                    InlineKeyboardButton("Edit Resolution", callback_data=f"edit_resolution{m_suffix}")
                ],
                [
                    InlineKeyboardButton("Edit Preset", callback_data=f"edit_preset{m_suffix}"),
                    InlineKeyboardButton("Edit Audio Bitrate", callback_data=f"edit_audio_b{m_suffix}")
                ]
            ])

            await message.reply_text(reply_text, reply_markup=keyboard)
        except PyMongoError as e:    
            await message.reply_text("<blockquote>Database error: Could not retrieve settings. Please try again later.</blockquote>")    
            logger.error(f"DB Error in /settings: {e}")    
        except FloodWait as e:    
            await asyncio.sleep(e.value)    
            await message.reply_text("<blockquote>Rate limit hit, please try again shortly.</blockquote>")    
        except Exception as e:    
            await message.reply_text("<blockquote>An unexpected error occurred. Please try again.</blockquote>")    
            logger.error(f"Unexpected error in /settings: {e}")    
    else:    
        await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ</blockquote>")    

# ------------------- COMPRESS -------------------
@app.on_message(filters.incoming & filters.command(["compress", f"compress@{BOT_USERNAME}"]))    
async def help_message(app, message):    
    if message.chat.id not in AUTH_USERS:    
        return await message.reply_text("<blockquote>Yᴏᴜ Aʀᴇ Nᴏᴛ Aᴜᴛʜᴏʀɪꜱᴇᴅ Tᴏ Uꜱᴇ Tʜɪꜱ Bᴏᴛ Cᴏɴᴛᴀᴄᴛ @Lord_Vasudev_Krishna</blockquote>")    
    query = await message.reply_text("Aᴅᴅᴇᴅ Tᴏ Qᴜᴇᴜᴇ...\nPʟᴇᴀꜱᴇ ʙᴇ Pᴀᴛɪᴇɴᴛ, Cᴏᴍᴘʀᴇꜱꜱ ᴡɪʟʟ Sᴛᴀʀᴛ Sᴏᴏɴ", quote=True)    
    data.append((message.reply_to_message, None))
    if len(data) == 1:    
        await query.delete()       
        await add_task(message.reply_to_message, None)

# ------------------- RESTART -------------------
@app.on_message(filters.incoming & filters.command(["restart", f"restart@{BOT_USERNAME}"]))    
async def restarter(app, message):    
    if message.from_user.id in AUTH_USERS:    
        await message.reply_text("Rᴇꜱᴛᴀʀᴛɪɴɢ...")    
        quit(1)    
    else:    
        await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ</blockquote>")    

# ------------------- CLEAR -------------------
@app.on_message(filters.incoming & filters.command(["clear", f"clear@{BOT_USERNAME}"]))    
async def restarter(app, message):    
    data.clear()    
    if message.chat.id not in AUTH_USERS:    
        return await message.reply_text("<blockquote>Yᴏᴜ Aʀᴇ Nᴏᴛ Aᴜᴛʜᴏʀɪꜱᴇᴅ Tᴏ Uꜱᴇ Tʜɪꜱ Bᴏᴛ Cᴏɴᴛᴀᴄᴛ @Lord_Vasudev_Krishna</blockquote>")    
    await message.reply_text("<blockquote>Sᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ Cʟᴇᴀʀᴇᴅ Qᴜᴇᴜᴇ...</blockquote>")    

# ------------------- VIDEO / DOCUMENT -------------------
@app.on_message(filters.incoming & (filters.video | filters.document))    
async def help_message(app, message):    
    if message.chat.id not in AUTH_USERS:    
        return await message.reply_text("<blockquote>Yᴏᴜ Aʀᴇ Nᴏᴛ Aᴜᴛʜᴏʀɪꜱᴇᴅ Tᴏ Uꜱᴇ Tʜɪꜱ Bᴏᴛ Cᴏɴᴛᴀᴄᴛ @Lord_Vasudev_Krishna</blockquote>")
    # Instead of starting immediately, show quality options
    await incoming_start_message_f(app, message, quality_check=True)

# ------------------- STATE HANDLER -------------------
@app.on_message(filters.text & ~filters.command(list(filter(lambda x: x.startswith("/"), ["/"]))))
async def state_handler(client, message):
    if message.from_user.id in user_states:
        state = user_states[message.from_user.id]
        setting = state["setting"]
        mode = state["mode"]
        value = message.text.strip()

        try:
            if setting == "crf":
                await db.set_crf(int(value), mode)
            elif setting == "resolution":
                await db.set_resolution(value, mode)
            elif setting == "preset":
                await db.set_preset(value, mode)
            elif setting == "audio_b":
                await db.set_audio_b(value, mode)

            mode_str = mode if mode else "default/480p"
            await message.reply_text(f"Updated {setting} to {value} for {mode_str}")
            del user_states[message.from_user.id]
        except Exception as e:
            await message.reply_text(f"Error updating setting: {e}")

# ------------------- SYSINFO -------------------
@app.on_message(filters.incoming & filters.command(["sysinfo", f"sysinfo@{BOT_USERNAME}"]))    
async def help_message(app, message):    
    if message.from_user.id in AUTH_USERS:    
        await sysinfo(message)    
    else:    
        await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ</blockquote>")    

# ------------------- CANCEL -------------------
@app.on_message(filters.incoming & filters.command(["cancel", f"cancel@{BOT_USERNAME}"]))    
async def help_message(app, message):    
    await incoming_cancel_message_f(app, message)    

# ------------------- EXEC -------------------
@app.on_message(filters.incoming & filters.command(["exec", f"exec@{BOT_USERNAME}"]))    
async def help_message(app, message):    
    await exec_message_f(app, message)    

# ------------------- EVAL -------------------
@app.on_message(filters.incoming & filters.command(["eval", f"eval@{BOT_USERNAME}"]))    
async def help_message(app, message):    
    await eval_message_f(app, message)    

# ------------------- STOP -------------------
@app.on_message(filters.incoming & filters.command(["stop", f"stop@{BOT_USERNAME}"]))    
async def help_message(app, message):    
    await on_task_complete()        

# ------------------- HELP -------------------
@app.on_message(filters.incoming & filters.command(["help", f"help@{BOT_USERNAME}"]))    
async def help_message(app, message):    
    await message.reply_text(
        "Hɪ, ɪ ᴀᴍ <b>Video Encoder bot</b>\n"
        "<blockquote>➥ Sᴇɴᴅ ᴍᴇ Yᴏᴜʀ Tᴇʟᴇɢʀᴀᴍ Fɪʟᴇꜱ\n"
        "➥ I ᴡɪʟʟ Eɴᴄᴏᴅᴇ ᴛʜᴇᴍ Oɴᴇ ʙʏ Oɴᴇ Aꜱ ɪ Hᴀᴠᴇ <b>Queue Feature</b>\n"
        "➥ Jᴜꜱᴛ Sᴇɴᴅ ᴍᴇ ᴛʜᴇ Jᴘɢ/Pɪᴄ ᴀɴᴅ Iᴛ Wɪʟʟ ʙᴇ Sᴇᴛ ᴀꜱ Yᴏᴜʀ Cᴜꜱᴛᴏᴍ Tʜᴜᴍʙɴᴀɪʟ \n"
        "➥ Fᴏʀ FFᴍᴘᴇɢ Lᴏᴠᴇʀꜱ - U ᴄᴀɴ Cʜᴀɴɢᴇ ᴄʀꜰ Bʏ /eval crf.insert(0, 'crf value')</blockquote> \n"
        "<b>Maintained By : @SECRECT_BOT_UPDATES</b>",
        quote=True
    )    

# ------------------- LOG -------------------
@app.on_message(filters.incoming & filters.command(["log", f"log@{BOT_USERNAME}"]))    
async def help_message(app, message):    
    await upload_log_file(app, message)    

# ------------------- PING -------------------
@app.on_message(filters.incoming & filters.command(["ping", f"ping@{BOT_USERNAME}"]))    
async def up(app, message):    
    stt = dt.now()    
    ed = dt.now()    
    v = ts(int((ed - uptime).total_seconds() * 1000))    
    u = f"<blockquote>Bᴏᴛ ᴜᴘᴛɪᴍᴇ = {v} </blockquote>"    
    ms = (ed - stt).microseconds / 1000    
    p = f"Pɪɴɢ = {ms}ms "    
    await message.reply_text(u + "\n" + p)    

# ----------------------------------------------------------------------
# Callback button handler
# ----------------------------------------------------------------------
call_back_button_handler = CallbackQueryHandler(button)    
app.add_handler(call_back_button_handler)    

# ----------------------------------------------------------------------
# ------------------- STARTUP MESSAGE TO SUDO -------------------
# ----------------------------------------------------------------------
SUDO_ID = 7660990923   # keep as int

async def send_startup_message():
    try:
        start_time = dt.now()
        uptime_str = ts(int((start_time - uptime).total_seconds() * 1000))
        await app.send_message(
            chat_id=SUDO_ID,
            text=(
                "<blockquote><b>Bot Restarted Successfully!</b>\n\n"
                f"<b>Uptime:</b> <code>{uptime_str}</code>\n"
                f"<b>Started at:</b> <code>{start_time.strftime('%Y-%m-%d %I:%M:%S %p')}</code>\n"
                f"<b>Platform:</b> <code>{platform.system()} {platform.release()}</code>\n"
                f"<b>@Lord_Vasudev_Krishna</b></blockquote>"
            ),
            disable_web_page_preview=True
        )
        logger.info("Startup message sent to sudo user.")
    except Exception as e:
        logger.error(f"Could not send startup message: {e}")

# ----------------------------------------------------------------------
# ------------------- MAIN ENTRY POINT -------------------------
# ----------------------------------------------------------------------
async def main():
    await app.start()

    # Load authorized users from DB
    try:
        db_auth_users = await db.get_auth_users()
        for user_id in db_auth_users:
            if user_id not in AUTH_USERS:
                AUTH_USERS.append(user_id)
        logger.info(f"Loaded {len(db_auth_users)} authorized users from DB.")
    except Exception as e:
        logger.error(f"Failed to load authorized users from DB: {e}")

    await set_bot_commands(app)
    await send_startup_message()          # <-- sends the restart notice
    me = await app.get_me()
    logger.info(f"Bot started as @{me.username}")
    await pyrogram.idle()                 # keeps the bot alive
    await app.stop()

# ----------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # (download folder already created at the top of the file)
    app.loop.run_until_complete(main())
