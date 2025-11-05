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
    pid_list
)
from helper.database import db


async def convert_video(video_file, output_directory, total_time, bot, message, chan_msg):
    # Extract file name and extension
    kk = video_file.split("/")[-1]
    aa = kk.split(".")[-1]
    out_put_file_name = kk.replace("[@Itsme123c]", f".{aa}")
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

    # Prepare FFmpeg command components
    ffmpeg_cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-progress", progress,
        "-i", video_file
    ]

    
    if watermark is not None:
        ffmpeg_cmd.extend(["-i", watermark])
        ffmpeg_cmd.extend(["-filter_complex", "[1:v]scale=1000:-1[wm];[0:v][wm]overlay=x='if(between(t,5,20),(W-w)*(t-5)/5,if(between(t,845,860),(W-w)*(t-12)/6,if(between(t,1245,1260),(W-w)*(t-20)/5,NAN)))':y=10,scale=1920:1080,format=yuv420p10le"])

    ffmpeg_cmd.extend([
        "-c:v", video_codec,
        "-crf", str(crf),
        "-s", resolution,
        "-c:a", audio_codec,
        "-b:a", audio_b,
        "-preset", preset,
        "-x265-params", "bframes=8:psy-rd=1:ref=3:aq-mode=3:aq-strength=0.8:deblock=1,1:rc-lookahead=32"
    ])
            
    # Add video bitrate if not None
    if video_bitrate is not None:
        ffmpeg_cmd.extend(["-b:v", video_bitrate])

    # Add bit depth if 10-bit
    if bits == "10":
        ffmpeg_cmd.extend(["-pix_fmt", "yuv420p10le"])
        
    ffmpeg_cmd.extend([
        "-map", "0", 
        "-c:s", "copy", 
        "-ac", "2", 
        "-ab", audio_b, 
        "-vbr", "2", 
        "-level", "3.1", 
        "-threads", "1"
    ])
    logger.info(f"Input exists: {os.path.exists(video_file)}, Path: {video_file}")
    logger.info(f"Output directory exists: {os.path.exists(output_directory)}, Path: {output_directory}")

    # Complete FFmpeg command
    ffmpeg_cmd.extend([out_put_file_name, "-y"])
    file_genertor_command = " ".join(shlex.quote(x) for x in ffmpeg_cmd)

    logger.info(f"Running FFmpeg: {file_genertor_command}")

    # Start FFmpeg process
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

    # === HEROKU-PROOF PROGRESS LOOP ===
    isDone = False
    last_percentage = -1
    stuck_counter = 0
    speed = 1.0

    while process.returncode is None:
        await asyncio.sleep(3)
        try:
            if not os.path.exists(progress):
                stuck_counter += 1
                if stuck_counter > 10:
                    logger.warning("progress.txt missing for 30s, continuing...")
                continue

            with open(progress, 'r', encoding='utf-8', errors='ignore') as file:
                text = file.read().strip()

            if not text:
                continue

            # Parse FFmpeg progress
            frame_match = re.search(r"frame=(\d+)", text)
            time_match = re.search(r"out_time_ms=(\d+)", text)
            progress_match = re.search(r"progress=(\w+)", text)
            speed_match = re.search(r"speed=([\d.]+)x", text)

            if time_match:
                elapsed_us = int(time_match.group(1))
                elapsed_time = elapsed_us / 1_000_000
            else:
                elapsed_time = 0

            if speed_match:
                speed = float(speed_match.group(1))
            else:
                speed = 1.0

            if progress_match and progress_match.group(1) == "end":
                logger.info("FFmpeg reported 'progress=end'")
                isDone = True
                break

            # Calculate percentage (cap at 99%)
            percentage = min(99, math.floor(elapsed_time * 100 / total_time)) if total_time > 0 else 0

            if percentage > last_percentage:
                last_percentage = percentage
                stuck_counter = 0

                # ETA
                remaining = (total_time - elapsed_time) / speed if speed > 0 else 0
                ETA = TimeFormatter(remaining * 1000) if remaining > 0 else "-"

                # Progress bar
                filled = percentage // 10
                empty = 10 - filled
                progress_bar = f"[{''.join([FINISHED_PROGRESS_STR] * filled)}{''.join([UN_FINISHED_PROGRESS_STR] * empty)}]"

                stats = (
                    f'<p>⚡ <b>ᴇɴᴄᴏᴅɪɴɢ ɪɴ ᴘʀᴏɢʀᴇss</b></p>\n\n'
                    f'🕛 <b>ᴛɪᴍᴇ ʟᴇғᴛ:</b> {ETA}\n'
                    f'<b>ꜱᴘᴇᴇᴅ:</b> {speed:.2f}x\n\n'
                    f'♻️ <b>ᴘʀᴏɢʀᴇss:</b> {percentage}%\n{progress_bar}\n'
                )

                try:
                    await message.edit_text(
                        text=stats,
                        reply_markup=InlineKeyboardMarkup(
                            [[InlineKeyboardButton('❌ Cancel ❌', callback_data='fuckingdo')]]
                        )
                    )
                except:
                    pass
                try:
                    await chan_msg.edit_text(text=stats)
                except:
                    pass

                logger.debug(f"Progress: {percentage}% | Speed: {speed:.2f}x | ETA: {ETA}")

        except Exception as e:
            logger.warning(f"Progress loop safe error: {e}")
            continue

    # === END LOOP ===

    stdout, stderr = await process.communicate()
    e_response = stderr.decode().strip()
    t_response = stdout.decode().strip()
    logger.info(f"FFmpeg stdout: {t_response}")
    logger.info(f"FFmpeg stderr: {e_response}")

    del pid_list[0]

    # Clean up watermark file
    if watermark_file and os.path.exists(watermark_file):
        try:
            os.remove(watermark_file)
        except Exception as e:
            logger.error(f"Failed to delete watermark file: {e}")

    if os.path.exists(out_put_file_name):
        return out_put_file_name
    else:
        logger.error("FFmpeg output file not created")
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
