import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
LOGGER = logging.getLogger(__name__)

import os, asyncio, pyrogram, psutil, platform, time
from bot import data
from bot.plugins.incoming_message_fn import incoming_compress_message_f
from pyrogram.types import Message
import psutil
import subprocess
from urllib.request import urlopen

def checkKey(dict, key):
  if key in dict.keys():
    return True
  else:
    return False

def hbs(size):
    if not size:
        return ""
    power = 2 ** 10
    raised_to_pow = 0
    dict_power_n = {0: "B", 1: "K", 2: "M", 3: "G", 4: "T", 5: "P"}
    while size > power:
        size /= power
        raised_to_pow += 1
    return str(round(size, 2)) + " " + dict_power_n[raised_to_pow] + "B"

async def on_task_complete():
    del data[0]
    if len(data) > 0:
      await add_task(data[0])

async def add_task(message: Message):
    try:
        os.system('rm -rf /app/downloads/*')
        await incoming_compress_message_f(message)
    except Exception as e:
        LOGGER.info(e)  
    await on_task_complete()

def human(n: int) -> str:
    return psutil._common.bytes2human(n)


async def sysinfo(e):
    # Warm up CPU percent
    psutil.cpu_percent(interval=None)
    cpu_usage = psutil.cpu_percent(interval=1)

    # CPU frequency & cores
    freq = psutil.cpu_freq()
    freq_current = f"{round(freq.current / 1000, 2)} GHz" if freq else "N/A"
    cpu_physical = psutil.cpu_count(logical=False) or "N/A"
    cpu_logical  = psutil.cpu_count(logical=True)  or "N/A"

    # RAM (psutil)
    ram = psutil.virtual_memory()

    # Disk
    disk = psutil.disk_usage('/')

    # Network
    net = psutil.net_io_counters()
    ul_size = net.bytes_sent
    dl_size = net.bytes_recv

    # === NEW: Real CPU flags from /proc/cpuinfo ===
    try:
        cpu_flags_raw = subprocess.check_output(
            "cat /proc/cpuinfo | grep -i '^flags' | head -n1 | cut -d: -f2", 
            shell=True, text=True
        ).strip()
        cpu_flags = cpu_flags_raw[:120] + ("..." if len(cpu_flags_raw) > 120 else "")
    except:
        cpu_flags = "Unable to read /proc/cpuinfo"

    # === NEW: Container/Docker RAM limit from cgroup ===
    try:
        cgroup_limit_raw = subprocess.check_output(
            "cat /sys/fs/cgroup/memory/memory.limit_in_bytes 2>/dev/null || echo 'No limit'",
            shell=True, text=True
        ).strip()
        cgroup_limit = int(cgroup_limit_raw)
        if cgroup_limit > 10**12:  # Insanely high = no real limit (host RAM)
            cgroup_ram = "Unlimited (Host RAM)"
        else:
            cgroup_ram = f"{human(cgroup_limit)}B (Container Limit)"
    except:
        cgroup_ram = "Not in cgroup / inaccessible"

    # Python version
    python_version = platform.python_version()

    # FFmpeg version
    try:
        ffmpeg_out = subprocess.check_output(['ffmpeg', '-version'], stderr=subprocess.STDOUT)
        ffmpeg_version = ffmpeg_out.decode().split('\n')[0].strip()
    except:
        ffmpeg_version = "FFmpeg not found"

    # Key encoders
    try:
        encoders = subprocess.check_output(['ffmpeg', '-encoders'], stderr=subprocess.DEVNULL).decode()
        libx264 = "Yes" if "libx264" in encoders else "No"
        libx265 = "Yes" if "libx265" in encoders else "No"
        libsvtav1 = "Yes" if "libsvtav1" in encoders else "No"
        encoders_info = f"x264: {libx264} | x265: {libx265} | SVT-AV1: {libsvtav1}"
    except:
        encoders_info = "Failed to check"

    # Hardware acceleration
    try:
        hwaccels = subprocess.check_output(['ffmpeg', '-hwaccels'], stderr=subprocess.DEVNULL).decode().lower()
        hwaccel_info = f"NVENC: {'Yes' if 'nvenc' in hwaccels else 'No'} | VAAPI: {'Yes' if 'vaapi' in hwaccels else 'No'} | VideoToolbox: {'Yes' if 'videotoolbox' in hwaccels else 'No'}"
    except:
        hwaccel_info = "Failed to check"

    # Download speed test (10MB)
    try:
        url = 'http://speedtest.tele2.net/10MB.zip'
        start = time.perf_counter()
        with urlopen(url, timeout=10) as r:
            r.read()
        duration = time.perf_counter() - start
        speed_mbps = round((10 * 8) / duration, 2)
        download_speed = f"{speed_mbps} Mbps"
    except:
        download_speed = "Test failed"

    text = (
        "<u><b>🔧 Sʏꜱᴛᴇᴍ & Sᴇʀᴠᴇʀ Iɴғᴏ</b></u>\n"
        "<blockquote expandable>"
        f"<b>CPU Usage:</b> <i>{cpu_usage}%</i> | <b>RAM Usage:</b> <i>{ram.percent}%</i> | <b>Disk:</b> <i>{disk.percent}%</i>\n\n"

        f"<b>CPU Model Flags:</b>\n<code>{cpu_flags}</code>\n\n"
        f"<b>CPU Freq:</b> <i>{freq_current}</i>\n"
        f"<b>Cores:</b> Physical: <i>{cpu_physical}</i> | Logical: <i>{cpu_logical}</i>\n\n"

        f"<b>RAM (psutil):</b> {human(ram.total)}B total → {human(ram.available)}B free\n"
        f"<b>Container RAM Limit:</b> <i>{cgroup_ram}</i>\n\n"

        f"<b>Disk (/):</b> {human(disk.total)}B → {human(disk.free)}B free\n"
        f"<b>Network /\:</b> {human(dl_size)}B | {human(ul_size)}B\n\n"

        f"<b>Python:</b> <i>{python_version}</i>\n"
        f"<b>FFmpeg:</b> <i>{ffmpeg_version}</i>\n"
        f"<b>Encoders:</b> <i>{encoders_info}</i>\n"
        f"<b>HW Accel:</b> <i>{hwaccel_info}</i>\n"
        f"<b>Internet Speed (10MB):</b> <i>{download_speed}</i>"
        "</blockquote>"
    )

    await e.reply_text(text, disable_web_page_preview=True)
