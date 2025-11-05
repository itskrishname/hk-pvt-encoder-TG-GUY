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
    # 1. CPU – first call returns 0.0, so we call it once and discard
    psutil.cpu_percent(interval=None)         
    cpu_usage = psutil.cpu_percent(interval=1) 

    # 2. CPU frequency
    freq = psutil.cpu_freq()
    freq_current = (
        f"{round(freq.current / 1000, 2)} GHz"
        if freq else "N/A"
    )

    # 3. Core counts
    cpu_physical = psutil.cpu_count(logical=False) or "E"
    cpu_logical  = psutil.cpu_count(logical=True)  or "E"

    # 4. RAM
    ram = psutil.virtual_memory()

    # 5. Disk – root filesystem
    disk = psutil.disk_usage('/')

    # 6. Network I/O
    net = psutil.net_io_counters()
    ul_size = net.bytes_sent
    dl_size = net.bytes_recv

    text = (
        "<u><b>Sʏꜱᴛᴇᴍ Sᴛᴀᴛꜱ</b></u>\n"
        "<blockquote>"
        f"<b>CPU Freq:</b> {freq_current}\n"
        f"<b>CPU Cores [ Physical:</b> {cpu_physical} | <b>Total:</b> {cpu_logical} ]\n\n"

        f"<b>Total Disk :</b> {human(disk.total)}B\n"
        f"<b>Used:</b> {human(disk.used)}B | <b>Free:</b> {human(disk.free)}B\n\n"

        f"<b>Total Upload:</b> {human(ul_size)}B\n"
        f"<b>Total Download:</b> {human(dl_size)}B\n\n"

        f"<b>Total Ram :</b> {human(ram.total)}B\n"
        f"<b>Used:</b> {human(ram.used)}B | <b>Free:</b> {human(ram.available)}B\n\n"

        f"<b>CPU:</b> {cpu_usage}%\n"
        f"<b>RAM:</b> {int(ram.percent)}%\n"
        f"<b>DISK:</b> {int(disk.percent)}%"
        "</blockquote>"
    )

    await e.reply_text(text, disable_web_page_preview=True)
