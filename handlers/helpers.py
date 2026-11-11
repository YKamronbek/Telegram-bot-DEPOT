from __future__ import annotations

import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

logger = logging.getLogger(__name__)


async def safe_edit_text(
    call: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup | None = None
) -> None:

    if not isinstance(call.message, Message):
        return
    try:
        await call.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            logger.warning("Не удалось изменить сообщение: %s", exc)


async def safe_edit_markup(call: CallbackQuery, reply_markup: InlineKeyboardMarkup) -> None:
    if not isinstance(call.message, Message):
        return
    try:
        await call.message.edit_reply_markup(reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            logger.warning("Не удалось изменить кнопки: %s", exc)