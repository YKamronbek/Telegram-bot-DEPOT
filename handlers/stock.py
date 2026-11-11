from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import Database
from keyboards import main_menu
from states import FindProduct
from utils import fmt_int

router = Router(name="stock")


async def show_stock(message: Message, db: Database) -> None:

    products = await db.get_products()
    if not products:
        await message.answer("Склад пуст.", reply_markup=main_menu())
        return

    text = "<b>📦 Остатки на складе:</b>\n\n"
    for p in products:
        text += f"• <b>{p.display_name}</b> — {fmt_int(p.quantity)} шт.\n"

    await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")


async def start_find(message: Message, state: FSMContext, db: Database, query: str | None = None) -> None:

    await state.clear()

    if query:
        query_str = query.strip()
        products = await db.search_products(query_str)
        if not products:
            await message.answer(f"По запросу «{query_str}» ничего не найдено.", reply_markup=main_menu())
            return
        text = f"<b>Результаты поиска по запросу «{query_str}»:</b>\n\n"
        for p in products:
            text += f"• <b>{p.display_name}</b> — {fmt_int(p.quantity)} шт.\n"
        await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")
        return

    products = await db.get_products()
    if not products:
        await message.answer("Склад пуст, искать нечего.", reply_markup=main_menu())
        return

    await state.set_state(FindProduct.query)
    await message.answer(
        "Введите название или часть названия товара для поиска:\n\nОтмена: /cancel"
    )


@router.message(FindProduct.query, F.text)
async def process_find_query(message: Message, state: FSMContext, db: Database) -> None:
    query = message.text.strip()
    if not query:
        await message.answer("Введите корректный текст для поиска:")
        return

    products = await db.search_products(query)
    await state.clear()

    if not products:
        await message.answer(
            f"По запросу «{query}» ничего не найдено.", reply_markup=main_menu()
        )
        return

    text = f"<b>Результаты поиска по запросу «{query}»:</b>\n\n"
    for p in products:
        text += f"• <b>{p.display_name}</b> — {fmt_int(p.quantity)} шт.\n"

    await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")