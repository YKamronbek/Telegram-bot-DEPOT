from __future__ import annotations

from aiogram import Router


def get_routers() -> list[Router]:

    from handlers import add, delete, errors, fallback, menu, remove, stock

    return [
        menu.router,
        add.router,
        remove.router,
        delete.router,
        stock.router,
        fallback.router,
        errors.router,
    ]