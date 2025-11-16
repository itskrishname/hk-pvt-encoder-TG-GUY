import logging

logging.getLogger("pymongo").setLevel(logging.INFO)
logging.getLogger("motor").setLevel(logging.INFO)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

from datetime import datetime as dt
import os, asyncio, pyrogram, psutil, platform
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
    app
)
from bot.helper_funcs.utils import add_task, on_task_complete, sysinfo
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message
from psutil import disk_usage, cpu_percent, virtual_memory, Process as psprocess

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
from helper.database import db
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pymongo.errors import PyMongoError

SUDO_USER = 7465574522

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
        + ((str(milliseconds) + "ms, ") if milliseconds else "")
    )
    return tmp[:-2]


if __name__ == "__main__" :
    # create download directory, if not exist
    if not os.path.isdir(DOWNLOAD_LOCATION):
        os.makedirs(DOWNLOAD_LOCATION)
        
    # STATUS ADMIN Command

    # START command
    incoming_start_message_handler = MessageHandler(
        incoming_start_message_f,
        filters=filters.command(["start", f"start@{BOT_USERNAME}"])
    )
    app.add_handler(incoming_start_message_handler)

    @app.on_message(filters.incoming & filters.command(["crf", f"crf@{BOT_USERNAME}"]))
    async def changecrf(app, message):
        if message.from_user.id in AUTH_USERS:
            try:
                cr = message.text.split(" ", maxsplit=1)[1]
                cr_int = int(cr)  # Validate as integer
                await db.set_crf(cr_int)
                OUT = f"<blockquote>I will be using : {cr} crf</blockquote>"
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
            await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ 🔒</blockquote>")

    @app.on_message(filters.incoming & filters.command(["resolution", f"resolution@{BOT_USERNAME}"]))
    async def changer(app, message):
        if message.from_user.id in AUTH_USERS:
            try:
                res = message.text.split(" ", maxsplit=1)[1]
                await db.set_resolution(res)
                OUT = f"<blockquote>I will be using : {res} </blockquote>"
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
            await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ 🔒</blockquote>")

    @app.on_message(filters.incoming & filters.command(["preset", f"preset@{BOT_USERNAME}"]))
    async def changepr(app, message):
        if message.from_user.id in AUTH_USERS:
            try:
                preset_val = message.text.split(" ", maxsplit=1)[1]
                await db.set_preset(preset_val)
                OUT = f"<blockquote>I will be using : {preset_val} preset</blockquote>"
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
            await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ 🔒</blockquote>")

    @app.on_message(filters.incoming & filters.command(["v_codec", f"v_codec@{BOT_USERNAME}"]))
    async def changevcodec(app, message):
        if message.from_user.id in AUTH_USERS:
            try:
                codec_val = message.text.split(" ", maxsplit=1)[1]
                await db.set_video_codec(codec_val)
                OUT = f"<blockquote>I will be using : {codec_val} video codec</blockquote>"
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
            await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ 🔒</blockquote>")

    @app.on_message(filters.incoming & filters.command(["a_codec", f"a_codec@{BOT_USERNAME}"]))
    async def changeacodec(app, message):
        if message.from_user.id in AUTH_USERS:
            try:
                codec_val = message.text.split(" ", maxsplit=1)[1]
                await db.set_audio_codec(codec_val)
                OUT = f"<blockquote>I will be using : {codec_val} audio codec</blockquote>"
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
            await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ 🔒</blockquote>")

    @app.on_message(filters.incoming & filters.command(["audio_b", f"audio_b@{BOT_USERNAME}"]))
    async def changeab(app, message):
        if message.from_user.id in AUTH_USERS:
            try:
                aud = message.text.split(" ", maxsplit=1)[1]
                await db.set_audio_b(aud)
                OUT = f"<blockquote>I will be using : {aud} audio bitrate</blockquote>"
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
            await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ 🔒</blockquote>")

    @app.on_message(filters.incoming & filters.command(["v_bitrate", f"v_bitrate@{BOT_USERNAME}"]))
    async def changevbitrate(app, message):
        if message.from_user.id in AUTH_USERS:
            try:
                br = message.text.split(" ", maxsplit=1)[1]
                br_int = int(br)  # Validate as integer (0 for None)
                await db.set_video_bitrate(br_int)
                display = "no video bitrate (auto)" if br_int == 0 else f"{br_int}"
                OUT = f"<blockquote>I will be using : {display} video bitrate</blockquote>"
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
            await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ 🔒</blockquote>")

    @app.on_message(filters.incoming & filters.command(["bits", f"bits@{BOT_USERNAME}"]))
    async def changebits(app, message):
        if message.from_user.id in AUTH_USERS:
            try:
                bits_val = message.text.split(" ", maxsplit=1)[1]
                if bits_val not in ["8", "10"]:
                    await message.reply_text("<blockquote>Bits must be either 8 or 10, e.g., /bits 10</blockquote>")
                    return
                await db.set_bits(bits_val)
                OUT = f"<blockquote>I will be using : {bits_val}-bit video encoding</blockquote>"
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
            await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ 🔒</blockquote>") 

    
    @app.on_message(filters.incoming & filters.command(["watermark", f"watermark@{BOT_USERNAME}"]))
    async def changewatermark(app, message):
        if message.from_user.id in AUTH_USERS:
            try:
                wm = message.text.split(" ", maxsplit=1)[1]
                if wm.strip().lower() in ["0", "none", ""]:
                    await db.set_watermark(0)
                    OUT = f"<blockquote>I will be using : no watermark</blockquote>"
                else:
                    await db.set_watermark(wm)
                    OUT = f"<blockquote>I will be using : {wm} watermark</blockquote>"
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
            await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ 🔒</blockquote>")

    @app.on_message(filters.incoming & filters.command(["settings", f"settings@{BOT_USERNAME}"]))
    async def settings(app, message):
        if message.from_user.id in AUTH_USERS:
            try:
                crf_val = await db.get_crf()
                preset_val = await db.get_preset()
                resolution_val = await db.get_resolution()
                audio_b_val = await db.get_audio_b()
                audio_codec_val = await db.get_audio_codec()
                video_codec_val = await db.get_video_codec()
                video_bitrate_val = await db.get_video_bitrate()
                watermark_val = await db.get_watermark()
                bits_val = await db.get_bits()

                video_bitrate_display = "Auto/None" if video_bitrate_val is None else f"{video_bitrate_val}"
                watermark_display = "None" if watermark_val is None else f"{watermark_val}"

                reply_text = (
                    f"<b>Tʜᴇ Cᴜʀʀᴇɴᴛ Sᴇᴛᴛɪɴɢꜱ ᴡɪʟʟ ʙᴇ Aᴅᴅᴇᴅ Yᴏᴜʀ Vɪᴅᴇᴏ Fɪʟᴇ ⚙️:</b>\n"
                    f"<blockquote><b>➥ Video Codec</b> : <code>{video_codec_val}</code> \n"
                    f"<b>➥ Audio Codec</b> : <code>{audio_codec_val}</code> \n"
                    f"<b>➥ Crf</b> : <code>{crf_val}</code> \n"
                    f"<b>➥ Resolution</b> : <code>{resolution_val}</code> \n"
                    f"<b>➥ Preset</b> : <code>{preset_val}</code> \n"
                    f"<b>➥ Audio Bitrate</b> : <code>{audio_b_val}</code> \n"
                    f"<b>➥ Video Bitrate</b> : <code>{video_bitrate_display}</code> \n"
                    f"<b>➥ Bits</b> : <code>{bits_val} bits</code> \n"
                    f"<b>➥ Watermark</b> : <code>{watermark_display}</code></blockquote>\n"
                    f"<b>🥇 Tʜᴇ Aʙɪʟɪᴛʏ ᴛᴏ Cʜᴀɴɢᴇ Sᴇᴛᴛɪɴɢꜱ ɪꜱ Oɴʟʏ ꜰᴏʀ Aᴅᴍɪɴ</b>"
                )
                await message.reply_text(reply_text)
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
            await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ 🔒</blockquote>")

    
        
    @app.on_message(filters.incoming & filters.command(["compress", f"compress@{BOT_USERNAME}"]))
    async def help_message(app, message):
        if message.chat.id not in AUTH_USERS:
            return await message.reply_text("<blockquote>Yᴏᴜ Aʀᴇ Nᴏᴛ Aᴜᴛʜᴏʀɪꜱᴇᴅ Tᴏ Uꜱᴇ Tʜɪꜱ Bᴏᴛ Cᴏɴᴛᴀᴄᴛ @Lord_Vasudev_Krishna</blockquote>")
        query = await message.reply_text("Aᴅᴅᴇᴅ Tᴏ Qᴜᴇᴜᴇ ⏰...\nPʟᴇᴀꜱᴇ ʙᴇ Pᴀᴛɪᴇɴᴛ, Cᴏᴍᴘʀᴇꜱꜱ ᴡɪʟʟ Sᴛᴀʀᴛ Sᴏᴏɴ", quote=True)
        data.append(message.reply_to_message)
        if len(data) == 1:
         await query.delete()   
         await add_task(message.reply_to_message)     
 
    @app.on_message(filters.incoming & filters.command(["restart", f"restart@{BOT_USERNAME}"]))
    async def restarter(app, message):
        if message.from_user.id in AUTH_USERS:
            await message.reply_text("Rᴇꜱᴛᴀʀᴛɪɴɢ...♻️")
            quit(1)
        else:
            await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ 🔒</blockquote>")
            
    @app.on_message(filters.incoming & filters.command(["clear", f"clear@{BOT_USERNAME}"]))
    async def restarter(app, message):
        data.clear()
        if message.chat.id not in AUTH_USERS:
            return await message.reply_text("<blockquote>Yᴏᴜ Aʀᴇ Nᴏᴛ Aᴜᴛʜᴏʀɪꜱᴇᴅ Tᴏ Uꜱᴇ Tʜɪꜱ Bᴏᴛ Cᴏɴᴛᴀᴄᴛ @Lord_Vasudev_Krishna</blockquote>")
        query = await message.reply_text("<blockquote>Sᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ Cʟᴇᴀʀᴇᴅ Qᴜᴇᴜᴇ...📚</blockquote>")
      
        
    @app.on_message(filters.incoming & (filters.video | filters.document))
    async def help_message(app, message):
        if message.chat.id not in AUTH_USERS:
            return await message.reply_text("<blockquote>Yᴏᴜ Aʀᴇ Nᴏᴛ Aᴜᴛʜᴏʀɪꜱᴇᴅ Tᴏ Uꜱᴇ Tʜɪꜱ Bᴏᴛ Cᴏɴᴛᴀᴄᴛ @Lord_Vasudev_Krishna</blockquote>")
        query = await message.reply_text("Aᴅᴅᴇᴅ Tᴏ Qᴜᴇᴜᴇ ⏰...\nPʟᴇᴀꜱᴇ ʙᴇ Pᴀᴛɪᴇɴᴛ, Cᴏᴍᴘʀᴇꜱꜱ ᴡɪʟʟ Sᴛᴀʀᴛ Sᴏᴏɴ", quote=True)
        data.append(message)
        if len(data) == 1:
         await query.delete()   
         await add_task(message)
            
    @app.on_message(filters.incoming & filters.command(["sysinfo", f"sysinfo@{BOT_USERNAME}"]))
    async def help_message(app, message):
        if message.from_user.id in AUTH_USERS:
            await sysinfo(message)
        else:
            await message.reply_text("<blockquote>Aᴅᴍɪɴ Oɴʟʏ 🔒</blockquote>")
        
    @app.on_message(filters.incoming & filters.command(["cancel", f"cancel@{BOT_USERNAME}"]))
    async def help_message(app, message):
        await incoming_cancel_message_f(app, message)
        
    @app.on_message(filters.incoming & filters.command(["exec", f"exec@{BOT_USERNAME}"]))
    async def help_message(app, message):
        await exec_message_f(app, message)
        
    @app.on_message(filters.incoming & filters.command(["eval", f"eval@{BOT_USERNAME}"]))
    async def help_message(app, message):
        await eval_message_f(app, message)
        
    @app.on_message(filters.incoming & filters.command(["stop", f"stop@{BOT_USERNAME}"]))
    async def help_message(app, message):
        await on_task_complete()    
   
    @app.on_message(filters.incoming & filters.command(["help", f"help@{BOT_USERNAME}"]))
    async def help_message(app, message):
        await message.reply_text("Hɪ, ɪ ᴀᴍ <b>Video Encoder bot</b>\n<blockquote>➥ Sᴇɴᴅ ᴍᴇ Yᴏᴜʀ Tᴇʟᴇɢʀᴀᴍ Fɪʟᴇꜱ\n➥ I ᴡɪʟʟ Eɴᴄᴏᴅᴇ ᴛʜᴇᴍ Oɴᴇ ʙʏ Oɴᴇ Aꜱ ɪ Hᴀᴠᴇ <b>Queue Feature</b>\n➥ Jᴜꜱᴛ Sᴇɴᴅ ᴍᴇ ᴛʜᴇ Jᴘɢ/Pɪᴄ ᴀɴᴅ Iᴛ Wɪʟʟ ʙᴇ Sᴇᴛ ᴀꜱ Yᴏᴜʀ Cᴜꜱᴛᴏᴍ Tʜᴜᴍʙɴᴀɪʟ \n➥ Fᴏʀ FFᴍᴘᴇɢ Lᴏᴠᴇʀꜱ - U ᴄᴀɴ Cʜᴀɴɢᴇ ᴄʀꜰ Bʏ /eval crf.insert(0, 'crf value')</blockquote> \n<b>Maintained By : @SECRECT_BOT_UPDATES", quote=True)
        
    @app.on_message(filters.incoming & filters.command(["log", f"log@{BOT_USERNAME}"]))
    async def help_message(app, message):
        await upload_log_file(app, message)
    @app.on_message(filters.incoming & filters.command(["ping", f"ping@{BOT_USERNAME}"]))
    async def up(app, message):
      stt = dt.now()
      ed = dt.now()
      v = ts(int((ed - uptime).seconds) * 1000)
      u = f"<blockquote>Bᴏᴛ ᴜᴘᴛɪᴍᴇ = {v} 🚀"
      ms = (ed - stt).microseconds / 1000
      p = f"Pɪɴɢ = {ms}ms 🌋</blockquote>"
      await message.reply_text(u + "\n" + p)

    call_back_button_handler = CallbackQueryHandler(
        button
    )
    app.add_handler(call_back_button_handler)


    async def start_bot():
        await app.start()
        await app.send_message(int(sudo_users), "<blockquote>♻️ Bot restarted and is now online!</blockquote>")
        await idle()  # keep bot alive

    import asyncio
    from pyrogram import idle

    asyncio.run(start_bot())
