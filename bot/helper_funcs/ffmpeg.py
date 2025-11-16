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
    # -------------------------------------------------- 1. Prepare files
    kk = os.path.basename(video_file)
    aa = kk.rsplit(".", 1)[-1]
    out_put_file_name = kk.replace(f".{aa}", "[@Itsme123c].mkv")
    progress_path = os.path.join(output_directory, "progress.txt")
    open(progress_path, "w").close()                     # empty progress file

    # -------------------------------------------------- 2. DB settings
    try:
        crf          = await db.get_crf()
        preset       = await db.get_preset()
        resolution   = await db.get_resolution()
        audio_b      = await db.get_audio_b()
        audio_codec  = await db.get_audio_codec()
        video_codec  = await db.get_video_codec()
        video_bitrate= await db.get_video_bitrate()
        watermark    = await db.get_watermark()
        bits         = await db.get_bits()
    except Exception as e:
        logger.error(f"DB error: {e}")
        await message.reply_text("<blockquote>DB error – cannot fetch settings.</blockquote>")
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
        fps = 30.0 
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
        

    # -------------------------------------------------- 4. Build FFmpeg command
    ffmpeg_cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-progress", progress_path, "-i", video_file
    ]

    # ----- watermark -------------------------------------------------
    if watermark:
        ffmpeg_cmd += ["-i", watermark]
        ffmpeg_cmd += ["-filter_complex",
                       "[1:v]scale=1000:-1[wm];[0:v][wm]overlay=x='if(between(t,5,20),(W-w)*(t-5)/5,"
                       "if(between(t,845,860),(W-w)*(t-12)/6,if(between(t,1245,1260),(W-w)*(t-20)/5,NAN)))':"
                       "y=10,scale=1920:1080,format=yuv420p10le"]


    # ----- video / audio --------------------------------------------
    ffmpeg_cmd += [
        "-c:v", video_codec, "-crf", str(crf), "-s", resolution,
        "-c:a", audio_codec, "-b:a", audio_b, "-preset", preset,
    ]
    if video_bitrate:
        ffmpeg_cmd += ["-b:v", video_bitrate]
    if bits == "10":
        ffmpeg_cmd += ["-pix_fmt", "yuv420p10le"]
    ffmpeg_cmd += [
        "-map", "0", "-c:s", "copy",
        out_put_file_name, "-y"
    ]

    cmd_str = " ".join(shlex.quote(x) for x in ffmpeg_cmd)
    logger.info(f"FFmpeg command: {cmd_str}")

    # -------------------------------------------------- 5. Start FFmpeg
    COMPRESSION_START = time.time()
    proc = await asyncio.create_subprocess_shell(
        cmd_str,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    logger.info(f"FFmpeg PID: {proc.pid}")
    pid_list.insert(0, proc.pid)

    status_json = os.path.join(output_directory, "status.json")
    with open(status_json, "r+") as f:
        data = json.load(f)
        data["pid"] = proc.pid
        data["message"] = message.id
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()

    # -------------------------------------------------- 6. Progress loop
    last_pct = -1
    stuck_cnt = 0
    finalizing = False

    # ---- initial message ----
    init_bar = "♻️<b>ᴘʀᴏɢʀᴇss:</b> 0%\n[{}{}]".format(
        FINISHED_PROGRESS_STR * 0,
        UN_FINISHED_PROGRESS_STR * 10
    )
    init_txt = (
        "<p>Encoding initializing...</p>\n\n"
        "FFmpeg warming up (first 10-30 s normal)...\n\n"
        f"{init_bar}"
    )
    try:
        await message.edit_text(
            init_txt,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton('Cancel', callback_data='fuckingdo')]]
            )
        )
    except: pass
    try: await chan_msg.edit_text(init_txt)
    except: pass

    while proc.returncode is None:
        await asyncio.sleep(3)

        # ---- read progress file ----
        if not os.path.exists(progress_path):
            stuck_cnt += 1
            if stuck_cnt > 10:
                logger.warning("progress.txt missing >30 s")
            continue

        try:
            with open(progress_path, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read()
        except Exception as e:
            logger.warning(f"read progress error: {e}")
            continue

        if not raw:
            continue

        # ---- parse latest line ----
        lines = raw.strip().splitlines()
        latest = lines[-1] if lines else ""

        # regexes
        frame_m   = re.search(r"frame=(\d+)", raw)
        fps_m     = re.search(r"fps=([\d.]+)", raw)
        speed_m   = re.search(r"speed=([\d.]+)x", raw)
        prog_m    = re.search(r"progress=(\w+)", raw)

        cur_frame = int(frame_m.group(1)) if frame_m else 0
        cur_fps   = float(fps_m.group(1)) if fps_m else 30.0
        speed     = float(speed_m.group(1)) if speed_m else 1.0
        is_end    = prog_m and prog_m.group(1) == "end"

        # ---- percentage -------------------------------------------------
        if total_frames and total_frames > 0:
            pct = min(100, math.floor(cur_frame / total_frames * 100))
            use_frames = True
        else:
            # fallback to time (very rare)
            t_ms = re.search(r"out_time_ms=(\d+)", raw)
            elapsed = int(t_ms.group(1)) / 1_000_000 if t_ms else 0.0
            pct = min(100, math.floor(elapsed * 100 / total_time)) if total_time else 0
            use_frames = False

        # ---- finalizing (muxing) ----------------------------------------
        if pct >= 100 and not finalizing:
            finalizing = True
            final_start = time.time()
            fin_txt = (
                "<p>Finalizing encode...</p>\n\n"
                "Muxing audio/video – this can take 5-15 min.\n\n"
                f"♻️<b>ᴘʀᴏɢʀᴇss:</b> 100%\n[{FINISHED_PROGRESS_STR*10}]"
            )
            try: await message.edit_text(fin_txt, reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton('Cancel', callback_data='fuckingdo')]]
            ))
            except: pass
            try: await chan_msg.edit_text(fin_txt)
            except: pass
            continue

        if finalizing:
            elapsed_fin = TimeFormatter((time.time() - final_start) * 1000)
            fin_txt = (
                "<p>Finalizing encode...</p>\n\n"
                f"<b>Time finalizing:</b> {elapsed_fin}\n\n"
                f"♻️<b>ᴘʀᴏɢʀᴇss:</b> 100%\n[{FINISHED_PROGRESS_STR*10}]"
            )
            try: await message.edit_text(fin_txt, reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton('Cancel', callback_data='fuckingdo')]]
            ))
            except: pass
            try: await chan_msg.edit_text(fin_txt)
            except: pass
            continue

        # ---- ETA -------------------------------------------------------
        if use_frames and total_frames:
            remaining_frames = max(0, total_frames - cur_frame)
            remaining_sec    = remaining_frames / cur_fps if cur_fps else 0
            eta_sec          = remaining_sec / speed if speed else 0
        else:
            elapsed = (int(re.search(r"out_time_ms=(\d+)", raw).group(1)) / 1_000_000
                      if re.search(r"out_time_ms=(\d+)", raw) else 0)
            eta_sec = (total_time - elapsed) / speed if speed else 0
        ETA = TimeFormatter(int(eta_sec * 1000)) if eta_sec else "-"

        # ---- estimated final size ---------------------------------------
        cur_size = os.path.getsize(out_put_file_name) if os.path.exists(out_put_file_name) else 0
        est_size = humanbytes(cur_size / (pct / 100)) if pct > 0 and cur_size else "-"

        # ---- time taken -------------------------------------------------
        taken = TimeFormatter((time.time() - COMPRESSION_START) * 1000)

        # ---- build bar --------------------------------------------------
        filled = pct // 10
        bar = f"[{FINISHED_PROGRESS_STR*filled}{UN_FINISHED_PROGRESS_STR*(10-filled)}]"

        # ---- send update only when % changed ---------------------------
        if pct > last_pct or last_pct == -1:
            last_pct = pct
            stuck_cnt = 0

            txt = (
                "<p>Encoding in progress</p>\n\n"
                f"<b>Time left:</b> {ETA}\n"
                f"<b>Time taken:</b> {taken}\n"
                f"<b>Speed:</b> {speed:.2f}x\n"
                f"<b>Est. size:</b> {est_size}\n\n"
                f"♻️<b>ᴘʀᴏɢʀᴇss:</b> {pct}%\n{bar}"
            )
            try:
                await message.edit_text(
                    txt,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton('Cancel', callback_data='fuckingdo')]]
                    )
                )
            except Exception as e:
                logger.warning(f"user edit failed: {e}")
            try:
                await chan_msg.edit_text(txt)
            except Exception as e:
                logger.warning(f"channel edit failed: {e}")

            logger.debug(f"Progress: {pct}% | frame {cur_frame}/{total_frames or '?'} | speed {speed:.2f}x")
        else:
            stuck_cnt += 1
            if stuck_cnt > 20:                     # 1 min no change
                logger.warning(f"No % change for 1 min at {pct}%")

        if is_end:
            logger.info("FFmpeg reported progress=end")
            break

    # -------------------------------------------------- 7. Wait for termination
    if proc.returncode is None:
        try:
            await asyncio.wait_for(proc.wait(), timeout=60)
        except asyncio.TimeoutError:
            logger.error("FFmpeg did not exit – killing")
            proc.terminate()
            await proc.wait()

    # -------------------------------------------------- 8. Cleanup
    stdout, stderr = await proc.communicate()
    logger.info(f"FFmpeg stdout:\n{stdout.decode(errors='ignore')}")
    logger.info(f"FFmpeg stderr:\n{stderr.decode(errors='ignore')}")

    del pid_list[0]


    if os.path.exists(out_put_file_name):
        logger.info("Encoding finished")
        return out_put_file_name

    await message.reply_text("<blockquote>Encoding failed – no output file.</blockquote>")
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
