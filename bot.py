import sqlite3
import asyncio
from datetime import datetime, date
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, BotCommand
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
import os
import re
from aiogram.client.default import DefaultBotProperties

# ---------------- CONFIG ----------------
load_dotenv()

API_TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID", 0))
TOPIC_JADVAL = int(os.getenv("TOPIC_JADVAL", 0))
TOPIC_MIN = int(os.getenv("TOPIC_MIN", 0))
TOPIC_NORMAL = int(os.getenv("TOPIC_NORMAL", 0))
TOPIC_MAX = int(os.getenv("TOPIC_MAX", 0))
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip().isdigit()]

bot = Bot(API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# Session storage (user -> report data)
user_sessions = {}

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            ism TEXT NOT NULL,
            familya TEXT NOT NULL,
            muassasa TEXT NOT NULL,
            kurs_sinf INTEGER NOT NULL,
            min_pomidor INTEGER NOT NULL,
            max_pomidor INTEGER NOT NULL,
            start_day INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            kun INTEGER NOT NULL,
            subject TEXT NOT NULL,
            pomidor INTEGER NOT NULL,
            completed BOOLEAN NOT NULL,
            report_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

# ---------------- UTILS ----------------
def get_user_day(user_id: int) -> int:
    """Foydalanuvchining joriy kunini hisoblash."""
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    cursor.execute("SELECT start_day, created_at FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        start_day, created_at = result
        created_date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").date()
        today = date.today()
        days_passed = (today - created_date).days
        return start_day + days_passed
    return 1

def escape_md_v2(text: object) -> str:
    """Escape text for Telegram MarkdownV2."""
    if text is None:
        return ""
    s = str(text)
    escape_chars = "_*[]()~`>#+-=|{}.!"
    for ch in escape_chars:
        s = s.replace(ch, "\\" + ch)
    return s

# ---------------- ADMIN PANEL ----------------
def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    return user_id in ADMIN_IDS

@dp.message(Command("admin"))
async def admin_panel(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("⚠️ Sizda admin huquqlari yo‘q!")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Umumiy statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilarni boshqarish", callback_data="admin_users")],
        [InlineKeyboardButton(text="📢 E'lon yuborish", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📅 Hisobotlar", callback_data="admin_reports")]
    ])
    await msg.answer(
        "<b>🔧 Admin Paneli</b>\n\n"
        "Quyidagi funksiyalardan birini tanlang:",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.message.answer("⚠️ Sizda admin huquqlari yo‘q!")
        await callback.answer()
        return

    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM daily_reports WHERE report_date = ?", (date.today(),))
    active_users = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(pomidor) FROM daily_reports WHERE report_date = ?", (date.today(),))
    total_pomidors = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT u.ism, SUM(d.pomidor) as total
        FROM users u
        LEFT JOIN daily_reports d ON u.id = d.user_id
        GROUP BY u.id, u.ism
        ORDER BY total DESC
        LIMIT 5
    """)
    top_users = cursor.fetchall()

    conn.close()

    text = (
        f"📊 <b>Umumiy Statistikalar</b>\n\n"
        f"👥 Jami foydalanuvchilar: {total_users} ta\n"
        f"📈 Bugun faol foydalanuvchilar: {active_users} ta\n"
        f"🍅 Bugungi jami pomidorlar: {total_pomidors} ta\n\n"
        f"🏆 Top 5 foydalanuvchilar (jami pomidorlar):\n"
    )
    for i, (ism, total) in enumerate(top_users, 1):
        total = total or 0
        text += f"{i}. {ism} – {total} ta 🍅\n"

    await callback.message.answer(text)
    await callback.answer()

@dp.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.message.answer("⚠️ Sizda admin huquqlari yo‘q!")
        await callback.answer()
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Foydalanuvchilar ro‘yxati", callback_data="list_users")],
        [InlineKeyboardButton(text="🗑 Foydalanuvchini o‘chirish", callback_data="delete_user")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_admin")]
    ])
    await callback.message.answer(
        "<b>👥 Foydalanuvchilarni boshqarish</b>\n\n"
        "Quyidagi amallardan birini tanlang:",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == "list_users")
async def list_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.message.answer("⚠️ Sizda admin huquqlari yo‘q!")
        await callback.answer()
        return

    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, ism, familya, username FROM users")
    users = cursor.fetchall()
    conn.close()

    if not users:
        await callback.message.answer("📋 Foydalanuvchilar ro‘yxati bo‘sh!")
        await callback.answer()
        return

    text = "<b>📋 Foydalanuvchilar ro‘yxati</b>\n\n"
    for user in users:
        user_id, ism, familya, username = user
        text += f"ID: {user_id} | {ism} {familya} | @{username}\n"

    await callback.message.answer(text)
    await callback.answer()

@dp.callback_query(F.data == "delete_user")
async def prompt_delete_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.message.answer("⚠️ Sizda admin huquqlari yo‘q!")
        await callback.answer()
        return

    await callback.message.answer(
        "O‘chiriladigan foydalanuvchi ID sini yuboring.\n"
        "Masalan: <code>123</code>"
    )
    await callback.answer()

@dp.message(F.text.regexp(r"^\d+$"))
async def delete_user(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("⚠️ Sizda admin huquqlari yo‘q!")
        return

    user_id = int(msg.text)
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, ism FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        await msg.answer(f"⚠️ ID {user_id} ga ega foydalanuvchi topilmadi!")
        conn.close()
        return

    cursor.execute("DELETE FROM daily_reports WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    await msg.answer(f"✅ Foydalanuvchi {user[1]} (ID: {user_id}) muvaffaqiyatli o‘chirildi!")

@dp.callback_query(F.data == "admin_broadcast")
async def prompt_broadcast(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.message.answer("⚠️ Sizda admin huquqlari yo‘q!")
        await callback.answer()
        return

    await callback.message.answer(
        "E'lon matnini yuboring:\n"
        "Masalan: <code>E'lon: Yangi funksiyalar qo‘shildi!</code>"
    )
    await callback.answer()

@dp.message(F.text.startswith("E'lon:"))
async def send_broadcast(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("⚠️ Sizda admin huquqlari yo‘q!")
        return

    broadcast_message = msg.text.replace("E'lon:", "").strip()
    if not broadcast_message:
        await msg.answer("⚠️ E'lon matni bo‘sh bo‘lmasligi kerak!")
        return

    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users")
    users = cursor.fetchall()
    conn.close()

    sent_count = 0
    for user in users:
        try:
            user_id = user[0] if not user[0].startswith("@") else user[0][1:]
            await bot.send_message(
                user_id,
                f"📢 <b>E'lon:</b> {broadcast_message}"
            )
            sent_count += 1
        except Exception as e:
            print(f"E'lon yuborishda xatolik (user: {user[0]}): {str(e)}")

    await msg.answer(f"✅ E'lon {sent_count} ta foydalanuvchiga yuborildi!")

@dp.callback_query(F.data == "admin_reports")
async def admin_reports(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.message.answer("⚠️ Sizda admin huquqlari yo‘q!")
        await callback.answer()
        return

    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.ism, d.kun, d.subject, d.pomidor, d.completed, d.report_date
        FROM daily_reports d
        JOIN users u ON d.user_id = u.id
        WHERE d.report_date = ?
        ORDER BY d.created_at DESC
        LIMIT 10
    """, (date.today(),))
    reports = cursor.fetchall()
    conn.close()

    if not reports:
        await callback.message.answer("📅 Bugungi hisobotlar topilmadi!")
        await callback.answer()
        return

    text = "<b>📅 Bugungi hisobotlar (oxirgi 10 ta)</b>\n\n"
    for report in reports:
        ism, kun, subject, pomidor, completed, report_date = report
        status = "✅" if completed else "❌"
        text += f"👤 {ism} | Day {kun} | {subject} | {pomidor} 🍅 | {status} | {report_date}\n"

    await callback.message.answer(text)
    await callback.answer()

@dp.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.message.answer("⚠️ Sizda admin huquqlari yo‘q!")
        await callback.answer()
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Umumiy statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilarni boshqarish", callback_data="admin_users")],
        [InlineKeyboardButton(text="📢 E'lon yuborish", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📅 Hisobotlar", callback_data="admin_reports")]
    ])
    await callback.message.answer(
        "<b>🔧 Admin Paneli</b>\n\n"
        "Quyidagi funksiyalardan birini tanlang:",
        reply_markup=keyboard
    )
    await callback.answer()

# ---------------- EXISTING HANDLERS ----------------
@dp.message(Command("start"))
async def start_cmd(msg: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ro‘yxatdan o‘tish", callback_data="register")]
    ])
    await msg.answer(
        "<b>Assalomu alaykum!</b>\n\n"
        "Botga xush kelibsiz! Ro‘yxatdan o‘tish uchun quyidagi formatda ma‘lumotlarni yuboring:\n\n"
        "<i>Ism, Familya, Universitet(maktab), Kurs(sinf), Min_pomidor, Max_pomidor, Boshlang‘ich_kun</i>\n\n"
        "Masalan:\n<code>Asilbek, Sadullayev, PDP University, 2, 12, 20, 24</code>\n\n"
        "Eslatma: Boshlang‘ich kun 1 yoki undan katta bo‘lishi kerak.\n"
        "Ro‘yxatdan o‘tish uchun tugmani bosing:",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "register")
async def prompt_register(callback: CallbackQuery):
    await callback.message.answer(
        "Iltimos, ma‘lumotlarni quyidagi formatda yuboring:\n"
        "<code>Ism, Familya, Universitet(maktab), Kurs(sinf), Min_pomidor, Max_pomidor, Boshlang‘ich_kun</code>\n"
        "Masalan: <code>Asilbek, Sadullayev, PDP University, 2, 12, 20, 24</code>\n"
        "Eslatma: Boshlang‘ich kun 1 yoki undan katta bo‘lishi kerak."
    )
    await callback.answer()

@dp.callback_query(F.data == "start_report")
@dp.message(Command("report"))
async def start_report(msg_or_callback: Message | CallbackQuery):
    user_id = msg_or_callback.from_user.id
    today = date.today()
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username=?", (msg_or_callback.from_user.username or str(user_id),))
    user_data = cursor.fetchone()
    conn.close()

    if not user_data:
        await (msg_or_callback.answer if isinstance(msg_or_callback, Message) else msg_or_callback.message.answer)(
            "⚠️ Siz ro‘yxatdan o‘tmagansiz! Iltimos, /start buyrug‘i bilan ro‘yxatdan o‘ting."
        )
        return

    kun = get_user_day(user_data[0])
    user_sessions[user_id] = {
        "kun": kun,
        "report_date": today,
        "entries": []
    }

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Yakunlash", callback_data=f"done_report_{user_id}")]
    ])

    text = (
        f"📌 <b>DAY {kun}</b>\n📣 <b>Bugungi reja 📝</b>\n\n"
        "Fan nomini, pomidor sonini va holatni quyidagi formatda yuboring:\n"
        "<code>Fan, Pomidor, ✅|❌</code>\nMasalan: <code>Matematika, 3, ✅</code>\n\n"
        "Hisobotni kiritib bo‘lgach, 'Yakunlash' tugmasini bosing."
    )

    if isinstance(msg_or_callback, Message):
        await msg_or_callback.answer(text, reply_markup=keyboard)
    else:
        await msg_or_callback.message.answer(text, reply_markup=keyboard)
        await msg_or_callback.answer()

@dp.message(F.text.regexp(r"(.+),\s*(\d+),\s*(✅|❌)"))
async def handle_report(msg: Message):
    user_id = msg.from_user.id
    if user_id not in user_sessions:
        await msg.answer("⚠️ Iltimos, avval <b>/report</b> buyrug‘ini ishga tushiring.")
        return

    match = re.match(r"(.+),\s*(\d+),\s*(✅|❌)", msg.text)
    if not match:
        await msg.answer("⚠️ Noto‘g‘ri format! Quyidagi formatda yuboring: <code>Fan, Pomidor, ✅|❌</code>\nMasalan: <code>Matematika, 3, ✅</code>")
        return

    subject, pomidor, status = match.groups()
    pomidor = int(pomidor)
    completed = status == "✅"

    if not subject.strip():
        await msg.answer("⚠️ Fan nomi bo‘sh bo‘lmasligi kerak! Masalan: <code>Matematika, 3, ✅</code>")
        return
    if pomidor <= 0:
        await msg.answer("⚠️ Pomidor soni musbat bo‘lishi kerak! Masalan: <code>Matematika, 3, ✅</code>")
        return

    user_sessions[user_id]["entries"].append({
        "subject": subject.strip(),
        "pomidor": pomidor,
        "completed": completed
    })

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Yana qo‘shish", callback_data=f"add_report_{user_id}")],
        [InlineKeyboardButton(text="Yakunlash", callback_data=f"done_report_{user_id}")]
    ])

    await msg.answer(
        f"✅ Qabul qilindi: <b>{subject.strip()}</b>, {pomidor} 🍅, {status}\n\n"
        "Yana hisobot qo‘shish uchun quyidagi formatda yuboring yoki tugmalardan foydalaning.",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("add_report_"))
async def prompt_add_report(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    if user_id not in user_sessions:
        await callback.message.answer("⚠️ Iltimos, avval <b>/report</b> buyrug‘ini ishga tushiring.")
        await callback.answer()
        return

    await callback.message.answer(
        "Yana hisobot qo‘shish uchun quyidagi formatda yuboring:\n"
        "<code>Fan, Pomidor, ✅|❌</code>\nMasalan: <code>Matematika, 3, ✅</code>\n"
        "Eslatma: Fan nomi bo‘sh bo‘lmasligi va pomidor soni musbat bo‘lishi kerak."
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("done_report_"))
async def done_report(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    if user_id not in user_sessions:
        await callback.message.answer("⚠️ Faol hisobot sessiyasi yo‘q.")
        await callback.answer()
        return

    report = user_sessions[user_id]
    kun, report_date, entries = report["kun"], report["report_date"], report["entries"]

    if not entries:
        await callback.message.answer("⚠️ Hech qanday hisobot qo‘shilmadi!")
        await callback.answer()
        return

    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, min_pomidor, max_pomidor, ism FROM users WHERE username=?",
                   (callback.from_user.username or str(user_id),))
    user_data = cursor.fetchone()
    if not user_data:
        await callback.message.answer("⚠️ Siz ro‘yxatdan o‘tmagansiz!")
        conn.close()
        await callback.answer()
        return
    db_user_id, min_p, max_p, ism = user_data

    for entry in entries:
        cursor.execute("""
            INSERT INTO daily_reports (user_id, kun, subject, pomidor, completed, report_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (db_user_id, kun, entry["subject"], entry["pomidor"], entry["completed"], report_date))

    conn.commit()

    # Summary
    jami_pomidor = sum(entry["pomidor"] for entry in entries)
    hours_spent = (jami_pomidor * 25) / 60
    development_level = kun * 0.1

    text = (
        f"> 👤 *{escape_md_v2(ism)}*\n\n"
        f"> 📌 *DAY {escape_md_v2(kun)}*\n\n"
        f"> 📣 *Bugungi reja 📝*\n\n"
        ">\n"
    )

    for i, entry in enumerate(entries, 1):
        subject = escape_md_v2(entry.get("subject", ""))
        pomidor = escape_md_v2(entry.get("pomidor", ""))
        status = "✅" if entry.get("completed") else "❌"
        text += f"> {escape_md_v2(i)}\\. {subject} – {pomidor} ta 🍅 {status}\n"

    text += f">\n> *Jami:* {escape_md_v2(jami_pomidor)} ta pomidor 🍅\n\n"
    dev_str = escape_md_v2(f"{development_level:.1f}")
    hours_str = escape_md_v2(f"{hours_spent:.2f}")
    text += f"> 📈 Bugungi rivojlanish darajasi: {dev_str}%\n\n"
    text += f"> ⏳ Bugun o‘qishga sarflangan vaqt: {hours_str} soat\n\n"
    date_str = escape_md_v2(report_date.strftime("%d.%m.%Y"))
    text += f"> 📅 Sana: {date_str}"

    topic = TOPIC_NORMAL
    if jami_pomidor <= min_p:
        topic = TOPIC_MIN
    elif jami_pomidor >= max_p:
        topic = TOPIC_MAX

    await bot.send_message(
        CHAT_ID,
        text,
        message_thread_id=topic,
        parse_mode="MarkdownV2"
    )

    conn.close()
    del user_sessions[user_id]
    await callback.message.answer("✅ Hisobot muvaffaqiyatli yuborildi!")
    await callback.answer()

@dp.message()
async def register_user(msg: Message):
    if re.match(r"(.+),\s*(\d+),\s*(✅|❌)", msg.text):
        return

    parts = msg.text.split(",")
    if len(parts) == 7:
        try:
            ism, familya, muassasa, kurs, min_p, max_p, start_day = [p.strip() for p in parts]
            kurs, min_p, max_p, start_day = int(kurs), int(min_p), int(max_p), int(start_day)

            if start_day < 1:
                await msg.answer("⚠️ Boshlang‘ich kun 1 yoki undan katta bo‘lishi kerak!")
                return
            if min_p < 0 or max_p < min_p:
                await msg.answer("⚠️ Min_pomidor va Max_pomidor musbat sonlar bo‘lishi va Max_pomidor Min_pomidordan katta bo‘lishi kerak!")
                return

            conn = sqlite3.connect("daily_reports.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username=?", (msg.from_user.username or str(msg.from_user.id),))
            if cursor.fetchone():
                await msg.answer("⚠️ Siz allaqachon ro‘yxatdan o‘tgansiz!")
                conn.close()
                return

            cursor.execute("""
                INSERT INTO users (username, ism, familya, muassasa, kurs_sinf, min_pomidor, max_pomidor, start_day)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (msg.from_user.username or str(msg.from_user.id),
                  ism, familya, muassasa, kurs, min_p, max_p, start_day))
            conn.commit()
            conn.close()

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Hisobot yuborish", callback_data="start_report")]
            ])
            await msg.answer(f"✅ Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz! Hisobotlaringiz {start_day}-kundan boshlanadi. Hisobot yuborish uchun tugmani bosing:", reply_markup=keyboard)
        except ValueError:
            await msg.answer("⚠️ Kurs, Min_pomidor, Max_pomidor va Boshlang‘ich_kun son bo‘lishi kerak!")
        except Exception as e:
            await msg.answer(f"⚠️ Xatolik yuz berdi: {str(e)}")
    else:
        await msg.answer("⚠️ Ma‘lumotlarni to‘liq yuboring! Format: <code>Ism, Familya, Universitet(maktab), Kurs(sinf), Min_pomidor, Max_pomidor, Boshlang‘ich_kun</code>")

# ---------------- JOBS ----------------
async def ask_users():
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, ism, username FROM users")
    users = cursor.fetchall()
    conn.close()

    today = date.today()
    for user_id, ism, username in users:
        kun = get_user_day(user_id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Hisobot yuborish", callback_data="start_report")],
            [InlineKeyboardButton(text="Keyinroq", callback_data=f"remind_later_{user_id}")]
        ])
        try:
            await bot.send_message(
                user_id,
                f"👤 <b>{ism}</b>, bugungi hisobotingizni yuboring!\n\n"
                f"📌 <b>DAY {kun}</b>\n📣 <b>Bugungi reja 📝</b>\n\n"
                "Fan nomini, pomidor sonini va holatni yuboring:\n"
                "<code>Fan, Pomidor, ✅|❌</code>\nMasalan: <code>Matematika, 3, ✅</code>\n\n"
                "Hisobot qo‘shish uchun tugmani bosing yoki to‘g‘ridan-to‘g‘ri ma’lumot yuboring:",
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Xatolik yuz berdi (user_id: {user_id}): {str(e)}")

@dp.callback_query(F.data.startswith("remind_later_"))
async def remind_later(callback: CallbackQuery):
    await callback.message.answer("🕒 Hisobotni keyinroq yuborishingiz mumkin. /report buyrug‘i bilan boshlang.")
    await callback.answer()

async def send_reports():
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    today = date.today()

    # Top 6 users
    cursor.execute("""
        SELECT u.ism, SUM(d.pomidor) as total
        FROM users u
        LEFT JOIN daily_reports d ON u.id = d.user_id AND d.report_date = ?
        GROUP BY u.id, u.ism
        ORDER BY total DESC
        LIMIT 6
    """, (today,))
    top_users = cursor.fetchall()

    # Total users and statistics
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM daily_reports WHERE report_date = ?", (today,))
    active_users = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(pomidor) FROM daily_reports WHERE report_date = ?", (today,))
    total_pomidors = cursor.fetchone()[0] or 0

    text = (
        f"📊 <b>Kunlik hisobot</b> – Sana: {today.strftime('%d.%m.%Y')}\n\n"
        f"👥 <b>Jami a'zolar:</b> {total_users} ta\n"
        f"📈 <b>Faol ishtirokchilar:</b> {active_users} ta\n"
        f"🍅 <b>Jami pomidorlar:</b> {total_pomidors} ta\n\n"
        f"🏆 <b>Top 6 ishtirokchilar:</b>\n"
    )
    for i, (ism, total) in enumerate(top_users, 1):
        total = total or 0
        text += f"{i}. {ism} – {total} ta 🍅\n"
    text += f"\n📅 <i>Sana:</i> {today.strftime('%d.%m.%Y')}"

    await bot.send_message(CHAT_ID, text, message_thread_id=TOPIC_JADVAL)
    conn.close()

# ---------------- SCHEDULER ----------------
def setup_scheduler():
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    scheduler.add_job(ask_users, "cron", hour=20, minute=0)
    scheduler.add_job(send_reports, "cron", hour=0, minute=0)
    scheduler.start()
    return scheduler

async def set_default_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="⚪️ Botni ishga tushirish"),
        BotCommand(command="report", description="📝 Hisobot yuborish"),
        BotCommand(command="admin", description="🔧 Admin paneli (adminlar uchun)")
    ]
    await bot.set_my_commands(commands)

# ---------------- MAIN ----------------
async def main():
    init_db()
    await set_default_commands(bot)
    setup_scheduler()
    print("🤖 Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())