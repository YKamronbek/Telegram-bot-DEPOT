from __future__ import annotations

import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNetworkError, TelegramUnauthorizedError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import BASE_DIR, Config, ConfigError, load_config
from database import Database
from handlers import get_routers
from middlewares import AccessMiddleware

logger = logging.getLogger("sklad_bot")

BOT_COMMANDS = [
    BotCommand(command="start", description="Главное меню"),
    BotCommand(command="list", description="Остатки на складе"),
    BotCommand(command="find", description="Найти товар"),
    BotCommand(command="history", description="История операций"),
    BotCommand(command="cancel", description="Отменить текущее действие"),
    BotCommand(command="help", description="Справка"),
]


def setup_logging(level: str) -> None:

    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    file = RotatingFileHandler(
        log_dir / "bot.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [console, file]


def build_dispatcher(config: Config, db: Database) -> Dispatcher:

    dp = Dispatcher(storage=MemoryStorage())
    dp["db"] = db  # попадает в обработчики как аргумент db
    dp["tz"] = config.timezone  # ...и tz

    access = AccessMiddleware(config.allowed_users)
    dp.message.outer_middleware(access)
    dp.callback_query.outer_middleware(access)

    for router in get_routers():
        dp.include_router(router)
    return dp


async def run() -> None:
    config = load_config()
    setup_logging(config.log_level)

    db = Database(config.db_path)
    await db.init()

    bot = Bot(token=config.bot_token)
    dp = build_dispatcher(config, db)

    try:
        me = await bot.get_me()
        await bot.delete_webhook(drop_pending_updates=False)  # вебхук мешает polling
        await bot.set_my_commands(BOT_COMMANDS)
        logger.info("Бот запущен: @%s (разрешено пользователей: %d)", me.username, len(config.allowed_users))
        await dp.start_polling(bot)  # allowed_updates определяются по обработчикам
    finally:
        await bot.session.close()
        logger.info("Бот остановлен")


def main() -> None:
    try:
        asyncio.run(run())
    except ConfigError as exc:
        print(f"Ошибка настроек: {exc}", file=sys.stderr)
        sys.exit(1)
    except TelegramUnauthorizedError:
        print("Telegram не принял BOT_TOKEN. Проверьте токен в файле .env.", file=sys.stderr)
        sys.exit(1)
    except TelegramNetworkError as exc:
        print(f"Нет связи с Telegram: {exc}. Проверьте интернет и повторите запуск.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()