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
    """Asynchronously convert video with live progress updates to Telegram."""
    # Extract file name
    kk = os.path.basename(video_file)
    ext = kk.split(".")[-1]
    out_put_file_name = os.path.join(output_directory, kk.replace(f".{ext}", "[@Itsme123c].mkv"))

    # === Fetch settings from DB ===
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
        logger.error(f"DB fetch error: {e}")
        await message.reply_text("<blockquote>Database error: Could not fetch encoding settings.</blockquote>")
        return None

    # === Prepare FFmpeg base command ===
    ffmpeg_cmd = [
        "ffmpeg", "-hide_banner",
        "-loglevel", "info",           # Keep stderr clean
        "-progress", "pipe:1",          # Send progress to stdout (important!)
        "-i", video_file
    ]

    if watermark:
        ffmpeg_cmd.extend(["-i", watermark_file])
        ffmpeg_cmd.extend([
            "-filter_complex",
            "[1:v]scale=1000:-1[wm];"
            "[0:v][wm]overlay=x='if(between(t,5,20),(W-w)*(t-5)/5,"
            "if(between(t,845,860),(W-w)*(t-12)/6,"
            "if(between(t,1245,1260),(W-w)*(t-20)/5,NAN)))':y=10,"
            "scale=1920:1080,format=yuv420p10le"
        ])
                    

    # === Video/audio settings ===
    ffmpeg_cmd.extend([
        "-c:v", video_codec,
        "-crf", str(crf),
        "-preset", preset,
        "-s", resolution,
        "-c:a", audio_codec,
        "-b:a", audio_b,
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
        "-level", "3.1",
        "-threads", "1",
        "-y",
        out_put_file_name
    ])

    # === Start subprocess ===
    logger.info(f"Running FFmpeg: {' '.join(shlex.quote(x) for x in ffmpeg_cmd)}")

    process = await asyncio.create_subprocess_exec(
        *ffmpeg_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    pid_list.insert(0, process.pid)
    COMPRESSION_START_TIME = time.time()
    logger.info(f"FFmpeg PID: {process.pid}")

    # === Progress monitoring ===
    isDone = False
    last_percentage = -1
    stuck_counter = 0
    elapsed_time = 0
    speed = 1.0
    last_edit_time = 0
    

    while True:
        if process.returncode is not None:
            break

        try:
            line = await asyncio.wait_for(process.stdout.readline(), timeout=3.0)
            if not line:
                continue

            text = line.decode('utf-8', errors='ignore').strip()
            if not text:
                continue

            if not ("out_time_ms" in text or "speed=" in text or "progress=" in text):
                continue  # skip unrelated lines

            time_match = re.search(r"out_time_ms=(\d+)", text)
            speed_match = re.search(r"speed=([\d.]+)x", text)
            progress_match = re.search(r"progress=(\w+)", text)

            if time_match:
                elapsed_us = int(time_match.group(1))
                elapsed_time = elapsed_us / 1_000_000
            if speed_match:
                try:
                    speed = float(speed_match.group(1))
                except:
                    pass
            if progress_match and progress_match.group(1) == "end":
                isDone = True
                logger.info("FFmpeg finished normally.")
                break

            percentage = min(99, math.floor(elapsed_time * 100 / total_time)) if total_time > 0 else 0

            # Throttle Telegram updates to every 5 seconds
            now = time.time()
            if (now - last_edit_time >= EDIT_INTERVAL) and (percentage > last_percentage or last_percentage == -1):
                last_percentage = percentage
                last_edit_time = now
                stuck_counter = 0

                remaining = max(0, (total_time - elapsed_time) / max(speed, 0.1))
                ETA = TimeFormatter(remaining * 1000) if remaining > 0 else "-"

                filled_blocks = percentage // 10
                empty_blocks = 10 - filled_blocks
                progress_bar = f"[{FINISHED_PROGRESS_STR * filled_blocks}{UN_FINISHED_PROGRESS_STR * empty_blocks}]"

                status_text = (
                    f"<b>⚡ Encoding in Progress...</b>\n\n"
                    f"🕒 <b>Time Left:</b> {ETA}\n"
                    f"⚙️ <b>Speed:</b> {speed:.2f}x\n"
                    f"📊 <b>Progress:</b> {percentage}%\n{progress_bar}"
                )

                try:
                    await message.edit_text(
                        text=status_text,
                        reply_markup=InlineKeyboardMarkup(
                            [[InlineKeyboardButton("❌ Cancel", callback_data="fuckingdo")]]
                        )
                    )
                except Exception as e:
                    logger.warning(f"User msg edit fail: {e}")

                try:
                    await chan_msg.edit_text(text=status_text)
                except Exception as e:
                    logger.warning(f"Channel msg edit fail: {e}")

            stuck_counter += 1
            if stuck_counter > 10:
                logger.warning(f"Progress stuck at {percentage}% for 30s...")

        except asyncio.TimeoutError:
            continue
        except Exception as e:
            logger.warning(f"Progress loop error: {e}")
            continue

    # === Wait for completion ===
    if not isDone:
        try:
            await asyncio.wait_for(process.wait(), timeout=20.0)
        except asyncio.TimeoutError:
            logger.error("FFmpeg timed out, terminating.")
            process.terminate()

    stdout, stderr = await process.communicate()
    logger.info(f"FFmpeg stdout: {stdout.decode(errors='ignore')[:300]}")
    logger.info(f"FFmpeg stderr: {stderr.decode(errors='ignore')[:300]}")

    if pid_list:
        pid_list.pop(0)


    # === Final output check ===
    if os.path.exists(out_put_file_name):
        logger.info(f"Encoding successful → {out_put_file_name}")
        return out_put_file_name
    else:
        await message.reply_text("<blockquote>Error: Encoding failed, no output file created.</blockquote>")
        logger.error("FFmpeg output file missing.")
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
