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
from bot.helper.database import db

# ---------- Small helpers ----------
def humanbytes(size: float) -> str:
    if size is None:
        return "0B"
    if size == 0:
        return "0B"
    power = 1024
    n = 0
    units = ["B", "KB", "MB", "GB", "TB"]
    while size >= power and n < len(units) - 1:
        size /= power
        n += 1
    return f"{size:.2f}{units[n]}"

def parse_timecode(tc: str) -> float:
    """
    Parse strings like "00:01:23.456" or "N/A"
    Return seconds as float or None.
    """
    if not tc or tc.upper() == "N/A":
        return None
    # Accept formats HH:MM:SS(.ms) or MM:SS(.ms)
    parts = tc.split(':')
    try:
        parts = [float(p) for p in parts]
    except Exception:
        return None
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 1:
        return parts[0]
    return None

# ---------- convert_video (fixed) ----------
async def convert_video(video_file, output_directory, total_time, bot, message, chan_msg, mode=None):
    # Extract file name and extension
    kk = video_file.split("/")[-1]
    aa = kk.split(".")[-1] if "." in kk else ""
    out_put_file_name = kk.replace(f".{aa}", "[@Lord_Vasudev_Krishna].mkv") if aa else kk + "[@Lord_Vasudev_Krishna].mkv"
    out_put_fullpath = os.path.join(output_directory, out_put_file_name)

    # Fetch settings from database using mode
    try:
        crf = await db.get_crf(mode)
        preset = await db.get_preset(mode)
        resolution = await db.get_resolution(mode)
        audio_b = await db.get_audio_b(mode)
        audio_codec = await db.get_audio_codec(mode)
        video_codec = await db.get_video_codec(mode)
        video_bitrate = await db.get_video_bitrate(mode)
        watermark = await db.get_watermark(mode)
        bits = await db.get_bits(mode)
        size = await db.get_size(mode)
    except Exception as e:
        logger.error(f"Failed to fetch settings from database: {e}")
        await message.reply_text("<blockquote expandable>Database error: Could not fetch encoding settings. Please try again later.</blockquote>")
        return None

    # Get total frames and fps using ffprobe (best-effort)
    total_frames = None
    fps = 30.0  # default fallback
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=nb_frames,r_frame_rate',
            '-of', 'default=noprint_wrappers=1',
            video_file
        ]
        out = subprocess.check_output(cmd).decode('utf-8', errors='ignore').strip().splitlines()
        for line in out:
            if line.startswith('nb_frames='):
                try:
                    total_frames = int(line.split('=', 1)[1])
                except Exception:
                    total_frames = None
            elif line.startswith('r_frame_rate='):
                fps_str = line.split('=', 1)[1]
                if '/' in fps_str:
                    try:
                        num, den = map(int, fps_str.split('/'))
                        if den != 0:
                            fps = num / den
                    except Exception:
                        pass
                else:
                    try:
                        fps = float(fps_str)
                    except Exception:
                        pass
        logger.info(f"Total frames: {total_frames}, FPS: {fps}")
    except Exception as e:
        logger.warning(f"ffprobe failed: {e}")
        total_frames = None
        fps = 30.0

    # Estimate total frames if not available and total_time known
    if total_frames is None and total_time:
        try:
            total_frames = int(total_time * fps)
            logger.info(f"Estimated total frames: {total_frames}")
        except Exception:
            total_frames = None

    # Prepare FFmpeg command components (progress on stdout)
    ffmpeg_cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-progress", "pipe:1",  # progress on stdout (structured key=value)
        "-i", video_file
    ]

    if watermark:
        ffmpeg_cmd.extend([
            "-vf", (
                f"drawtext=text='{watermark}':"
                "x='if(gte(t,240),w-(t-240)*60,NAN)':"
                "y=10:"
                f"fontsize={size}:"
                "fontcolor=white:"
                "enable='gte(t,240)':"
                "box=0"
            )
        ])

    ffmpeg_cmd.extend([
        "-c:v", video_codec,
        "-crf", str(crf),
        "-s", resolution,
        "-c:a", audio_codec,
        "-b:a", audio_b,
        "-ac", "2",
        "-mapping_family", "1",        
        "-preset", preset,
        "-x265-params", "wpp=1:pmode=0:pme=0:no-sao=1:aq-mode=1:aq-strength=0.8:psy-rd=1.0:ref=3:bframes=4:keyint=240:min-keyint=24:rc-lookahead=10",
         "-tune", "animation"
    ])

    if video_bitrate:
        ffmpeg_cmd.extend(["-b:v", str(video_bitrate)])

    if bits == "10":
        ffmpeg_cmd.extend(["-pix_fmt", "yuv420p10le"])
    else: 
        ffmpeg_cmd.extend(["-pix_fmt", "yuv420p"])

    ffmpeg_cmd.extend([
        "-map", "0",
        "-c:s", "copy",
        out_put_fullpath,
        "-y"
    ])

    # for logging
    file_genertor_command = " ".join(shlex.quote(x) for x in ffmpeg_cmd)
    logger.info(f"Running FFmpeg: {file_genertor_command}")
    logger.info(f"Input exists: {os.path.exists(video_file)}, Path: {video_file}")
    logger.info(f"Output directory exists: {os.path.exists(output_directory)}, Path: {output_directory}")

    # Start FFmpeg process
    COMPRESSION_START_TIME = time.time()
    process = await asyncio.create_subprocess_shell(
        file_genertor_command,
        stdout=asyncio.subprocess.PIPE,   # structured progress
        stderr=asyncio.subprocess.PIPE,   # encoder logs/warnings
        shell=True
    )

    logger.info(f"ffmpeg_process: {process.pid}")
    pid_list.insert(0, process.pid)

    status = os.path.join(output_directory, "status.json")
    try:
        if os.path.exists(status):
            with open(status, 'r+') as f:
                try:
                    statusMsg = json.load(f)
                except Exception:
                    statusMsg = {}
                statusMsg['pid'] = process.pid
                statusMsg['message'] = getattr(message, "id", None)
                f.seek(0)
                json.dump(statusMsg, f, indent=2)
                f.truncate()
    except Exception as e:
        logger.warning(f"Could not write status.json: {e}")

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
    except Exception:
        pass
    try:
        await chan_msg.edit_text(text=init_stats)
    except Exception:
        pass

    # === PROGRESS READING LOOP (read structured key=value blocks from stdout) ===
    progress_dict = {}
    last_percentage = -1
    last_update_time = 0
    stuck_counter = 0

    async def read_stderr():
        # Keep reading stderr so the buffer doesn't block - we just log it
        try:
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                text = line.decode('utf-8', errors='ignore').strip()
                if text:
                    logger.debug(f"FFmpeg stderr: {text}")
        except Exception as e:
            logger.debug(f"stderr reader ended: {e}")

    # schedule stderr reader so it doesn't block
    asyncio.create_task(read_stderr())

    try:
        while True:
            # read a line from stdout (progress pipe)
            line = await process.stdout.readline()
            if not line:
                # EOF reached
                break

            text = line.decode('utf-8', errors='ignore').strip()
            if not text:
                continue

            logger.debug(f"FFmpeg progress raw: {text}")

            # parse key=value
            if "=" in text:
                k, v = text.split("=", 1)
                progress_dict[k.strip()] = v.strip()

            # When FFmpeg emits a 'progress' key, that's the end of a block
            if "progress" in progress_dict:
                prog_value = progress_dict.get("progress", "")
                # if progress=end => encoding finished
                if prog_value == "end":
                    logger.info("FFmpeg reported progress=end")
                    break

                # now compute stats from the block
                try:
                    frame_str = progress_dict.get("frame", "0")
                    current_frame = int(frame_str) if frame_str.isdigit() else 0
                except Exception:
                    current_frame = 0

                # fps (may be N/A or 0.00 early)
                try:
                    fps_str = progress_dict.get("fps", "")
                    current_fps = float(fps_str) if fps_str and fps_str.upper() != "N/A" else fps
                    if current_fps == 0:
                        current_fps = fps
                except Exception:
                    current_fps = fps

                # speed (format like "1.23x" or "N/A")
                try:
                    sp = progress_dict.get("speed", "1x")
                    if sp and sp.upper() != "N/A":
                        speed = float(sp.replace("x", ""))
                    else:
                        speed = 1.0
                except Exception:
                    speed = 1.0

                # size in bytes (total_size)
                try:
                    cs = progress_dict.get("total_size", "0")
                    current_size = int(cs) if cs.isdigit() else 0
                except Exception:
                    current_size = 0

                # out_time e.g. 00:00:05.040 or N/A
                out_time_str = progress_dict.get("out_time", None)
                out_time_seconds = parse_timecode(out_time_str) if out_time_str else None

                # Percentage calculation:
                percentage = 0
                if total_frames and total_frames > 0:
                    percentage = math.floor((current_frame / total_frames) * 100)
                elif out_time_seconds and total_time:
                    try:
                        percentage = math.floor((out_time_seconds / total_time) * 100)
                    except Exception:
                        percentage = 0
                else:
                    # fallback: estimate by frames if we have any frames seen and assumed fps+total_time
                    if total_time and current_fps and current_frame:
                        est_total_frames = int(total_time * current_fps)
                        if est_total_frames > 0:
                            percentage = math.floor((current_frame / est_total_frames) * 100)
                        else:
                            percentage = 0
                    else:
                        percentage = 0

                percentage = max(0, min(100, int(percentage)))

                # throttle updates to at most once per second
                now = time.time()
                if (now - last_update_time) >= EDIT_INTERVAL:
                    last_update_time = now
                    last_percentage = percentage
                    stuck_counter = 0

                    # remaining seconds using frames if possible
                    remaining_seconds = 0
                    if total_frames and current_fps and current_frame >= 0:
                        remaining_frames = max(0, total_frames - current_frame)
                        remaining_seconds = remaining_frames / max(current_fps * speed, 0.0001)
                    elif out_time_seconds and total_time:
                        remaining_seconds = max(0, total_time - out_time_seconds) / max(speed, 0.0001)
                    else:
                        remaining_seconds = 0

                    ETA = TimeFormatter(int(remaining_seconds * 1000)) if remaining_seconds > 0 else "-"

                    # time taken
                    time_taken = TimeFormatter(int((time.time() - COMPRESSION_START_TIME) * 1000))

                    # estimated size (if percentage > 0)
                    estimated_size = humanbytes(int((current_size / (percentage / 100)) if percentage > 0 and current_size > 0 else current_size))

                    # build progress bar
                    filled = percentage // 10
                    empty = 10 - filled
                    progress_str = "♻️<b>ᴘʀᴏɢʀᴇss:</b> {0}%\n[{1}{2}]".format(
                        percentage,
                        ''.join([FINISHED_PROGRESS_STR for i in range(filled)]),
                        ''.join([UN_FINISHED_PROGRESS_STR for i in range(empty)])
                    )

                    stats = (
                        f'<p>⚡ <b>ᴇɴᴄᴏᴅɪɴɢ ɪɴ ᴘʀᴏɢʀᴇss</b></p>\n\n'
                        f'🕛 <b>ᴛɪᴍᴇ ʟᴇꜰᴛ:</b> {ETA}\n'
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
                        logger.debug(f"Edit message failed: {e}")

                    try:
                        await chan_msg.edit_text(text=stats)
                    except Exception as e:
                        logger.debug(f"Edit channel failed: {e}")

                    logger.debug(f"Progress updated: {percentage}% | Frames: {current_frame}/{total_frames} | Speed: {speed:.2f}x")

                else:
                    stuck_counter += 1
                    if stuck_counter > 60:
                        # log but don't kill; ffmpeg may be doing a long encode step
                        logger.warning(f"No UI update for 60 loops at {percentage}% (ffmpeg alive).")

                # clear the progress_dict for the next block
                progress_dict.clear()

            # end of handling a block
    except Exception as e:
        logger.exception(f"Progress read loop error: {e}")

    # Wait for ffmpeg to finish if not already
    if process.returncode is None:
        try:
            await asyncio.wait_for(process.wait(), timeout=120.0)
            logger.info("FFmpeg finished via wait()")
        except asyncio.TimeoutError:
            logger.error("FFmpeg did not exit in time; terminating")
            try:
                process.terminate()
                await process.wait()
            except Exception:
                pass

    # Collect remaining stdout/stderr
    try:
        stdout, stderr = await process.communicate()
        t_response = stdout.decode('utf-8', errors='ignore').strip() if stdout else ""
        e_response = stderr.decode('utf-8', errors='ignore').strip() if stderr else ""
        logger.info(f"FFmpeg stdout: {t_response}")
        logger.info(f"FFmpeg stderr: {e_response}")
    except Exception as e:
        logger.debug(f"Error reading final output: {e}")

    # remove pid
    try:
        del pid_list[0]
    except Exception:
        pass

    # Check output
    if os.path.exists(out_put_fullpath):
        logger.info(f"Encoding success: {out_put_fullpath}")
        return out_put_fullpath
    else:
        logger.error("No output file created")
        try:
            await message.reply_text("<blockquote expandable>Error: Encoding failed. No output file created.</blockquote>")
        except Exception:
            pass
        return None

# ---------- media_info (unchanged but robustified) ----------
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
  output = stdout.decode(errors='ignore').strip()
  duration = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", output)
  bitrates = re.search(r"bitrate:\s*([\d\.]+)\s*kb/s", output, re.IGNORECASE)

  if duration is not None:
    hours = int(duration.group(1))
    minutes = int(duration.group(2))
    seconds = float(duration.group(3))
    total_seconds = int(( hours * 60 * 60 ) + ( minutes * 60 ) + math.floor(seconds))
  else:
    total_seconds = None
  if bitrates is not None:
    bitrate = bitrates.group(1)
  else:
    bitrate = None
  return total_seconds, bitrate

# ---------- take_screen_shot (unchanged but ensures paths) ----------
async def take_screen_shot(video_file, output_directory, ttl):
    out_put_file_name = os.path.join(
        output_directory,
        str(int(time.time())) + ".jpg"
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
            out_put_file_name,
            "-y"
        ]

        process = await asyncio.create_subprocess_exec(
            *file_genertor_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        e_response = stderr.decode(errors='ignore').strip()
        t_response = stdout.decode(errors='ignore').strip()
        if e_response:
            logger.debug(f"screenshot stderr: {e_response}")

    if os.path.lexists(out_put_file_name):
        return out_put_file_name
    else:
        return None

# ---------- get_width_height (unchanged) ----------
def get_width_height(video_file):
    try:
        metadata = extractMetadata(createParser(video_file))
        if metadata and metadata.has("width") and metadata.has("height"):
            return metadata.get("width"), metadata.get("height")
        else:
            return 1280, 720
    except Exception as e:
        logger.debug(f"get_width_height failed: {e}")
        return 1280, 720
