from __future__ import annotations

from zoneinfo import ZoneInfo

from aiogram.types import Message

from database import Database
from keyboards import main_menu
from utils import format_operation_line, paginate_text

HISTORY_LIMIT = 20


async def show_history(message: Message, db: Database, tz: ZoneInfo) -> None:

    operations = await db.get_history(HISTORY_LIMIT)
    if not operations:
        await message.answer("История операций пока пуста", reply_markup=main_menu())
        return
    lines = [format_operation_line(op, tz) for op in operations]
    chunks = paginate_text(f"Последние операции (не больше {HISTORY_LIMIT}):\n", lines)
    for i, chunk in enumerate(chunks):
        await message.answer(chunk, reply_markup=main_menu() if i == len(chunks) - 1 else None)