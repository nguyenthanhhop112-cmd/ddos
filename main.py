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
PRICE_PER_DAY = 10000

# 👑 QUYỀN ADMIN
ADMIN_ID = 7816353760 

logging.basicConfig(level=logging.INFO)
bot = TelegramClient(StringSession(), API_ID, API_HASH)

# --- HELPER FUNCTIONS ---
def db_get_user(uid):
    res = supabase.table("users").select("*").eq("user_id", uid).execute()
    if not res.data:
        supabase.table("users").insert({"user_id": uid, "balance": 0}).execute()
        return {"user_id": uid, "balance": 0}
    return res.data[0]

# --- NÂNG CẤP: LOGIC ĐẬP HỘP (CLONE WORKER) ---
async def worker_grab_loop(client, phone, owner_id, expiry_str):
    try:
        if not client.is_connected():
            await client.connect()
        if not await client.is_user_authorized():
            logging.error(f"Session {phone} không hợp lệ.")
            return

        # Nâng cấp: Đổi thời gian ra đây để không gọi Database liên tục gây lag
        expiry_date = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))

        # Nâng cấp: Lắng nghe cả tin nhắn mới và tin nhắn bị Edit (tránh sót hộp)
        @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
        @client.on(events.MessageEdited(chats=BOT_GAME_TARGET))
        async def handler(ev):
            # Kiểm tra hạn dùng từ RAM
            if datetime.now(timezone.utc) > expiry_date:
                logging.info(f"Clone {phone} hết hạn. Đang xóa...")
                await bot.send_message(owner_id, f"⚠️ **THÔNG BÁO:** Clone `{phone}` đã hết hạn thuê. Đã tự động ngắt kết nối!")
                await client.disconnect()
                supabase.table("my_clones").delete().eq("phone", phone).execute() # Tự gỡ khỏi DB
                return

            if ev.reply_markup:
                # Nâng cấp: Quét kỹ các nút hơn
                for row in ev.reply_markup.rows:
                    for btn in row.buttons:
                        if btn.text and "đập" in btn.text.lower():
                            await asyncio.sleep(random.uniform(0.1, 0.4)) # Delay chống block
                            try:
                                # Nhấn nút chính xác
                                click_result = await ev.click(text=btn.text)
                                await asyncio.sleep(1.0)
                                
                                # Cách 1: Bắt mã code qua thông báo Popup ẩn
                                if click_result and getattr(click_result, 'message', None):
                                    msg_popup = click_result.message
                                    if "là:" in msg_popup:
                                        code = re.search(r'là:\s*([A-Z0-9]+)', msg_popup).group(1)
                                        await bot.send_message(owner_id, f"🎊 **CLONE `{phone}` TRÚNG TỪ POPUP!**\n🔑 Code: `{code}`")
                                        return
                                
                                # Cách 2: (Backup của bạn) Bắt mã code qua tin nhắn chat mới
                                msgs = await client.get_messages(BOT_GAME_TARGET, limit=2)
                                for m in msgs:
                                    if m.message and "là:" in m.message:
                                        m_match = re.search(r'là:\s*([A-Z0-9]+)', m.message)
                                        if m_match:
                                            code = m_match.group(1)
                                            await bot.send_message(owner_id, f"🎊 **CLONE `{phone}` TRÚNG!**\n🔑 Code: `{code}`")
                                            return
                            except Exception as e:
                                logging.error(f"Lỗi click clone {phone}: {e}")
        
        await client.run_until_disconnected()
    except Exception as e:
        logging.error(f"Worker Error {phone}: {e}")

# ==========================================================
#                   GIAO DIỆN NGƯỜI DÙNG
# ==========================================================
def main_menu_text(user):
    return (
        f"👑 **HỆ THỐNG CLONE VIP** 👑\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 ID: `{user['user_id']}`\n"
        f"💰 Số dư: **{user['balance']:,} VNĐ**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚡ *Trạng thái: Server siêu mượt*"
    )

def main_btns():
    return [
        [TButton.inline("➕ THÊM ACC MỚI", b"add_clone")],
        [TButton.inline("📱 DANH SÁCH CLONE", b"list_clones")],
        [TButton.inline("🏦 NẠP TIỀN", b"dep_menu"), TButton.inline("👤 VÍ CỦA TÔI", b"me")],
        [TButton.url("💬 HỖ TRỢ", "https://t.me/nth_dev")]
    ]

@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    user = db_get_user(e.sender_id)
    await e.respond(main_menu_text(user), buttons=main_btns())

@bot.on(events.CallbackQuery)
async def cb_handler(e):
    uid, data = e.sender_id, e.data.decode()
    if data.startswith("admin_"): return
    
    if data == "back":
        user = db_get_user(uid)
        await e.edit(main_menu_text(user), buttons=main_btns())
    
    elif data == "dep_menu":
        btns = [
            [TButton.inline("💸 10.000đ", b"p_10000"), TButton.inline("💸 20.000đ", b"p_20000")],
            [TButton.inline("💸 50.000đ", b"p_50000"), TButton.inline("💸 100.000đ", b"p_100000")],
            [TButton.inline("🔙 QUAY LẠI", b"back")]
        ]
        await e.edit("🏦 **CHỌN MỨC NẠP TIỀN**", buttons=btns)

    elif data.startswith("p_"):
        amt = data.split("_")[1]
        qr = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount={amt}&addInfo=NAP%20{uid}"
        txt = (f"📥 **THÔNG TIN CHUYỂN KHOẢN**\n\n"
               f"💰 Số tiền: **{int(amt):,} VNĐ**\n"
               f"📝 Nội dung: `NAP {uid}`")
        await e.edit(txt, buttons=[[TButton.url("📲 MỞ APP BANK", qr)], [TButton.inline("🔙 QUAY LẠI", b"dep_menu")]])

    elif data == "me":
        user = db_get_user(uid)
        await e.edit(f"👤 **HỒ SƠ**\n🆔 ID: `{uid}`\n💰 Ví: **{user['balance']:,}đ**", buttons=[[TButton.inline("🔙 QUAY LẠI", b"back")]])

    elif data == "list_clones":
        res = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        if not res.data: return await e.answer("❌ Bạn không có clone nào!", alert=True)
        txt = "📱 **CLONE CỦA BẠN**\n\n"
        btns = []
        for c in res.data:
            btns.append([TButton.inline(f"🗑 Xóa {c['phone']}", f"del_{c['id']}")])
        btns.append([TButton.inline("🔙 QUAY LẠI", b"back")])
        await e.edit(txt, buttons=btns)

    elif data.startswith("del_"):
        cid = data.split("_")[1]
        supabase.table("my_clones").delete().eq("id", cid).execute()
        await e.answer("✅ Đã gỡ clone!", alert=True)
        await e.edit("Đã cập nhật danh sách.", buttons=[[TButton.inline("🔙 QUAY LẠI", b"back")]])

@bot.on(events.CallbackQuery(data=b"add_clone"))
async def add_clone_process(e):
    user = db_get_user(e.sender_id)
    if user['balance'] < PRICE_PER_DAY:
        return await e.answer(f"❌ Bạn cần ít nhất {PRICE_PER_DAY:,} VNĐ", alert=True)

    async with bot.conversation(e.sender_id) as conv:
        try:
            await conv.send_message("📞 **Bước 1/3:** Nhập số điện thoại (VD: +84123...):")
            phone = (await conv.get_response()).text.strip().replace(" ", "")
            
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            await client.send_code_request(phone)
            
            await conv.send_message("📩 **Bước 2/3:** Nhập mã OTP:")
            otp = (await conv.get_response()).text.strip()
            
            try:
                await client.sign_in(phone, otp)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 **Bước 3/3:** Nhập mật khẩu 2FA:")
                pwd = (await conv.get_response()).text.strip()
                await client.sign_in(password=pwd)

            session_str = client.session.save()
            expiry_date = datetime.now(timezone.utc) + timedelta(days=1)
            expiry_iso = expiry_date.isoformat()
            
            # Trừ tiền & Lưu DB
            supabase.table("users").update({"balance": user['balance'] - PRICE_PER_DAY}).eq("user_id", e.sender_id).execute()
            supabase.table("my_clones").insert({
                "owner_id": e.sender_id, "phone": phone, 
                "session": session_str, "expiry": expiry_iso
            }).execute()

            await conv.send_message(f"✅ **THÀNH CÔNG!**\nClone `{phone}` đang hoạt động.")
            
            # Cập nhật lời gọi hàm
            asyncio.create_task(worker_grab_loop(client, phone, e.sender_id, expiry_iso))
            
        except Exception as ex:
            await conv.send_message(f"❌ **LỖI:** {str(ex)}")

# ==========================================================
#                   TÍNH NĂNG ADMIN
# ==========================================================
@bot.on(events.NewMessage(pattern="/admin"))
async def admin_cmd(e):
    if e.sender_id != ADMIN_ID: return
    btns = [
        [TButton.inline("📊 THỐNG KÊ", b"admin_stats"), TButton.inline("📢 THÔNG BÁO", b"admin_cast")],
        [TButton.inline("💰 CỘNG/TRỪ TIỀN", b"admin_money")],
        [TButton.inline("❌ ĐÓNG MENU", b"admin_close")]
    ]
    await e.respond("👨‍💻 **QUẢN TRỊ VIÊN**", buttons=btns)

@bot.on(events.CallbackQuery(pattern=re.compile(b"admin_.*")))
async def admin_cb_handler(e):
    if e.sender_id != ADMIN_ID: return
    data = e.data.decode()
    
    if data == "admin_stats":
        u_res = supabase.table("users").select("*").execute()
        c_res = supabase.table("my_clones").select("*").execute()
        txt = (f"📊 **THỐNG KÊ**\n\n"
               f"👥 Người dùng: {len(u_res.data)}\n"
               f"📱 Clone đang chạy: {len(c_res.data)}\n"
               f"💰 Tổng tiền ví: {sum(u['balance'] for u in u_res.data):,}")
        await e.edit(txt, buttons=[[TButton.inline("🔙 QUAY LẠI", b"admin_back")]])
        
    elif data == "admin_back":
        await admin_cmd(e)

    elif data == "admin_money":
        await e.delete()
        async with bot.conversation(e.sender_id) as conv:
            await conv.send_message("👤 Nhập ID khách:")
            tid = int((await conv.get_response()).text)
            await conv.send_message("💰 Số tiền (âm để trừ):")
            amt = int((await conv.get_response()).text)
            
            user = db_get_user(tid)
            new_bal = user['balance'] + amt
            supabase.table("users").update({"balance": new_bal}).eq("user_id", tid).execute()
            await conv.send_message(f"✅ Xong! ID {tid} có: {new_bal:,}đ")

# ==========================================================
#                   FLASK WEBHOOK (RENDER)
# ==========================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!", 200

@app.route('/sepay-webhook', methods=['POST'])
def webhook():
    d = request.json
    content = d.get("content", "").upper()
    m = re.search(r'NAP\s+(\d+)', content)
    if m:
        uid, amt = int(m.group(1)), int(d.get("transferAmount", 0))
        user = db_get_user(uid)
        new_bal = user['balance'] + amt
        supabase.table("users").update({"balance": new_bal}).eq("user_id", uid).execute()
        asyncio.run_coroutine_threadsafe(bot.send_message(uid, f"✅ **NẠP THÀNH CÔNG!**\n💰 +{amt:,} VNĐ"), asyncio.get_event_loop())
    return jsonify({"status": "ok"}), 200

# ==========================================================
#                   KHỞI CHẠY
# ==========================================================
async def main():
    await bot.start(bot_token=BOT_TOKEN)
    try:
        clones = supabase.table("my_clones").select("*").execute()
        for c in clones.data:
            cl = TelegramClient(StringSession(c['session']), API_ID, API_HASH)
            # Cập nhật lời gọi hàm
            asyncio.create_task(worker_grab_loop(cl, c['phone'], c['owner_id'], c['expiry']))
    except: pass
    
    print(">>> BOT MAIN.PY ĐANG CHẠY... <<<")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
                                
