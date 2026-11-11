from __future__ import annotations

from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import Database
from handlers import add, delete, history, remove, stock
from keyboards import (
    BTN_ADD,
    BTN_DELETE,
    BTN_FIND,
    BTN_HISTORY,
    BTN_REMOVE,
    BTN_STOCK,
    main_menu,
)

router = Router(name="menu")

WELCOME_TEXT = (
    "Здравствуйте! Это бот «Склад» — учёт товаров и их количества.\n\n"
    "Выберите действие в меню внизу. Подсказка по командам — /help."
)

HELP_TEXT = (
    "Бот «Склад» — учёт товаров и количества.\n\n"
    "Кнопки меню:\n"
    "• Добавить товар — добавить вид товара и количество. "
    "Если такой товар уже есть, количество прибавится.\n"
    "• Списать товар — уменьшить остаток.\n"
    "• Остатки — весь список по алфавиту (команда /list).\n"
    "• Найти товар — поиск по части названия (команда /find шины).\n"
    "• Удалить товар — убрать позицию полностью.\n"
    "• История операций — последние 20 действий (команда /history).\n\n"
    "/cancel — прервать текущий диалог и вернуться в меню."
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(HELP_TEXT, reply_markup=main_menu())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    was_active = await state.get_state() is not None
    await state.clear()
    await message.answer(
        "Действие отменено." if was_active else "Нечего отменять.", reply_markup=main_menu()
    )


@router.message(F.text == BTN_ADD)
async def btn_add(message: Message, state: FSMContext) -> None:
    await state.clear()
    await add.start_add(message, state)


@router.message(F.text == BTN_REMOVE)
async def btn_remove(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    await remove.start_remove(message, state, db)


@router.message(F.text == BTN_STOCK)
@router.message(Command("list"))
async def btn_stock(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    await stock.show_stock(message, db)


@router.message(F.text == BTN_FIND)
async def btn_find(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    await stock.start_find(message, state, db)


@router.message(Command("find"))
async def cmd_find(
    message: Message, command: CommandObject, state: FSMContext, db: Database
) -> None:
    await state.clear()

    if command.args:
        query = command.args.strip()
        products = await db.search_products(query)
        if not products:
            await message.answer(f"По запросу «{query}» ничего не найдено.", reply_markup=main_menu())
            return
        text = f"Результаты поиска по запросу «{query}»:\n\n"
        for p in products:
            text += f"• <b>{p.display_name}</b> — {p.quantity} шт.\n"
        await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")
    else:
        await stock.start_find(message, state, db)


@router.message(F.text == BTN_DELETE)
async def btn_delete(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    await delete.start_delete(message, state, db)


@router.message(F.text == BTN_HISTORY)
@router.message(Command("history"))
async def btn_history(message: Message, state: FSMContext, db: Database, tz: ZoneInfo) -> None:
    await state.clear()
    await history.show_history(message, db, tz)