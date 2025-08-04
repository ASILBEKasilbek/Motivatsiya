import sqlite3
from datetime import datetime, timedelta

def init_db():
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    
    # Foydalanuvchi hisobotlari
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            user_id INTEGER,
            username TEXT,
            date TEXT,
            tasks TEXT,
            issues TEXT,
            plans TEXT,
            day_count INTEGER
        )
    """)
    
    # Foydalanuvchi sozlamalari
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            channel_id TEXT,
            reminder_time TEXT DEFAULT '20:00',
            custom_questions TEXT,
            streak_start_date TEXT,
            current_streak INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()

def save_report(user_id, username, tasks, issues, plans, day_count):
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        "INSERT INTO reports (user_id, username, date, tasks, issues, plans, day_count) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, username, date, tasks, issues, plans, day_count)
    )
    conn.commit()
    conn.close()

def save_user_settings(user_id, channel_id=None, reminder_time=None, custom_questions=None):
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO user_settings (user_id, channel_id, reminder_time, custom_questions) VALUES (?, ?, ?, ?)",
        (user_id, channel_id, reminder_time, custom_questions)
    )
    conn.commit()
    conn.close()

def get_user_settings(user_id):
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id, reminder_time, custom_questions, streak_start_date, current_streak FROM user_settings WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result if result else (None, "20:00", None, None, 0)

def update_streak(user_id):
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    cursor.execute("SELECT date FROM reports WHERE user_id = ? ORDER BY date DESC LIMIT 1", (user_id,))
    last_report = cursor.fetchone()
    
    today = datetime.now().date()
    streak = 1
    streak_start_date = today.strftime("%Y-%m-%d")
    
    if last_report:
        last_date = datetime.strptime(last_report[0], "%Y-%m-%d").date()
        if last_date == today:
            cursor.execute("SELECT current_streak FROM user_settings WHERE user_id = ?", (user_id,))
            streak = cursor.fetchone()[0]
        elif last_date == today - timedelta(days=1):
            cursor.execute("SELECT current_streak, streak_start_date FROM user_settings WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            streak = result[0] + 1 if result else 1
            streak_start_date = result[1] if result else today.strftime("%Y-%m-%d")
        else:
            streak = 1
            streak_start_date = today.strftime("%Y-%m-%d")
    
    cursor.execute(
        "INSERT OR REPLACE INTO user_settings (user_id, current_streak, streak_start_date) VALUES (?, ?, ?)",
        (user_id, streak, streak_start_date)
    )
    conn.commit()
    conn.close()
    return streak

def get_report_stats(user_id):
    conn = sqlite3.connect("daily_reports.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM reports WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]

    cursor.execute("SELECT current_streak FROM user_settings WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    streak = row[0] if row else 0

    conn.close()
    return count, streak
