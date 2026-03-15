import asyncio, re, os, random, logging
from datetime import datetime, timedelta, timezone
from threading import Thread
from flask import Flask, request, jsonify
from telethon import TelegramClient, events, Button as TButton
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from supabase import create_client, Client

# ===== CẤU HÌNH HỆ THỐNG =====
SUPABASE_URL = "https://npjjarsmvmqvhdnkvtxc.supabase.co" 
SUPABASE_KEY = "sb_publishable_gVXyT92FL0XpsiiEcerYFQ_RXE3n0ke"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8475867709:AAGPINZGRgMnZBRDpNZWPGgBof0fY8N-0D4"
STK_MSB = "96886693002613"
BOT_GAME_TARGET = "xocdia88_bot_uytin_bot"

# Cấu hình giá
PRICE_BOT_1DAY = 10000  # Giá gia hạn bot 1 ngày
PRICE_ADD_CLONE = 2000  # Phí thêm 1 acc clone (nếu bạn muốn free thì để 0)

# 👑 QUYỀN ADMIN
ADMIN_ID = 7816353760 

logging.basicConfig(level=logging.INFO)
bot = TelegramClient(StringSession(), API_ID, API_HASH)

# --- HELPER FUNCTIONS ---
def db_get_user(uid):
    res = supabase.table("users").select("*").eq("user_id", uid).execute()
    if not res.data:
        # Nếu chưa có, tạo mới với bot_expiry là thời điểm hiện tại (hết hạn ngay)
        now_iso = datetime.now(timezone.utc).isoformat()
        supabase.table("users").insert({"user_id": uid, "balance": 0, "bot_expiry": now_iso}).execute()
        return {"user_id": uid, "balance": 0, "bot_expiry": now_iso}
    return res.data[0]

# --- LOGIC ĐẬP HỘP (KIỂM TRA HẠN BOT CỦA CHỦ) ---
async def worker_grab_loop(client, phone, owner_id):
    try:
        if not client.is_connected():
            await client.connect()
        if not await client.is_user_authorized():
            return

        @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
        @client.on(events.MessageEdited(chats=BOT_GAME_TARGET))
        async def handler(ev):
            # Lấy thông tin chủ bot để check hạn dùng bot
            owner = db_get_user(owner_id)
            expiry_date = datetime.fromisoformat(owner['bot_expiry'].replace('Z', '+00:00'))
            
            # Nếu hết hạn dùng Bot, clone sẽ không làm gì cả (nhưng vẫn treo để chờ gia hạn)
            if datetime.now(timezone.utc) > expiry_date:
                return 

            if ev.reply_markup:
                for row in ev.reply_markup.rows:
                    for btn in row.buttons:
                        if btn.text and "đập" in btn.text.lower():
                            await asyncio.sleep(random.uniform(0.1, 0.5))
                            try:
                                click_result = await ev.click(text=btn.text)
                                # Bắt code trúng
                                if click_result and getattr(click_result, 'message', None):
                                    if "là:" in click_result.message:
                                        code = re.search(r'là:\s*([A-Z0-9]+)', click_result.message).group(1)
                                        await bot.send_message(owner_id, f"🎊 **ACC `{phone}` ĐẬP TRÚNG!**\n🔑 Code: `{code}`")
                            except: pass
        
        await client.run_until_disconnected()
    except Exception as e:
        logging.error(f"Worker Error {phone}: {e}")

# ==========================================================
#                   GIAO DIỆN NGƯỜI DÙNG
# ==========================================================
def main_menu_text(user):
    expiry_dt = datetime.fromisoformat(user['bot_expiry'].replace('Z', '+00:00'))
    time_left = expiry_dt - datetime.now(timezone.utc)
    
    status = "🔴 Hết hạn" if time_left.total_seconds() <= 0 else f"🟢 Còn {time_left.days} ngày {time_left.seconds//3600} giờ"
    
    return (
        f"👑 **QUẢN LÝ BOT ĐẬP HỘP** 👑\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 ID: `{user['user_id']}`\n"
        f"💰 Số dư: **{user['balance']:,} VNĐ**\n"
        f"⏳ Hạn Bot: **{status}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📢 *Lưu ý: Gia hạn Bot để các Acc Clone hoạt động.*"
    )

def main_btns():
    return [
        [TButton.inline("🚀 GIA HẠN BOT (SỬ DỤNG)", b"renew_bot")],
        [TButton.inline("➕ THÊM ACC CLONE", b"add_clone"), TButton.inline("📱 DS ACC", b"list_clones")],
        [TButton.inline("🏦 NẠP TIỀN", b"dep_menu"), TButton.inline("👤 VÍ", b"me")],
        [TButton.url("💬 HỖ TRỢ", "https://t.me/nth_dev")]
    ]

@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    user = db_get_user(e.sender_id)
    await e.respond(main_menu_text(user), buttons=main_btns())

@bot.on(events.CallbackQuery)
async def cb_handler(e):
    uid, data = e.sender_id, e.data.decode()
    
    if data == "back":
        user = db_get_user(uid)
        await e.edit(main_menu_text(user), buttons=main_btns())

    elif data == "renew_bot":
        btns = [
            [TButton.inline(f"💎 1 Ngày ({PRICE_BOT_1DAY:,}đ)", b"buy_1d")],
            [TButton.inline(f"💎 7 Ngày ({PRICE_BOT_1DAY*7:,}đ)", b"buy_7d")],
            [TButton.inline("🔙 QUAY LẠI", b"back")]
        ]
        await e.edit("Chọn gói gia hạn Bot của bạn:", buttons=btns)

    elif data.startswith("buy_"):
        days = 1 if "1d" in data else 7
        total_cost = PRICE_BOT_1DAY * days
        user = db_get_user(uid)
        
        if user['balance'] < total_cost:
            return await e.answer(f"❌ Bạn cần {total_cost:,}đ để gia hạn!", alert=True)
        
        # Tính toán thời gian mới
        current_expiry = datetime.fromisoformat(user['bot_expiry'].replace('Z', '+00:00'))
        base_time = max(current_expiry, datetime.now(timezone.utc))
        new_expiry = base_time + timedelta(days=days)
        
        supabase.table("users").update({
            "balance": user['balance'] - total_cost,
            "bot_expiry": new_expiry.isoformat()
        }).eq("user_id", uid).execute()
        
        await e.answer(f"✅ Đã gia hạn thành công {days} ngày!", alert=True)
        user_upd = db_get_user(uid)
        await e.edit(main_menu_text(user_upd), buttons=main_btns())

    # --- Các phần cũ giữ nguyên (Nạp tiền, List Clone, Xóa...) ---
    elif data == "dep_menu":
        btns = [[TButton.inline("💸 10.000đ", b"p_10000"), TButton.inline("💸 50.000đ", b"p_50000")], [TButton.inline("🔙 QUAY LẠI", b"back")]]
        await e.edit("🏦 **CHỌN MỨC NẠP TIỀN**", buttons=btns)
    elif data.startswith("p_"):
        amt = data.split("_")[1]
        txt = f"📥 **NẠP TIỀN**\n💰 Số tiền: **{int(amt):,}đ**\n📝 Nội dung: `NAP {uid}`\nSTK: `{STK_MSB}` (MSB)"
        await e.edit(txt, buttons=[[TButton.inline("🔙 QUAY LẠI", b"dep_menu")]])
    elif data == "me":
        user = db_get_user(uid)
        await e.edit(f"👤 **VÍ CỦA TÔI**\n💰 Số dư: {user['balance']:,}đ", buttons=[[TButton.inline("🔙 QUAY LẠI", b"back")]])
    elif data == "list_clones":
        res = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        if not res.data: return await e.answer("❌ Chưa có acc nào!", alert=True)
        btns = [[TButton.inline(f"🗑 Xóa {c['phone']}", f"del_{c['id']}")] for c in res.data]
        btns.append([TButton.inline("🔙 QUAY LẠI", b"back")])
        await e.edit("📱 **DANH SÁCH ACC CLONE**", buttons=btns)
    elif data.startswith("del_"):
        supabase.table("my_clones").delete().eq("id", data.split("_")[1]).execute()
        await e.answer("✅ Đã gỡ acc!", alert=True)
        await e.edit("Đã cập nhật.", buttons=[[TButton.inline("🔙 QUAY LẠI", b"back")]])

@bot.on(events.CallbackQuery(data=b"add_clone"))
async def add_clone_process(e):
    user = db_get_user(e.sender_id)
    if user['balance'] < PRICE_ADD_CLONE:
        return await e.answer(f"❌ Cần {PRICE_ADD_CLONE:,}đ để thêm acc!", alert=True)

    async with bot.conversation(e.sender_id) as conv:
        try:
            await conv.send_message("📞 Nhập số điện thoại (+84...):")
            phone = (await conv.get_response()).text.strip().replace(" ", "")
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            await client.send_code_request(phone)
            await conv.send_message("📩 Nhập mã OTP:")
            otp = (await conv.get_response()).text.strip()
            try:
                await client.sign_in(phone, otp)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 Nhập 2FA:")
                await client.sign_in(password=(await conv.get_response()).text.strip())

            # Lưu vào DB (Không còn expiry riêng cho clone nữa)
            supabase.table("users").update({"balance": user['balance'] - PRICE_ADD_CLONE}).eq("user_id", e.sender_id).execute()
            supabase.table("my_clones").insert({"owner_id": e.sender_id, "phone": phone, "session": client.session.save()}).execute()
            await conv.send_message(f"✅ Đã thêm acc {phone} thành công!")
            asyncio.create_task(worker_grab_loop(client, phone, e.sender_id))
        except Exception as ex:
            await conv.send_message(f"❌ Lỗi: {str(ex)}")

# --- PHẦN KHỞI CHẠY (Render) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Alive", 200

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    try:
        clones = supabase.table("my_clones").select("*").execute()
        for c in clones.data:
            cl = TelegramClient(StringSession(c['session']), API_ID, API_HASH)
            asyncio.create_task(worker_grab_loop(cl, c['phone'], c['owner_id']))
    except: pass
    await bot.run_until_disconnected()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    asyncio.run(main())
        
