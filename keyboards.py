from __future__ import annotations

from collections.abc import Sequence
from math import ceil

from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import Product
from utils import fmt_int, truncate


BTN_ADD = "Добавить товар"
BTN_REMOVE = "Списать товар"
BTN_STOCK = "Остатки"
BTN_FIND = "Найти товар"
BTN_DELETE = "Удалить товар"
BTN_HISTORY = "История операций"

PAGE_SIZE = 8


ACTION_REMOVE = "rm"
ACTION_DELETE = "del"


class PickCB(CallbackData, prefix="pick"):


    action: str
    product_id: int


class PageCB(CallbackData, prefix="page"):


    action: str
    page: int


class CancelCB(CallbackData, prefix="cancel"):
    """Кнопка «Отмена» под списком товаров."""


class ConfirmCB(CallbackData, prefix="confirm"):


    yes: bool


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ADD), KeyboardButton(text=BTN_REMOVE)],
            [KeyboardButton(text=BTN_STOCK), KeyboardButton(text=BTN_FIND)],
            [KeyboardButton(text=BTN_DELETE), KeyboardButton(text=BTN_HISTORY)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


MENU_BUTTONS = frozenset({BTN_ADD, BTN_REMOVE, BTN_STOCK, BTN_FIND, BTN_DELETE, BTN_HISTORY})


def products_keyboard(products: Sequence[Product], action: str, page: int = 0) -> InlineKeyboardMarkup:

    total_pages = max(1, ceil(len(products) / PAGE_SIZE))
    page = min(max(page, 0), total_pages - 1)
    chunk = products[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

    builder = InlineKeyboardBuilder()
    for product in chunk:
        label = truncate(f"{product.display_name} — {fmt_int(product.quantity)} шт.", 60)
        builder.row(
            InlineKeyboardButton(
                text=label, callback_data=PickCB(action=action, product_id=product.id).pack()
            )
        )

    if total_pages > 1:
        nav: list[InlineKeyboardButton] = []
        if page > 0:
            nav.append(
                InlineKeyboardButton(
                    text="◀ Назад", callback_data=PageCB(action=action, page=page - 1).pack()
                )
            )
        nav.append(
            InlineKeyboardButton(
                text=f"{page + 1}/{total_pages}",
                callback_data=PageCB(action=action, page=page).pack(),
            )
        )
        if page < total_pages - 1:
            nav.append(
                InlineKeyboardButton(
                    text="Вперёд ▶", callback_data=PageCB(action=action, page=page + 1).pack()
                )
            )
        builder.row(*nav)

    builder.row(InlineKeyboardButton(text="Отмена", callback_data=CancelCB().pack()))
    return builder.as_markup()


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да, удалить", callback_data=ConfirmCB(yes=True).pack()),
                InlineKeyboardButton(text="Отмена", callback_data=ConfirmCB(yes=False).pack()),
            ]
        ]
    )