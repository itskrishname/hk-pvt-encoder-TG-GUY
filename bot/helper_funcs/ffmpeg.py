import logging
logging.basicConfig(
    level=logging.DEBUG, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

import asyncio, aiohttp
import os
import time
import re
import json
import subprocess
import math
import shlex
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.helper_funcs.display_progress import (
  TimeFormatter
)
from bot.localisation import Localisation
from bot import (
    FINISHED_PROGRESS_STR,
    UN_FINISHED_PROGRESS_STR,
    DOWNLOAD_LOCATION,
    EDIT_INTERVAL,
    pid_list
)
from helper.database import db

async def convert_video(video_file, output_directory, total_time, bot, message, chan_msg):
    kk = video_file.split("/")[-1]
    aa = kk.split(".")[-1]
    out_put_file_name = kk.replace(f".{aa}", "[@Animes_Guy].mkv")
    progress = os.path.join(output_directory, "progress.txt")

    # Clear progress file
    with open(progress, 'w') as f:
        pass

    # Fetch settings from database
    try:
        crf = await db.get_crf()
        preset = await db.get_preset()
        resolution = await db.get_resolution()
        audio_b = await db.get_audio_b()
        audio_codec = await db.get_audio_codec()
        video_codec = await db.get_video_codec()
        video_bitrate = await db.get_video_bitrate()
        watermark = await db.get_watermark()
        bits = await db.get_bits()
    except Exception as e:
        logger.error(f"Failed to fetch settings from database: {e}")
        await message.reply_text("<blockquote>Database error: Could not fetch encoding settings. Please try again later.</blockquote>")
        return None

    ffmpeg_cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-progress", progress,
        "-i", video_file
    ]

    if watermark is not None:
        ffmpeg_cmd.extend(["-i", watermark])
        ffmpeg_cmd.extend(["-filter_complex", 
                           "[1:v]scale=1000:-1[wm];[0:v][wm]overlay=x='if(between(t,5,20),(W-w)*(t-5)/5,if(between(t,845,860),(W-w)*(t-12)/6,if(between(t,1245,1260),(W-w)*(t-20)/5,NAN)))':y=10,scale=1920:1080,format=yuv420p10le"])

    ffmpeg_cmd.extend([
        "-c:v", video_codec,
        "-crf", str(crf),
        "-s", resolution,
        "-c:a", audio_codec,
        "-b:a", audio_b,
        "-preset", preset,
        "-x265-params", "bframes=8:psy-rd=1:ref=3:aq-mode=3:aq-strength=0.8:deblock=1,1:rc-lookahead=32"
    ])
            
    if video_bitrate is not None:
        ffmpeg_cmd.extend(["-b:v", video_bitrate])

    if bits == "10":
        ffmpeg_cmd.extend(["-pix_fmt", "yuv420p10le"])
        
    ffmpeg_cmd.extend([
        "-map", "0", 
        "-c:s", "copy", 
        "-ac", "2", 
        "-ab", audio_b, 
        "-vbr", "2", 
        "-level", "3.1"
    ])

    logger.info(f"Input exists: {os.path.exists(video_file)}, Path: {video_file}")
    logger.info(f"Output directory exists: {os.path.exists(output_directory)}, Path: {output_directory}")

    ffmpeg_cmd.extend([out_put_file_name, "-y"])
    file_genertor_command = " ".join(shlex.quote(x) for x in ffmpeg_cmd)

    logger.info(f"Running FFmpeg: {file_genertor_command}")

    COMPRESSION_START_TIME = time.time()
    process = await asyncio.create_subprocess_shell(
        file_genertor_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    logger.info(f"ffmpeg_process: {process.pid}")
    pid_list.insert(0, process.pid)
    status = os.path.join(output_directory, "status.json")
    with open(status, 'r+') as f:
        statusMsg = json.load(f)
        statusMsg['pid'] = process.pid
        statusMsg['message'] = message.id
        f.seek(0)
        json.dump(statusMsg, f, indent=2)

    # === TG: Itsme123c / GitHub: Telegram_Guyz===
    isDone = False
    last_percentage = -1
    stuck_counter = 0

    init_stats = (
        f'<p>⚡ <b>ᴇɴᴄᴏᴅɪɴɢ ɪɴɪᴛɪᴀʟɪᴢɪɴɢ...</b></p>\n\n'
        f'⏳ FFmpeg warming up (first 10-30s normal)...\n\n'
        f'♻️ <b>ᴘʀᴏɢʀᴇss:</b> 0%\n[{'█' * 0 + '░' * 10}]\n'
    )
    try:
        await message.edit_text(
            text=init_stats,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ Cancel ❌', callback_data='fuckingdo')]])
        )
    except:
        pass
    try:
        await chan_msg.edit_text(text=init_stats)
    except:
        pass

    while process.returncode is None:
        await asyncio.sleep(3)
        try:
            if not os.path.exists(progress):
                stuck_counter += 1
                if stuck_counter > 10:  # 30s no file
                    logger.warning("progress.txt missing for 30s, but FFmpeg still running...")
                continue

            with open(progress, 'r', encoding='utf-8', errors='ignore') as file:
                text = file.read().strip()

            if not text:
                continue

            logger.debug(f"FFmpeg progress raw: {text[-200:]}")

            frame = re.findall("frame=(\d+)", text)
            time_in_us = re.findall("out_time_ms=(\d+)", text)
            progress_status = re.findall("progress=(\w+)", text)
            speed_matches = re.findall("speed=(\d+\.?\d*)x", text)

            if time_in_us:
                time_in_us = int(time_in_us[-1])
            else:
                time_in_us = 0
            elapsed_time = time_in_us / 1000000

            if speed_matches:
                speed = float(speed_matches[-1])
            else:
                speed = 1.0

            if progress_status and progress_status[-1] == "end":
                logger.info("FFmpeg progress=end detected")
                isDone = True
                break

            percentage = math.floor(elapsed_time * 100 / total_time) if total_time > 0 else 0
            percentage = min(100, percentage)

            
            if percentage > last_percentage or last_percentage == -1:
                last_percentage = percentage
                stuck_counter = 0

                difference = math.floor((total_time - elapsed_time) / speed) if speed > 0 else 0
                ETA = TimeFormatter(difference * 1000) if difference > 0 else "-"

                time_taken = TimeFormatter((time.time() - COMPRESSION_START_TIME) * 1000)

                progress_str = "♻️<b>ᴘʀᴏɢʀᴇss:</b> {0}%\n[{1}{2}]".format(
                    round(percentage, 2),
                    ''.join([FINISHED_PROGRESS_STR for i in range(math.floor(percentage / 10))]),
                    ''.join([UN_FINISHED_PROGRESS_STR for i in range(10 - math.floor(percentage / 10))])
                )

                stats = (
                    f'<p>⚡ <b>ᴇɴᴄᴏᴅɪɴɢ ɪɴ ᴘʀᴏɢʀᴇss</b></p>\n\n'
                    f'🕛 <b>ᴛɪᴍᴇ ʟᴇғᴛ:</b> {ETA}\n'
                    f'<b>⏱️ ᴛɪᴍᴇ ᴛᴀᴋᴇɴ:</b> {time_taken}\n'
                    f'<b>ꜱᴘᴇᴇᴅ:</b> {speed:.2f}x\n\n'
                    f'{progress_str}\n'
                )

                try:
                    await message.edit_text(
                        text=stats,
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ Cancel ❌', callback_data='fuckingdo')]])
                    )
                except Exception as e:
                    logger.warning(f"Edit message failed: {e}")

                try:
                    await chan_msg.edit_text(text=stats)
                except Exception as e:
                    logger.warning(f"Edit channel failed: {e}")

                logger.debug(f"Progress updated: {percentage}% | Elapsed: {elapsed_time:.1f}s | Speed: {speed:.2f}x")

            stuck_counter += 1
            if stuck_counter > 20:
                logger.warning(f"No progress update for 1min at {percentage}%, but FFmpeg alive...")

        except Exception as e:
            logger.warning(f"Safe progress read error: {e} — continuing...")
            continue

    if not isDone:
        try:
            await asyncio.wait_for(process.wait(), timeout=60.0)  # 1min grace
            logger.info("FFmpeg finished via returncode")
        except asyncio.TimeoutError:
            logger.error("FFmpeg timed out — killing process")
            process.terminate()
            await process.wait()

    stdout, stderr = await process.communicate()
    e_response = stderr.decode('utf-8', errors='ignore').strip()
    t_response = stdout.decode('utf-8', errors='ignore').strip()
    logger.info(f"FFmpeg stdout: {t_response}")
    logger.info(f"FFmpeg stderr: {e_response}")

    del pid_list[0]


    if os.path.exists(out_put_file_name):
        logger.info(f"Encoding success: {out_put_file_name}")
        return out_put_file_name
    else:
        logger.error("No output file created")
        await message.reply_text("<blockquote>Error: Encoding failed. No output file created.</blockquote>")
        return None
        
async def media_info(saved_file_path):
  process = subprocess.Popen(
    [
      'ffmpeg', 
      "-hide_banner", 
      '-i', 
      saved_file_path
    ], 
    stdout=subprocess.PIPE, 
    stderr=subprocess.STDOUT
  )
  stdout, stderr = process.communicate()
  output = stdout.decode().strip()
  duration = re.search("Duration:\s*(\d*):(\d*):(\d+\.?\d*)[\s\w*$]",output)
  bitrates = re.search("bitrate:\s*(\d+)[\s\w*$]",output)
  
  if duration is not None:
    hours = int(duration.group(1))
    minutes = int(duration.group(2))
    seconds = math.floor(float(duration.group(3)))
    total_seconds = ( hours * 60 * 60 ) + ( minutes * 60 ) + seconds
  else:
    total_seconds = None
  if bitrates is not None:
    bitrate = bitrates.group(1)
  else:
    bitrate = None
  return total_seconds, bitrate
  
async def take_screen_shot(video_file, output_directory, ttl):
    out_put_file_name = os.path.join(
        output_directory,
        str(time.time()) + ".jpg"
    )
    if video_file.upper().endswith(("MKV", "MP4", "WEBM")):
        file_genertor_command = [
            "ffmpeg",
            "-ss",
            str(ttl),
            "-i",
            video_file,
            "-vframes",
            "1",
            out_put_file_name
        ]
        
        process = await asyncio.create_subprocess_exec(
            *file_genertor_command,
            # stdout must a pipe to be accessible as process.stdout
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # Wait for the subprocess to finish
        stdout, stderr = await process.communicate()
        e_response = stderr.decode().strip()
        t_response = stdout.decode().strip()
    #
    if os.path.lexists(out_put_file_name):
        return out_put_file_name
    else:
        return None
# senpai I edited this,  maybe if it is wrong correct it 
def get_width_height(video_file):
    metadata = extractMetadata(createParser(video_file))
    if metadata.has("width") and metadata.has("height"):
        return metadata.get("width"), metadata.get("height")
    else:
        return 1280, 720
