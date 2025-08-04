# handlers.py
import json
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime
from config import DEFAULT_CHANNEL_ID
from states import ReportForm, SettingsForm
from database import save_report, save_user_settings, get_user_settings, get_report_stats, update_streak
from quotes import get_motivational_message
from aiogram import types
import sqlite3
router = Router()

@router.message(Command("start"))
async def start_command(message: Message):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard= InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistikani ko‘rish", callback_data="stats")]
    ])
    await message.answer(
        "🎉 Salom! Men Kundalik Faoliyat Hisobot Botiman!\n"
        "Har kuni sizning harakatlaringizni kanalda nishonlaymiz. Har bir kun – yangi yutuq!\n\n"
        "🔧 Sozlamalarni o‘zgartirish: /settings\n"
        "📝 Hisobot boshlash: /report\n",
        reply_markup=keyboard
    )

@router.message(Command("settings"))
async def settings_command(message: Message, state: FSMContext):
    await message.answer("Kanal ID yoki username’ni kiriting (masalan, @YourChannel):")
    await state.set_state(SettingsForm.channel_id)

@router.message(SettingsForm.channel_id)
async def process_channel_id(message: Message, state: FSMContext):
    await state.update_data(channel_id=message.text)
    await message.answer("Eslatma vaqtini kiriting (masalan, 20:00):")
    await state.set_state(SettingsForm.reminder_time)

@router.message(SettingsForm.reminder_time)
async def process_reminder_time(message: Message, state: FSMContext):
    await state.update_data(reminder_time=message.text)
    await message.answer("O‘zingiz uchun maxsus savollar kiritmoqchimisiz? (JSON formatida, masalan: [\"Savol 1\", \"Savol 2\"]) yoki \"yo‘q\" deb yozing:")
    await state.set_state(SettingsForm.custom_questions)


@router.message(SettingsForm.custom_questions)
async def process_custom_questions(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    raw_channel_id = data.get("channel_id", DEFAULT_CHANNEL_ID)
    reminder_time = data.get("reminder_time", "20:00")
    custom_questions = message.text if message.text != "yo‘q" else None

    # Kanal ID ni tozalash va mos formatga keltirish
    if isinstance(raw_channel_id, str):
        if raw_channel_id.startswith("https://t.me/"):
            # https link bo‘lsa, @username ajratib olamiz
            channel_username = raw_channel_id.replace("https://t.me/", "")
            if "joinchat" in channel_username or "+" in channel_username:
                # Maxfiy kanal linki — bundaylarni saqlamaslik yoki ogohlantirish kerak
                await message.answer("❌ Maxfiy kanal linkini emas, iltimos oddiy @kanal nomini yuboring.")
                await state.clear()
                return
            channel_id = f"@{channel_username}"
        elif raw_channel_id.startswith("@"):
            channel_id = raw_channel_id
        elif raw_channel_id.isdigit():
            channel_id = int("-100"+str(raw_channel_id))
        else:
            channel_id = DEFAULT_CHANNEL_ID  # Noto‘g‘ri format bo‘lsa defaultdan foydalanamiz
    else:
        channel_id = DEFAULT_CHANNEL_ID

    save_user_settings(user_id, channel_id, reminder_time, custom_questions)

    await message.answer("✅ Sozlamalar saqlandi! Hisobotni boshlash uchun /report buyrug‘ini yuboring.")
    await state.clear()


@router.message(Command("report"))
async def start_report(message: Message, state: FSMContext):
    user_id = message.from_user.id
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    cursor.execute("SELECT date FROM reports WHERE user_id = ? AND date = ?", (user_id, datetime.now().strftime("%Y-%m-%d")))
    print(cursor.fetchone())
    if cursor.fetchone():
        await message.answer("⛔ Bugun allaqachon hisobot yuborgansiz! Ertaga kuting yoki /stats ni tekshiring.")
        conn.close()
        return
    
    conn.close()
    import json

    custom_questions = get_user_settings(user_id)[2]

    # Yaroqli JSON string bo‘lmasa, default savollarni ishlatish
    try:
        questions = json.loads(custom_questions) if custom_questions and custom_questions.strip() else [
            "Bugun nimalarni bajarding? 🌟",
            "Bugun qanday muammolarga duch kelding? ⚠️",
            "Bugun qancha vaqt sarflading ? 🧭"
        ]
    except json.JSONDecodeError:
        questions = [
            "Bugun nimalarni bajarding? 🌟",
            "Bugun qanday muammolarga duch kelding? ⚠️",
            "Bugun qancha vaqt sarflading ? 🧭"
        ]

    await state.update_data(questions=questions, answers=[])
    await message.answer(questions[0])
    await state.set_state(ReportForm.tasks)


@router.message(ReportForm.tasks)
async def process_tasks(message: Message, state: FSMContext):
    data = await state.get_data()
    answers = data.get("answers", [])
    answers.append(message.text)
    await state.update_data(answers=answers)
    
    questions = data.get("questions")
    if len(answers) == 1:
        await message.answer(questions[1])
        await state.set_state(ReportForm.issues)
    elif len(answers) == 2:
        await message.answer(questions[2])
        await state.set_state(ReportForm.plans)
    else:
        await process_final_report(message, state)

@router.message(ReportForm.issues)
async def process_issues(message: Message, state: FSMContext):
    data = await state.get_data()
    answers = data.get("answers", [])
    answers.append(message.text)
    await state.update_data(answers=answers)
    
    questions = data.get("questions")
    await message.answer(questions[2])
    await state.set_state(ReportForm.plans)

@router.message(ReportForm.plans)
async def process_plans(message: Message, state: FSMContext):
    data = await state.get_data()
    answers = data.get("answers", [])
    answers.append(message.text)
    await state.update_data(answers=answers)
    
    await process_final_report(message, state)

async def process_final_report(message: Message, state: FSMContext):
    data = await state.get_data()
    answers = data.get("answers")
    user_id = message.from_user.id
    username = message.from_user.username or "Anonim"
    channel_id = get_user_settings(user_id)[0] or DEFAULT_CHANNEL_ID

    # ❗ Javoblar to'liq bo'lmagan holatlardan himoya
    if not answers or len(answers) < 3:
        await message.answer("❗ Javoblaringiz to‘liq emas. Iltimos, qayta urinib ko‘ring.")
        await state.clear()
        return

    # Kunlar sonini yangilash
    day_count = update_streak(user_id)

    # Ma'lumotlarni bazaga saqlash
    save_report(user_id, username, answers[0], answers[1], answers[2], day_count)

    # Kanalga post yuborish
    post_text = (
        f"📌 {day_count}-kun\n\n"
        f"📆 Sana: {message.date.strftime('%Y-%m-%d')}\n\n"
        f"📣 Today Plan 📝:\n{answers[0]}\n\n"
        f"⚠️ Problems :\n{answers[1]}\n\n"
        f"📈 Today's level of development is 0.1% *{day_count}={0.1 * day_count}%"
        f"⏳ Today I spent {answers[2]} hours studying"
        f"{get_motivational_message(day_count)}"
    )
    await message.bot.send_message(chat_id=channel_id, text=post_text)

    # Inline tugmalar bilan xabar
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistikani ko‘rish", callback_data="stats")],
        [InlineKeyboardButton(text="🔧 Sozlamalarni o‘zgartirish", callback_data="settings")]
    ])
    await message.answer(
        f"🎉 {day_count}-kun hisobotingiz kanalga yuborildi!\n\n{get_motivational_message(day_count)}",
        reply_markup=keyboard
    )
    await state.clear()

@router.callback_query(F.data == "stats")
async def show_stats(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    total_reports, streak = get_report_stats(user_id)
    await callback.message.answer(
        f"📊 Statistikangiz:\n"
        f"📝 Jami hisobotlar: {total_reports} ta\n"
        f"🔥 Ketma-ket kunlar: {streak} kun\n\n"
        f"{get_motivational_message(streak)}"
    )
    await callback.answer()

# @router.callback_query(F.data == "stats")
# async def show_stats(callback: types.CallbackQuery):
#     print(89)
#     user_id = callback.from_user.id
#     total_reports, streak = get_report_stats(user_id)
#     await callback.message.answer(
#         f"📊 Statistikangiz:\n"
#         f"📝 Jami hisobotlar: {total_reports} ta\n"
#         f"🔥 Ketma-ket kunlar: {streak} kun\n\n"
#         f"{get_motivational_message(streak)}"
#     )
#     await callback.answer()

@router.callback_query(F.data == "settings")
async def settings_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Kanal ID yoki username’ni kiriting (masalan, @YourChannel):")
    await state.set_state(SettingsForm.channel_id)
    await callback.answer()