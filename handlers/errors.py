from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)

router = Router(name="errors")

ERROR_TEXT = "Что-то пошло не так, попробуйте ещё раз"


@router.errors()
async def on_error(event: ErrorEvent) -> bool:
    logger.error("Ошибка при обработке обновления: %r", event.exception, exc_info=event.exception)
    update = event.update
    try:
        if update.message is not None:
            await update.message.answer(ERROR_TEXT)
        elif update.callback_query is not None:
            await update.callback_query.answer(ERROR_TEXT, show_alert=True)
    except Exception:  # noqa: BLE001 — если и ответить не вышло, просто логируем
        logger.exception("Не удалось сообщить пользователю об ошибке")
    return True  # ошибка обработана, бот продолжает работать