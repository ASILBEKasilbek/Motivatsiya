# bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import router
from database import init_db
from scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    # Ma'lumotlar bazasini ishga tushirish
    init_db()

    # Avtomatik savollar yuborishni sozlash
    setup_scheduler(bot)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())