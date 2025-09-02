import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

BOT_TOKEN = "7646223205:AAHBuit0gTN702jLKHo57_ZA4ypuURFuh1A"

dp = Dispatcher()

@dp.message(Command("ok"))
async def group_ok_command(message: Message):
    print(message)
    chat_id = -1002854303799      # Sen guruh ID
    topic_id = 9                  # "Jadval" mavzusining message_thread_id

    # Faqat guruhda ishlasin
    if message.chat.type in ["group", "supergroup"]:
        await message.bot.send_message(
            chat_id=chat_id,
            text="Salom! 👋 Bu xabar to‘g‘ridan-to‘g‘ri Jadval mavzusiga yuborildi.",
            message_thread_id=topic_id
        )

async def main():
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
