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

    # Get total frames and fps using ffprobe
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=nb_frames,r_frame_rate',
            '-of', 'default=noprint_wrappers=1',
            video_file
        ]
        out = subprocess.check_output(cmd).decode('utf-8').strip().splitlines()
        total_frames = None
        fps = 30.0  # Default
        for line in out:
            if line.startswith('nb_frames='):
                total_frames = int(line.split('=')[1])
            elif line.startswith('r_frame_rate='):
                fps_str = line.split('=')[1]
                if '/' in fps_str:
                    num, den = map(int, fps_str.split('/'))
                    fps = num / den
                else:
                    fps = float(fps_str)
        logger.info(f"Total frames: {total_frames}, FPS: {fps}")
    except Exception as e:
        logger.warning(f"ffprobe failed: {e}")
        total_frames = None
        fps = 30.0

    # Estimate total frames if not available
    if total_frames is None and total_time:
        total_frames = int(total_time * fps)
        logger.info(f"Estimated total frames: {total_frames}")

    # Prepare FFmpeg command components
    ffmpeg_cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-progress", "pipe:2",  # Use stderr for progress
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
        "-preset", preset
    ])
            
    if video_bitrate is not None:
        ffmpeg_cmd.extend(["-b:v", video_bitrate])

    if bits == "10":
        ffmpeg_cmd.extend(["-pix_fmt", "yuv420p10le"])
        
    ffmpeg_cmd.extend([
        "-map", "0", 
        "-c:s", "copy"
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

    # === FRAME-BASED LOOP ===
    isDone = False
    last_percentage = -1
    stuck_counter = 0

    # Initial "Initializing" message to show activity
    init_progress_str = "♻️<b>ᴘʀᴏɢʀᴇss:</b> 0%\n[{0}{1}]".format(
        ''.join([FINISHED_PROGRESS_STR for i in range(math.floor(0 / 10))]),
        ''.join([UN_FINISHED_PROGRESS_STR for i in range(10 - math.floor(0 / 10))])
    )
    init_stats = (
        f'<p>⚡ <b>ᴇɴᴄᴏᴅɪɴɢ ɪɴɪᴛɪᴀʟɪᴢɪɴɢ...</b></p>\n\n'
        f'⏳ FFmpeg warming up (first 10-30s normal)...\n\n'
        f'{init_progress_str}\n'
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

    # Buffer to collect progress lines
    progress_buffer = ""

    while process.returncode is None:
        await asyncio.sleep(3)
        try:
            # Read new lines from stderr (progress pipe)
            while True:
                line = await asyncio.wait_for(process.stderr.readline(), timeout=1.0)
                if line:
                    text = line.decode('utf-8', errors='ignore').strip()
                    if text:
                        logger.debug(f"FFmpeg progress raw: {text}")
                        progress_buffer += text + "\n"  # Accumulate lines like file read
                else:
                    break
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.warning(f"Safe progress read error: {e} — continuing...")
            continue

        if not progress_buffer:
            continue

        # Parse accumulated buffer (like your original file read)
        frame = re.findall("frame=(\d+)", progress_buffer)
        fps_matches = re.findall("fps=(\d+\.?\d*)", progress_buffer)
        speed_matches = re.findall("speed=(\d+\.?\d*)x", progress_buffer)
        progress_status = re.findall("progress=(\w+)", progress_buffer)
        size_matches = re.findall("total_size=(\d+)", progress_buffer)

        current_frame = int(frame[-1]) if frame else 0
        current_fps = float(fps_matches[-1]) if fps_matches else 30.0
        speed = float(speed_matches[-1]) if speed_matches else 1.0
        current_size = int(size_matches[-1]) if size_matches else 0

        if progress_status and progress_status[-1] == "end":
            logger.info("FFmpeg progress=end detected")
            isDone = True
            break

        # Percentage calculation (frame-based)
        percentage = math.floor((current_frame / total_frames) * 100) if total_frames > 0 else 0
        percentage = min(100, percentage)

        # Update only if changed (your original logic + initial force)
        if percentage != last_percentage:
            last_percentage = percentage
            stuck_counter = 0

            # ETA
            remaining_frames = max(0, total_frames - current_frame)
            remaining = remaining_frames / current_fps if current_fps > 0 else 0
            difference = math.floor(remaining / speed) if speed > 0 else 0
            ETA = TimeFormatter(difference * 1000) if difference > 0 else "-"

            # Time taken (elapsed encoding time)
            time_taken = TimeFormatter((time.time() - COMPRESSION_START_TIME) * 1000)

            # Estimated size (based on current size and percentage)
            estimated_size = humanbytes((current_size / (percentage / 100)) if percentage > 0 else 0)

            # Your original progress string
            progress_str = "♻️<b>ᴘʀᴏɢʀᴇss:</b> {0}%\n[{1}{2}]".format(
                round(percentage, 2),
                ''.join([FINISHED_PROGRESS_STR for i in range(math.floor(percentage / 10))]),
                ''.join([UN_FINISHED_PROGRESS_STR for i in range(10 - math.floor(percentage / 10))])
            )

            stats = (
                f'<p>⚡ <b>ᴇɴᴄᴏᴅɪɴɢ ɪɴ ᴘʀᴏɢʀᴇss</b></p>\n\n'
                f'🕛 <b>ᴛɪᴍᴇ ʟᴇғᴛ:</b> {ETA}\n'
                f'<b>⏱️ ᴛɪᴍᴇ ᴛᴀᴋᴇɴ:</b> {time_taken}\n'
                f'<b>ꜱᴘᴇᴇᴅ:</b> {speed:.2f}x\n'
                f'<b>ᴇꜱᴛɪᴍᴀᴛᴇᴅ ꜱɪᴢᴇ:</b> {estimated_size}\n\n'
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

            logger.debug(f"Progress updated: {percentage}% | Frames: {current_frame}/{total_frames} | Speed: {speed:.2f}x")

            # Clear buffer after update to avoid memory growth
            progress_buffer = text  # Keep last block for next parse

        stuck_counter += 1
        if stuck_counter > 20:  # 1min stuck warning
            logger.warning(f"No progress update for 1min at {percentage}%, but FFmpeg alive...")

    # Wait for FFmpeg to finish if not detected
    if not isDone:
        try:
            await asyncio.wait_for(process.wait(), timeout=60.0)  # 1min grace
            logger.info("FFmpeg finished via returncode")
        except asyncio.TimeoutError:
            logger.error("FFmpeg timed out — killing process")
            process.terminate()
            await process.wait()

    # Get final output
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
