from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import Database, ProductNotFoundError
from handlers.helpers import safe_edit_markup, safe_edit_text
from keyboards import (
    ACTION_DELETE,
    CancelCB,
    ConfirmCB,
    PageCB,
    PickCB,
    confirm_keyboard,
    main_menu,
    products_keyboard,
)
from states import DeleteProduct
from utils import fmt_int, user_display_name

router = Router(name="delete")

EMPTY_TEXT = "Склад пуст, удалять нечего"


async def start_delete(message: Message, state: FSMContext, db: Database) -> None:

    await state.clear()
    products = await db.get_products()
    if not products:
        await message.answer(EMPTY_TEXT, reply_markup=main_menu())
        return
    await state.set_state(DeleteProduct.choose)
    await message.answer(
        "Выберите товар для удаления:",
        reply_markup=products_keyboard(products, ACTION_DELETE),
    )


@router.callback_query(DeleteProduct.choose, PageCB.filter(F.action == ACTION_DELETE))
async def change_page(
    call: CallbackQuery, callback_data: PageCB, state: FSMContext, db: Database
) -> None:
    products = await db.get_products()
    if not products:
        await state.clear()
        await safe_edit_text(call, EMPTY_TEXT)
    else:
        await safe_edit_markup(call, products_keyboard(products, ACTION_DELETE, callback_data.page))
    await call.answer()


@router.callback_query(DeleteProduct.choose, PickCB.filter(F.action == ACTION_DELETE))
async def pick_product(
    call: CallbackQuery, callback_data: PickCB, state: FSMContext, db: Database
) -> None:
    product = await db.get_product(callback_data.product_id)
    if product is None:
        await call.answer("Этот товар уже удалён.", show_alert=True)
        products = await db.get_products()
        if products:
            await safe_edit_markup(call, products_keyboard(products, ACTION_DELETE))
        else:
            await state.clear()
            await safe_edit_text(call, EMPTY_TEXT)
        return

    await state.update_data(product_id=product.id)
    await state.set_state(DeleteProduct.confirm)
    await safe_edit_text(
        call,
        f"Удалить товар «{product.display_name}» (на складе: {fmt_int(product.quantity)} шт.)?\n"
        "Запись будет удалена полностью.",
        reply_markup=confirm_keyboard(),
    )
    await call.answer()


@router.callback_query(DeleteProduct.choose, CancelCB.filter())
async def cancel_choose(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit_text(call, "Удаление отменено.")
    await call.answer()


@router.callback_query(DeleteProduct.confirm, ConfirmCB.filter())
async def confirm(
    call: CallbackQuery, callback_data: ConfirmCB, state: FSMContext, db: Database
) -> None:
    data = await state.get_data()
    product_id = data.get("product_id")
    await state.clear()

    if not callback_data.yes:
        await safe_edit_text(call, "Удаление отменено.")
        await call.answer()
        return

    if product_id is None:
        await safe_edit_text(call, "Не удалось продолжить. Начните заново.")
        await call.answer()
        return

    try:
        product = await db.delete_product(
            product_id, call.from_user.id, user_display_name(call.from_user)
        )
    except ProductNotFoundError:
        await safe_edit_text(call, "Товар уже удалён.")
    else:
        await safe_edit_text(call, f"Товар удалён: {product.display_name}")
    await call.answer()