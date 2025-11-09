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
    # Extract file name and extension
    kk = video_file.split("/")[-1]
    aa = kk.split(".")[-1]
    out_put_file_name = kk.replace(f".{aa}", "[@Itsme123c].mkv")

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
        "ffmpeg", "-hide_banner", "-loglevel", "info", "-progress", "pipe:2",
        "-i", video_file
    ]

    if watermark:
        ffmpeg_cmd.extend(["-i", watermark_file])
        ffmpeg_cmd.extend([
            "-filter_complex",
            "[1:v]scale=1000:-1[wm];[0:v][wm]overlay=x='if(between(t,5,20),(W-w)*(t-5)/5,if(between(t,845,860),(W-w)*(t-12)/6,if(between(t,1245,1260),(W-w)*(t-20)/5,NAN)))':y=10,scale=1920:1080,format=yuv420p10le"
        ])
    
    ffmpeg_cmd.extend([
        "-c:v", video_codec,
        "-crf", str(crf),
        "-s", resolution,
        "-c:a", audio_codec,
        "-b:a", audio_b,
        "-preset", preset,
        "-x265-params", "bframes=8:psy-rd=1:ref=3:aq-mode=3:aq-strength=0.8:deblock=1,1:rc-lookahead=32"
    ])

    if video_bitrate:
        ffmpeg_cmd.extend(["-b:v", video_bitrate])

    if bits == "10":
        ffmpeg_cmd.extend(["-pix_fmt", "yuv420p10le"])

    ffmpeg_cmd.extend([
        "-map", "0",
        "-c:s", "copy",
        "-ac", "2",
        os.path.join(output_directory, out_put_file_name),
        "-y"
    ])

    command = " ".join(shlex.quote(x) for x in ffmpeg_cmd)
    logger.info(f"Running FFmpeg: {command}")

    
    start_time = time.time()
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    last_percentage = -1
    last_update_time = 0
    stuck_counter = 0
    speed = 1.0
    elapsed_time = 0
    is_done = False

    logger.info(f"ffmpeg_process PID: {process.pid}")

    # === Progress Loop ===
    while True:
        line = await process.stderr.readline()
        if not line:
            break
        text = line.decode(errors='ignore').strip()
        if not text:
            continue

        
        time_match = re.search(r"out_time_ms=(\d+)", text)
        speed_match = re.search(r"speed=([\d.]+)x", text)
        progress_match = re.search(r"progress=(\w+)", text)

        if time_match:
            elapsed_us = int(time_match.group(1))
            elapsed_time = elapsed_us / 1_000_000
        if speed_match:
            speed = float(speed_match.group(1))
        if progress_match and progress_match.group(1) == "end":
            is_done = True
            break

        percentage = min(99, math.floor(elapsed_time * 100 / total_time)) if total_time > 0 else 0

        # Calculate elapsed & ETA
        elapsed_real = int(time.time() - start_time)
        elapsed_str = time.strftime("%M:%S", time.gmtime(elapsed_real))
        if percentage > 0:
            estimated_total_time = elapsed_real / (percentage / 100)
            eta = max(0, estimated_total_time - elapsed_real)
            eta_str = time.strftime("%M:%S", time.gmtime(eta))
        else:
            eta_str = "--:--"

        # Update progress message every 5 seconds
        if percentage != last_percentage and (time.time() - last_update_time > EDIT_INTERVAL):
            last_percentage = percentage
            last_update_time = time.time()

            filled = percentage // 10
            bar = f"[{FINISHED_PROGRESS_STR * filled}{UN_FINISHED_PROGRESS_STR * (10 - filled)}]"

            status_text = (
                f"<b>⚡ Encoding In Progress</b>\n\n"
                f"🎞️ <b>Progress:</b> {percentage}%\n{bar}\n"
                f"⏱️ <b>Elapsed:</b> {elapsed_str}\n"
                f"⌛ <b>ETA:</b> {eta_str}\n"
                f"🚀 <b>Speed:</b> {speed:.2f}x"
            )

            try:
                await message.edit_text(
                    text=status_text,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton('❌ Cancel', callback_data='cancel_encoding')]]
                    )
                )
            except Exception:
                pass

            try:
                await chan_msg.edit_text(text=status_text)
            except Exception:
                pass

        stuck_counter += 1
        if stuck_counter > 20:
            logger.warning(f"Progress stuck at {percentage}% for >60s.")
            stuck_counter = 0

    await process.wait()

    output_path = os.path.join(output_directory, out_put_file_name)
    if os.path.exists(output_path):
        logger.info(f"✅ Encoding successful: {output_path}")
        total_elapsed = int(time.time() - start_time)
        await message.reply_text(f"<b>✅ Encoding completed!</b>\n🕒 Time Taken: {TimeFormatter(total_elapsed * 1000)}")
        return output_path
    else:
        logger.error("FFmpeg output not created.")
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
