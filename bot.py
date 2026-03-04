import subprocess
import os
import signal
import threading
import http.server
import socketserver
from telethon import TelegramClient, events, Button

# --- Cấu hình Web Server để Render không bị lỗi ---
def start_web_server():
    PORT = int(os.getenv("PORT", 10000))
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Web Server chạy tại port {PORT}")
        httpd.serve_forever()

# Chạy Web Server trong một luồng riêng
threading.Thread(target=start_web_server, daemon=True).start()

# --- Giữ nguyên phần Code Bot của bạn bên dưới ---
API_ID = int(os.getenv("36437338", 0))
API_HASH = os.getenv("18d34c7efc396d277f3db62baa078efc", "")
BOT_TOKEN = os.getenv("8194497853:AAG6fdLREzWaNLq9oHWOCfqYiUm-avveefA", "")
ADMIN_ID = int(os.getenv("7816353760", 0))

bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
current_process = None

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != ADMIN_ID: return
    await event.reply("🔥 **Bot Stress Test (Web Service Mode) đã Online!**")

@bot.on(events.NewMessage(pattern=r'/attack (https?://\S+)'))
async def attack_handler(event):
    global current_process
    if event.sender_id != ADMIN_ID: return
    
    url = event.pattern_match.group(1)
    if current_process and current_process.poll() is None:
        return await event.reply("⚠️ Đang có bài test chạy!")

    await event.reply(f"🚀 Đang tấn công: `{url}`", buttons=[Button.inline("🛑 STOP", b"stop")])

    current_process = subprocess.Popen([
        "locust", "-f", "load_test.py", "--headless",
        "-u", "300", "-r", "30", "--host", url
    ])

@bot.on(events.CallbackQuery(data=b"stop"))
async def stop_callback(event):
    global current_process
    if current_process:
        os.kill(current_process.pid, signal.SIGTERM)
        current_process = None
        await event.edit("🛑 Đã dừng.")

print("Bot đang chạy...")
bot.run_until_disconnected()
