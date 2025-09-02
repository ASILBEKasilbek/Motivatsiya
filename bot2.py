import sqlite3
import asyncio
from datetime import datetime, date
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
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

bot = Bot(
    API_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
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

# ---------------- HANDLERS ----------------
@dp.message(Command("start"))
async def start_cmd(msg: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ro‘yxatdan o‘tish", callback_data="register")]
    ])
    await msg.answer(
        "<b>Assalomu alaykum!</b>\n\n"
        "Botga xush kelibsiz! Ro‘yxatdan o‘tish uchun quyidagi formatda ma‘lumotlarni yuboring:\n\n"
        "<i>Ism, Familya, Universitet(maktab), Kurs(sinf), Min_pomidor, Max_pomidor</i>\n\n"
        "Masalan:\n<code>Asilbek, Sadullayev, PDP University, 2, 12, 20</code>\n\n"
        "Yoki quyidagi tugmani bosing:",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "register")
async def prompt_register(callback: CallbackQuery):
    await callback.message.answer(
        "Iltimos, ma‘lumotlarni quyidagi formatda yuboring:\n"
        "<code>Ism, Familya, Universitet(maktab), Kurs(sinf), Min_pomidor, Max_pomidor</code>\n"
        "Masalan: <code>Asilbek, Sadullayev, PDP University, 2, 12, 20</code>"
    )
    await callback.answer()

@dp.message()
async def register_user(msg: Message):
    parts = msg.text.split(",")
    if len(parts) == 6:
        try:
            ism, familya, muassasa, kurs, min_p, max_p = [p.strip() for p in parts]
            kurs, min_p, max_p = int(kurs), int(min_p), int(max_p)

            conn = sqlite3.connect("daily_reports.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username=?", (msg.from_user.username or str(msg.from_user.id),))
            if cursor.fetchone():
                await msg.answer("⚠️ Siz allaqachon ro‘yxatdan o‘tgansiz!")
                conn.close()
                return

            cursor.execute("""
                INSERT INTO users (username, ism, familya, muassasa, kurs_sinf, min_pomidor, max_pomidor)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (msg.from_user.username or str(msg.from_user.id),
                  ism, familya, muassasa, kurs, min_p, max_p))
            conn.commit()
            conn.close()

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Hisobot yuborish", callback_data="start_report")]
            ])
            await msg.answer("✅ Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz! Hisobot yuborish uchun tugmani bosing:", reply_markup=keyboard)
        except ValueError:
            await msg.answer("⚠️ Kurs, min_pomidor va max_pomidor son bo‘lishi kerak!")
        except Exception as e:
            await msg.answer(f"⚠️ Xatolik yuz berdi: {str(e)}")
    else:
        await msg.answer("⚠️ Ma‘lumotlarni to‘liq yuboring!")

@dp.callback_query(F.data == "start_report")
@dp.message(Command("report"))
async def start_report(msg_or_callback: Message | CallbackQuery):
    user_id = msg_or_callback.from_user.id if isinstance(msg_or_callback, Message) else msg_or_callback.from_user.id
    today = date.today()
    kun = (today - date(2025, 1, 1)).days + 1

    user_sessions[user_id] = {
        "kun": kun,
        "report_date": today,
        "entries": []
    }

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Hisobot qo'shish", callback_data=f"add_report_{user_id}")],
        [InlineKeyboardButton(text="Yakunlash", callback_data=f"done_report_{user_id}")]
    ])

    text = (
        f"📌 <b>DAY {kun}</b>\n📣 <b>Bugungi reja 📝</b>\n\n"
        "Fan nomini, pomidor sonini va holatni yuboring:\n"
        "<code>Fan, Pomidor, ✅|❌</code>\nMasalan: <code>Matematika, 3, ✅</code>\n\n"
        "Yangi hisobot qo‘shish uchun tugmani bosing yoki ma‘lumot yuboring."
    )

    if isinstance(msg_or_callback, Message):
        await msg_or_callback.answer(text, reply_markup=keyboard)
    else:
        await msg_or_callback.message.answer(text, reply_markup=keyboard)
        await msg_or_callback.answer()

@dp.callback_query(F.data.startswith("add_report_"))
async def prompt_add_report(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    if user_id not in user_sessions:
        await callback.message.answer("⚠️ Iltimos, avval <b>/report</b> buyrug‘ini ishga tushiring.")
        await callback.answer()
        return

    await callback.message.answer(
        "Yangi hisobot qo‘shish uchun quyidagi formatda yuboring:\n"
        "<code>Fan, Pomidor, ✅|❌</code>\nMasalan: <code>Matematika, 3, ✅</code>"
    )
    await callback.answer()

@dp.message(F.text.regexp(r"(.+),\s*(\d+),\s*(✅|❌)"))
async def handle_report(msg: Message):
    user_id = msg.from_user.id
    if user_id not in user_sessions:
        await msg.answer("⚠️ Iltimos, avval <b>/report</b> buyrug‘ini ishga tushiring.")
        return

    match = re.match(r"(.+),\s*(\d+),\s*(✅|❌)", msg.text)
    if not match:
        await msg.answer("⚠️ Noto‘g‘ri format! Misol: <code>Matematika, 3, ✅</code>")
        return

    subject, pomidor, status = match.groups()
    pomidor = int(pomidor)
    completed = status == "✅"

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
        f"✅ Qabul qilindi: <b>{subject.strip()}</b>, {pomidor} 🍅, {status}",
        reply_markup=keyboard
    )

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

    text = f"👤 <b>{ism}</b>\n📌 <b>DAY {kun}</b>\n📣 <b>Bugungi reja 📝</b>\n\n"
    for i, entry in enumerate(entries, 1):
        status = "✅" if entry["completed"] else "❌"
        text += f"{i}. {entry['subject']} – {entry['pomidor']} ta 🍅 {status}\n"
    text += f"\n<b>Jami:</b> {jami_pomidor} ta pomidor 🍅\n"
    text += f"📈 <i>Bugungi rivojlanish darajasi:</i> {development_level:.1f}%\n"
    text += f"⏳ <i>Bugun o‘qishga sarflangan vaqt:</i> {hours_spent:.2f} soat\n"
    text += f"📅 <i>Sana:</i> {report_date.strftime('%d.%m.%Y')}"

    topic = TOPIC_NORMAL
    if jami_pomidor <= min_p:
        topic = TOPIC_MIN
    elif jami_pomidor >= max_p:
        topic = TOPIC_MAX

    await bot.send_message(CHAT_ID, text, message_thread_id=topic)
    conn.close()
    del user_sessions[user_id]
    await callback.message.answer("✅ Hisobot muvaffaqiyatli yuborildi!")
    await callback.answer()

# ---------------- JOBS ----------------
async def ask_users():
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, ism, username FROM users")
    users = cursor.fetchall()
    conn.close()

    today = date.today()
    kun = (today - date(2025, 1, 1)).days + 1

    for user_id, ism, username in users:
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
                "Hisobot qo‘shish uchun tugmani bosing:",
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
    kun = (today - date(2025, 1, 1)).days + 1

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
        f"📊 <b>Kunlik hisobot</b> – DAY {kun}\n\n"
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

# ---------------- MAIN ----------------
async def main():
    init_db()
    setup_scheduler()
    print("🤖 Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())