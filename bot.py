import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database import init_db
from handlers import client, admin
from scheduler import reminder_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

async def main():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(admin.router)
    dp.include_router(client.router)

    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Бот запущен!")

    # Запускаем планировщик напоминаний параллельно с ботом
    await asyncio.gather(
        dp.start_polling(bot),
        reminder_loop(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
