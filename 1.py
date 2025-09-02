import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

# BOT_TOKEN = "7646223205:AAHBuit0gTN702jLKHo57_ZA4ypuURFuh1A"
BOT_TOKEN="8434943141:AAGiaks6xSsBTRXxBFsQ80igHj9naV0jU_U"

dp = Dispatcher()

@dp.message(Command("ok"))
async def group_ok_command(message: Message):
    print(message)
    chat_id = -1002742922777      # Sen guruh ID
    topic_id = 9                  # "Jadval" mavzusining message_thread_id

   
    await message.answer("OK qabul qilindi ✅")

async def main():
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
