import speedtest
from pyrogram import filters
from bot import app, AUTH_USERS, BOT_USERNAME
from bot.helper_funcs.display_progress import humanbytes

@app.on_message(filters.command(["speedtest", f"speedtest@{BOT_USERNAME}"]) & filters.user(AUTH_USERS))
async def run_speedtest(client, message):
    msg = await message.reply_text("<blockquote>Running Speedtest... Please wait.</blockquote>")

    try:
        st = speedtest.Speedtest()
        await msg.edit("<blockquote>Finding best server...</blockquote>")
        st.get_best_server()

        await msg.edit("<blockquote>Testing Download...</blockquote>")
        download = st.download()

        await msg.edit("<blockquote>Testing Upload...</blockquote>")
        upload = st.upload()

        ping = st.results.ping

        text = f"""
<blockquote><b>🚀 Speedtest Results</b>

<b>Download:</b> {humanbytes(download / 8)}/s
<b>Upload:</b> {humanbytes(upload / 8)}/s
<b>Ping:</b> {ping} ms
<b>ISP:</b> {st.results.client['isp']}</blockquote>
"""
        await msg.edit(text)

    except Exception as e:
        await msg.edit(f"<blockquote>Speedtest Failed: {str(e)}</blockquote>")
