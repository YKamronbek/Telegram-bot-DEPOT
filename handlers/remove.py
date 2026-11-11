from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import Database, NotEnoughStockError, ProductNotFoundError
from handlers.helpers import safe_edit_markup, safe_edit_text
from keyboards import ACTION_REMOVE, CancelCB, PageCB, PickCB, main_menu, products_keyboard
from states import RemoveProduct
from utils import ValidationError, fmt_int, parse_quantity, user_display_name

router = Router(name="remove")

EMPTY_TEXT = "Склад пуст, списывать нечего"
ASK_QUANTITY = "Введите количество для списания\n\nОтмена: /cancel"


async def start_remove(message: Message, state: FSMContext, db: Database) -> None:

    await state.clear()
    products = [p for p in await db.get_products() if p.quantity > 0]  # с нулём списывать нечего
    if not products:
        await message.answer(EMPTY_TEXT, reply_markup=main_menu())
        return
    await state.set_state(RemoveProduct.choose)
    await message.answer(
        "Выберите товар для списания:",
        reply_markup=products_keyboard(products, ACTION_REMOVE),
    )


@router.callback_query(RemoveProduct.choose, PageCB.filter(F.action == ACTION_REMOVE))
async def change_page(
    call: CallbackQuery, callback_data: PageCB, state: FSMContext, db: Database
) -> None:
    products = [p for p in await db.get_products() if p.quantity > 0]
    if not products:
        await state.clear()
        await safe_edit_text(call, EMPTY_TEXT)
    else:
        await safe_edit_markup(call, products_keyboard(products, ACTION_REMOVE, callback_data.page))
    await call.answer()


@router.callback_query(RemoveProduct.choose, PickCB.filter(F.action == ACTION_REMOVE))
async def pick_product(
    call: CallbackQuery, callback_data: PickCB, state: FSMContext, db: Database
) -> None:
    product = await db.get_product(callback_data.product_id)
    if product is None or product.quantity <= 0:
        # Пока пользователь выбирал, товар удалили или остаток обнулили — обновляем список
        await call.answer("Этот товар уже удалён или закончился.", show_alert=True)
        products = [p for p in await db.get_products() if p.quantity > 0]
        if products:
            await safe_edit_markup(call, products_keyboard(products, ACTION_REMOVE))
        else:
            await state.clear()
            await safe_edit_text(call, EMPTY_TEXT)
        return

    await state.update_data(product_id=product.id)
    await state.set_state(RemoveProduct.quantity)
    await safe_edit_text(
        call, f"Выбрано: {product.display_name} (на складе: {fmt_int(product.quantity)} шт.)"
    )
    if isinstance(call.message, Message):
        await call.message.answer(ASK_QUANTITY)
    await call.answer()


@router.callback_query(RemoveProduct.choose, CancelCB.filter())
async def cancel_choose(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit_text(call, "Списание отменено.")
    await call.answer()


@router.message(RemoveProduct.quantity, F.text)
async def process_quantity(message: Message, state: FSMContext, db: Database) -> None:
    try:
        quantity = parse_quantity(message.text)
    except ValidationError as exc:
        await message.answer(f"{exc}\n\n{ASK_QUANTITY}")
        return

    data = await state.get_data()
    product_id = data.get("product_id")
    if product_id is None or message.from_user is None:
        await state.clear()
        await message.answer("Не удалось продолжить. Начните заново.", reply_markup=main_menu())
        return

    try:
        result = await db.remove_quantity(
            product_id, quantity, message.from_user.id, user_display_name(message.from_user)
        )
    except NotEnoughStockError as exc:
        # Диалог продолжается: можно ввести другое число
        await message.answer(f"На складе только {fmt_int(exc.available)} шт.\n\n{ASK_QUANTITY}")
        return
    except ProductNotFoundError:
        await state.clear()
        await message.answer(
            "Товар не найден — возможно, его только что удалили.", reply_markup=main_menu()
        )
        return

    await state.clear()
    await message.answer(
        f"{result.display_name}\n"
        f"Списано {fmt_int(result.removed)} шт. Осталось: {fmt_int(result.left)} шт.",
        reply_markup=main_menu(),
    )