# states.py
from aiogram.fsm.state import State, StatesGroup

class ReportForm(StatesGroup):
    tasks = State()
    issues = State()
    plans = State()

class SettingsForm(StatesGroup):
    channel_id = State()
    reminder_time = State()
    custom_questions = State()