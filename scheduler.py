# scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from database import sqlite3
from quotes import get_motivational_message

async def send_daily_questions(bot: Bot):
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, reminder_time, current_streak FROM user_settings")
    users = cursor.fetchall()
    conn.close()

    for user_id, reminder_time, streak in users:
        await bot.send_message(
            chat_id=user_id,
            text=f"🌟 {streak + 1}-kun hisobot vaqti! /report buyrug‘ini yuboring.\n\n💬 {get_motivational_message(streak + 1)}"
        )

def setup_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_daily_questions,
        trigger="cron",
        hour=20,  # Default vaqt, foydalanuvchi sozlamalariga qarab o‘zgaradi
        minute=0,
        kwargs={"bot": bot}
    )
    scheduler.start()