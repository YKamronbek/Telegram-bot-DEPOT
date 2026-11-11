from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import Database
from keyboards import main_menu
from states import AddProduct
from utils import ValidationError, fmt_int, parse_name, parse_quantity, user_display_name

router = Router(name="add")

ASK_NAME = "Введите вид (название) товара.\n\nОтмена: /cancel"
ASK_QUANTITY = "Введите количество"


async def start_add(message: Message, state: FSMContext) -> None:

    await state.clear()
    await state.set_state(AddProduct.name)
    await message.answer(ASK_NAME)


@router.message(AddProduct.name, F.text)
async def process_name(message: Message, state: FSMContext) -> None:
    try:
        name = parse_name(message.text)
    except ValidationError as exc:
        await message.answer(f"{exc}\n\n{ASK_NAME}")
        return
    await state.update_data(name=name)
    await state.set_state(AddProduct.quantity)
    await message.answer(ASK_QUANTITY)


@router.message(AddProduct.quantity, F.text)
async def process_quantity(message: Message, state: FSMContext, db: Database) -> None:
    try:
        quantity = parse_quantity(message.text)
    except ValidationError as exc:
        await message.answer(f"{exc}\n\n{ASK_QUANTITY}")
        return

    data = await state.get_data()
    name = data.get("name")
    if not name or message.from_user is None:  # состояние потеряно — начинаем заново
        await state.clear()
        await message.answer("Не удалось продолжить. Начните заново.", reply_markup=main_menu())
        return

    result = await db.add_product(
        name, quantity, message.from_user.id, user_display_name(message.from_user)
    )
    await state.clear()
    await message.answer(
        f"Добавлено: {result.display_name} — {fmt_int(quantity)} шт. "
        f"Всего на складе: {fmt_int(result.total)} шт.",
        reply_markup=main_menu(),
    )