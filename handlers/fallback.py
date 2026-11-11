from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message

from keyboards import main_menu
from states import AddProduct, DeleteProduct, FindProduct, RemoveProduct

router = Router(name="fallback")

# Шаги, где ждём текст
_TEXT_STATES = (
    AddProduct.name,
    AddProduct.quantity,
    RemoveProduct.quantity,
    FindProduct.query,
)
# Шаги, где ждём нажатие кнопки под сообщением
_BUTTON_STATES = (
    RemoveProduct.choose,
    DeleteProduct.choose,
    DeleteProduct.confirm,
)


@router.message(StateFilter(*_TEXT_STATES), ~F.text)
async def need_text(message: Message) -> None:
    """Стикер, фото, голосовое и т. п. посреди диалога."""
    await message.answer("Пожалуйста, отправьте текст")


@router.message(StateFilter(*_BUTTON_STATES))
async def need_button(message: Message) -> None:
    await message.answer(
        "Выберите вариант кнопкой под сообщением выше или нажмите /cancel, чтобы отменить."
    )


@router.message()
async def unknown_message(message: Message) -> None:
    await message.answer(
        "Не понял вас. Выберите действие в меню внизу или нажмите /help.",
        reply_markup=main_menu(),
    )


@router.callback_query()
async def stale_button(call: CallbackQuery) -> None:

    await call.answer(
        "Эта кнопка уже неактуальна. Начните действие заново через меню.", show_alert=True
    )