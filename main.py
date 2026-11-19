import asyncio
import logging
import os

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from config import settings
from database.db import async_session, create_tables
from handlers import add_listing, my_listings, search, start
from middlewares.db import DatabaseMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_bot():
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DatabaseMiddleware(async_session))

    dp.include_router(start.router)
    dp.include_router(add_listing.router)
    dp.include_router(search.router)
    dp.include_router(my_listings.router)

    # Agar WEBAPP_URL bo'lsa, start handlerga WebApp tugmasi qo'shamiz
    if settings.WEBAPP_URL:
        from aiogram.filters import CommandStart
        from aiogram.types import Message

        @dp.message(CommandStart())
        async def cmd_start_webapp(message: Message):
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="🏠 Ilovani ochish",
                    web_app=WebAppInfo(url=settings.WEBAPP_URL),
                )
            ]])
            await message.answer(
                "🏠 <b>Uy Bor</b> — Maklerсiz uy toping!\n\nIlovani ochish uchun tugmani bosing:",
                reply_markup=kb,
            )

    await create_tables()
    logger.info("Bot ishga tushdi...")
    await dp.start_polling(bot, skip_updates=True)


def run_api():
    from api.app import app
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


async def main():
    await create_tables()

    # Bot va API ni parallel ishlatish
    bot_task = asyncio.create_task(run_bot())

    loop = asyncio.get_event_loop()
    from api.app import app
    port = int(os.getenv("PORT", 8000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    api_task = asyncio.create_task(server.serve())

    await asyncio.gather(bot_task, api_task)


if __name__ == "__main__":
    asyncio.run(main())
