import os
import aiosqlite
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "barbershop.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                service TEXT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS time_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                UNIQUE(date, time)
            )
        """)
        await db.commit()

async def add_appointment(user_id, username, full_name, phone, service, date, time):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO appointments (user_id, username, full_name, phone, service, date, time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (user_id, username, full_name, phone, service, date, time))
        await db.commit()
        return cursor.lastrowid

async def get_all_appointments():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM appointments ORDER BY date, time")
        return await cursor.fetchall()

async def get_appointments_by_date(date):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM appointments WHERE date = ? ORDER BY time", (date,))
        return await cursor.fetchall()

async def get_appointment_by_id(appt_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM appointments WHERE id = ?", (appt_id,))
        return await cursor.fetchone()

async def update_appointment_status(appt_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE appointments SET status = ? WHERE id = ?", (status, appt_id))
        await db.commit()

async def delete_appointment(appt_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM appointments WHERE id = ?", (appt_id,))
        await db.commit()

async def get_booked_times(date):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT time FROM appointments WHERE date = ? AND status != 'cancelled'
        """, (date,))
        rows = await cursor.fetchall()
        return [r[0] for r in rows]

async def get_user_appointments(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM appointments WHERE user_id = ? ORDER BY date, time
        """, (user_id,))
        return await cursor.fetchall()

# ─── Слоты времени ───────────────────────────────────────────────────────────

async def add_time_slot(date, time):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT INTO time_slots (date, time) VALUES (?, ?)", (date, time))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def delete_time_slot(date, time):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM time_slots WHERE date = ? AND time = ?", (date, time))
        await db.commit()

async def get_slots_by_date(date):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT time FROM time_slots WHERE date = ? ORDER BY time", (date,))
        rows = await cursor.fetchall()
        return [r[0] for r in rows]

async def get_free_slots(date):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT ts.time FROM time_slots ts
            WHERE ts.date = ?
              AND ts.time NOT IN (
                  SELECT time FROM appointments
                  WHERE date = ? AND status != 'cancelled'
              )
            ORDER BY ts.time
        """, (date, date))
        rows = await cursor.fetchall()
        return [r[0] for r in rows]

async def get_dates_with_slots():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT DISTINCT ts.date FROM time_slots ts
            WHERE EXISTS (
                SELECT 1 FROM time_slots ts2
                WHERE ts2.date = ts.date
                  AND ts2.time NOT IN (
                      SELECT time FROM appointments
                      WHERE date = ts2.date AND status != 'cancelled'
                  )
            )
            ORDER BY ts.date
        """)
        rows = await cursor.fetchall()
        return [r[0] for r in rows]

async def delete_slots_by_date(date):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM time_slots WHERE date = ?", (date,))
        await db.commit()
