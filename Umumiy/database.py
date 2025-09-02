import sqlite3
from datetime import datetime, timedelta


def init_db():
    conn=sqlite3.connect("daily_reports.db")
    cursor=conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
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
    conn.commit()
    conn.close()