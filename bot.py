import subprocess
import os
import signal
import threading
import http.server
import socketserver
from telethon import TelegramClient, events, Button

# --- Cấu hình Web Server giả để Render không tắt Bot ---
def start_web_server():
    # Render Web Service bắt buộc phải có Port này
    PORT = int(os.getenv("PORT", 10000))
    Handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"Web Server chạy tại port {PORT}")
            httpd.serve_forever()
    except Exception as e:
        print(f"Web Server Error: {e}")

# Chạy Server trong luồng riêng
threading.Thread(target=start_web_server, daemon=True).start()

# --- THÔNG TIN ĐÃ GẮN TRỰC TIẾP ---
API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8194497853:AAG6fdLREzWaNLq9oHWOCfqYiUm-avveefA"
ADMIN_ID = 7816353760

# Khởi tạo Bot
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
current_process = None

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != ADMIN_ID:
        return
    await event.reply("✅ **Bot đã sẵn sàng!**\nDùng lệnh: `/attack <url>`")

@bot.on(events.NewMessage(pattern=r'/attack (https?://\S+)'))
async def attack_handler(event):
    global current_process
    if event.sender_id != ADMIN_ID:
        return
    
    url = event.pattern_match.group(1)
    if current_process and current_process.poll() is None:
        return await event.reply("⚠️ Đang có bài test đang chạy. Hãy dừng nó trước!")

    await event.reply(f"🚀 **Đang kích hoạt tải cao:** `{url}`", 
                     buttons=[Button.inline("🛑 DỪNG LẠI", b"stop")])

    # Chạy Locust
    current_process = subprocess.Popen([
        "locust", "-f", "load_test.py", "--headless",
        "-u", "300", "-r", "30", "--host", url
    ])

@bot.on(events.CallbackQuery(data=b"stop"))
@bot.on(events.NewMessage(pattern='/stop'))
async def stop_handler(event):
    global current_process
    if current_process:
        os.kill(current_process.pid, signal.SIGTERM)
        current_process = None
        msg = "🛑 **Đã dừng.**"
    else:
        msg = "Không có gì đang chạy."
    
    if isinstance(event, events.CallbackQuery.Event):
        await event.edit(msg)
    else:
        await event.reply(msg)

print("Bot is starting with hardcoded credentials...")
bot.run_until_disconnected()
