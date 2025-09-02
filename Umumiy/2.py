import sqlite3
import asyncio
from datetime import datetime, date
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, RegexpCommandsFilter
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

import os 
load_dotenv()
# ---------------- CONFIG ----------------
API_TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID", 0))
TOPIC_JADVAL = int(os.getenv("TOPIC_JADVAL", 0))
TOPIC_MIN = int(os.getenv("TOPIC_MIN", 0))
TOPIC_NORMAL = int(os.getenv("TOPIC_NORMAL", 0))
TOPIC_MAX = int(os.getenv("TOPIC_MAX", 0))


bot = Bot(API_TOKEN, parse_mode="MarkdownV2")
dp = Dispatcher()

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()

    # Users table
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

    # Daily reports table
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
    await msg.answer(
        "Assalomu alaykum! Ro‘yxatdan o‘tish uchun ma‘lumotlarni quyidagi formatda yuboring:\n"
        "Ism, Familya, Muassasa, Kurs_sinf, Min_pomidor, Max_pomidor\n"
        "Masalan: `Asilbek, Sadullayev, PDP University, 1, 5, 20`"
    )

@dp.message()
async def register_user(msg: Message):
    parts = msg.text.split(",")
    if len(parts) == 6:
        try:
            ism, familya, muassasa, kurs, min_p, max_p = [p.strip() for p in parts]
            kurs = int(kurs)
            min_p = int(min_p)
            max_p = int(max_p)

            conn = sqlite3.connect("daily_reports.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, ism, familya, muassasa, kurs_sinf, min_pomidor, max_pomidor)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (msg.from_user.username or str(msg.from_user.id), ism, familya, muassasa, kurs, min_p, max_p))
            conn.commit()
            conn.close()

            await msg.answer("✅ Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz!")
        except ValueError:
            await msg.answer("⚠️ Kurs, min_pomidor va max_pomidor son bo‘lishi kerak!")
    else:
        await msg.answer("⚠️ Ma‘lumotlarni to‘liq yuboring!")

@dp.message(Command("report"))
async def start_report(msg: Message):
    user_id = msg.from_user.id
    today = date.today()
    kun = (today - date(2025, 1, 1)).days + 1

    # Initialize user report session
    dp.storage.data.setdefault(user_id, {})['report'] = {
        'kun': kun,
        'report_date': today,
        'entries': []
    }

    keyboard = [[InlineKeyboardButton("Buldi", callback_data=f"done_report_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await msg.answer(
        f"📌 DAY {kun}\n📣 Today Plan 📝\n\n"
        "Fan nomini, pomidor sonini va holatni yuboring:\n"
        "Misol: `Matematika, 3, ✅`\n"
        "Tugallagach, 'Buldi' tugmasini bosing.",
        reply_markup=reply_markup
    )

@dp.message(RegexpCommandsFilter(regexp_commands=[r"(.+),\s*(\d+),\s*(✅|❌)"]))
async def handle_report(msg: Message, regexp_command):
    user_id = msg.from_user.id
    if user_id not in dp.storage.data or 'report' not in dp.storage.data[user_id]:
        await msg.answer("Iltimos, avval /report buyrug‘ini ishga tushiring.")
        return

    subject, pomidor, status = regexp_command.groups()
    pomidor = int(pomidor)
    completed = status == '✅'

    dp.storage.data[user_id]['report']['entries'].append({
        'subject': subject.strip(),
        'pomidor': pomidor,
        'completed': completed
    })

    await msg.answer(f"✅ Qabul qilindi: {subject.strip()}, {pomidor} 🍅, {status}")

@dp.callback_query(F.data.startswith("done_report_"))
async def done_report(callback_query):
    user_id = int(callback_query.data.split("_")[-1])
    if user_id not in dp.storage.data or 'report' not in dp.storage.data[user_id]:
        await callback_query.message.answer("⚠️ Faol hisobot sessiyasi yo‘q.")
        return

    report = dp.storage.data[user_id]['report']
    kun = report['kun']
    report_date = report['report_date']
    entries = report['entries']

    # Save to database
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, min_pomidor, max_pomidor FROM users WHERE username=?", (callback_query.from_user.username or str(user_id),))
    user_data = cursor.fetchone()
    if not user_data:
        await callback_query.message.answer("⚠️ Siz ro‘yxatdan o‘tmagansiz!")
        conn.close()
        return
    db_user_id, min_p, max_p = user_data

    for entry in entries:
        cursor.execute("""
            INSERT INTO daily_reports (user_id, kun, subject, pomidor, completed, report_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (db_user_id, kun, entry['subject'], entry['pomidor'], entry['completed'], report_date))
    
    conn.commit()

    # Calculate summary
    jami_pomidor = sum(entry['pomidor'] for entry in entries)
    hours_spent = (jami_pomidor * 25) / 60
    development_level = kun * 0.1

    # Send user summary
    text = f"📣 Today Plan 📝\n\n"
    for i, entry in enumerate(entries, 1):
        status = "✅" if entry['completed'] else "❌"
        text += f"{i}\\. {entry['subject']} – {entry['pomidor']} ta 🕐{status}\n"
    text += f"\nJami: {jami_pomidor} ta pomidor 🍅\n"
    text += f"📈 Today's level of development is {development_level:.1f}% * DAY {kun}\n"
    text += f"⏳ Today I spent {hours_spent:.2f} hours studying\n"
    text += f"📅 Sana: {report_date.strftime('%d.%m.%Y')}"

    topic = TOPIC_NORMAL
    if jami_pomidor <= min_p:
        topic = TOPIC_MIN
    elif jami_pomidor >= max_p:
        topic = TOPIC_MAX

    await callback_query.message.reply(text=text.replace(".", "\\.").replace("-", "\\-"), message_thread_id=topic)

    conn.close()
    # Clear session
    del dp.storage.data[user_id]['report']
    await callback_query.answer()

# ---------------- JOBS ----------------
async def ask_users():
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, ism FROM users")
    users = cursor.fetchall()
    conn.close()

    today = date.today()
    kun = (today - date(2025, 1, 1)).days + 1

    for user_id, ism in users:
        keyboard = [[InlineKeyboardButton("Buldi", callback_data=f"done_report_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await bot.send_message(
            CHAT_ID,
            f"👤 {ism}, bugun nechta pomidor qildingiz?\n"
            f"📌 DAY {kun}\n📣 Today Plan 📝\n\n"
            "Fan nomini, pomidor sonini va holatni yuboring:\n"
            "Misol: `Matematika, 3, ✅`\n"
            "Tugallagach, 'Buldi' tugmasini bosing.",
            message_thread_id=TOPIC_NORMAL,
            reply_markup=reply_markup
        )

async def send_reports():
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    today = date.today()
    kun = (today - date(2025, 1, 1)).days + 1

    # Umumiy jadval (top 6)
    cursor.execute("""
        SELECT u.ism, SUM(d.pomidor) as total
        FROM users u
        LEFT JOIN daily_reports d ON u.id = d.user_id AND d.report_date = ?
        GROUP BY u.id, u.ism
        ORDER BY total DESC
        LIMIT 6
    """, (today,))
    top_users = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM users")
    soni = cursor.fetchone()[0]

    text = f"👤 *A'zolar soni:* {soni} ta\\:\n\n📆 *{kun}\\-kun*\n"
    for i, (ism, total) in enumerate(top_users, 1):
        total = total or 0
        text += f"> {i}\\. {ism} – {total} ta 🍅\n\n"
    text += f"📅 *Sana:* {today.strftime('%d.%m.%Y')}"

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
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())