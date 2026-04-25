"""
Планировщик напоминаний — запускается вместе с ботом.
За день до записи отправляет напоминание клиенту и админу.
"""
import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot
from config import ADMIN_ID
from database import get_appointments_by_date

logger = logging.getLogger(__name__)

async def send_reminders(bot: Bot):
    """Отправить напоминания о записях на завтра."""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    appointments = await get_appointments_by_date(tomorrow)

    active = [a for a in appointments if a["status"] != "cancelled"]
    if not active:
        return

    logger.info(f"Отправляю напоминания о {len(active)} записях на {tomorrow}")

    for appt in active:
        # Клиенту
        try:
            await bot.send_message(
                appt["user_id"],
                f"⏰ <b>Напоминание о записи!</b>\n\n"
                f"Завтра <b>{appt['date']}</b> в <b>{appt['time']}</b>\n"
                f"✂️ {appt['service']}\n\n"
                f"📍 Ждём вас по адресу: <b>ул. Астраханская 19</b>\n\n"
                f"Если не сможете прийти — пожалуйста, отмените запись заранее.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить напоминание клиенту {appt['user_id']}: {e}")

    # Админу — сводка
    lines = [f"📅 <b>Записи на завтра ({tomorrow}):</b>\n"]
    for appt in active:
        lines.append(f"🕐 {appt['time']} — {appt['full_name']}, {appt['phone']}\n    ✂️ {appt['service']}")
    try:
        await bot.send_message(ADMIN_ID, "\n".join(lines), parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Не удалось отправить сводку админу: {e}")


async def reminder_loop(bot: Bot):
    """Каждый час проверяем — если сейчас 10:00, отправляем напоминания."""
    logger.info("Планировщик напоминаний запущен")
    while True:
        now = datetime.now()
        # Отправляем напоминания каждый день в 10:00
        if now.hour == 10 and now.minute == 0:
            await send_reminders(bot)
            # Ждём 61 минуту чтобы не отправить дважды в одну минуту
            await asyncio.sleep(61 * 60)
        else:
            # Проверяем каждую минуту
            await asyncio.sleep(60)
