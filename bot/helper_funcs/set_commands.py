from pyrogram import Client
from pyrogram.types import BotCommand

async def set_bot_commands(client: Client):
    commands = [
        BotCommand("start", "Check if bot is alive"),
        BotCommand("help", "Get help"),
        BotCommand("ping", "Check ping"),
        BotCommand("settings", "View current settings (Admin)"),
        BotCommand("sysinfo", "View system info (Admin)"),
        BotCommand("speedtest", "Run Speedtest (Admin)"),
        BotCommand("auth", "Authorize user (Admin)"),
        BotCommand("update", "Update the bot (Admin)"),
        BotCommand("restart", "Restart the bot (Admin)"),
        BotCommand("log", "Get log file (Admin)"),
        BotCommand("compress", "Compress media (Admin)"),
        BotCommand("cancel", "Cancel current task (Admin)"),
        BotCommand("clear", "Clear the queue (Admin)"),
        BotCommand("crf", "Set CRF value (Admin)"),
        BotCommand("resolution", "Set resolution (Admin)"),
        BotCommand("preset", "Set preset (Admin)"),
        BotCommand("v_codec", "Set video codec (Admin)"),
        BotCommand("a_codec", "Set audio codec (Admin)"),
        BotCommand("audio_b", "Set audio bitrate (Admin)"),
        BotCommand("v_bitrate", "Set video bitrate (Admin)"),
        BotCommand("bits", "Set pixel format bits (Admin)"),
        BotCommand("watermark", "Set watermark text (Admin)"),
        BotCommand("size", "Set watermark font size (Admin)"),
        BotCommand("settings1", "Settings for 720p (Admin)"),
        BotCommand("settings2", "Settings for 1080p (Admin)"),
        BotCommand("exec", "Execute shell commands (Admin)"),
        BotCommand("eval", "Evaluate Python code (Admin)"),
        BotCommand("stop", "Stop the bot (Admin)"),
    ]
    await client.set_bot_commands(commands)
