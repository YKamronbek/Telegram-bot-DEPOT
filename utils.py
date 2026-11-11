from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from aiogram.types import User

    from database import Operation, Product

MIN_NAME_LEN = 2
MAX_NAME_LEN = 100
MAX_QUANTITY = 1_000_000
TELEGRAM_TEXT_LIMIT = 4000


_INVISIBLE_RE = re.compile("[\u200b\u2060\ufeff\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class ValidationError(ValueError):
    """Пользователь ввёл неверные данные. Текст — причина, её можно показать как есть."""


# ----------------------------------------------------------------------------
# Названия товаров
# ----------------------------------------------------------------------------
def clean_display_name(name: str) -> str:

    return " ".join(_INVISIBLE_RE.sub("", name).split())


def normalize_name(name: str) -> str:

    return clean_display_name(name).casefold()


def sort_key(name: str) -> str:

    return normalize_name(name).replace("ё", "е")


def parse_name(raw: str) -> str:

    name = clean_display_name(raw)
    if not name:
        raise ValidationError("Название не может быть пустым.")
    if len(name) < MIN_NAME_LEN:
        raise ValidationError(f"Название слишком короткое: минимум {MIN_NAME_LEN} символа.")
    if len(name) > MAX_NAME_LEN:
        raise ValidationError(
            f"Название слишком длинное: максимум {MAX_NAME_LEN} символов (у вас {len(name)})."
        )
    if name.startswith("/"):
        raise ValidationError(
            "Название не может начинаться с «/» — так выглядят команды. "
            "Чтобы выйти из диалога, нажмите /cancel."
        )
    return name


def parse_search_query(raw: str) -> str:

    query = clean_display_name(raw)
    if not query:
        raise ValidationError("Запрос не может быть пустым.")
    if len(query) > MAX_NAME_LEN:
        raise ValidationError(f"Запрос слишком длинный: максимум {MAX_NAME_LEN} символов.")
    return query


def parse_quantity(raw: str) -> int:

    text = raw.strip()
    if not re.fullmatch(r"[0-9]+", text):
        raise ValidationError("Введите целое число больше 0.")
    digits = text.lstrip("0")
    if not digits:
        raise ValidationError("Введите целое число больше 0.")
    if len(digits) > len(str(MAX_QUANTITY)):
        raise ValidationError(f"Слишком большое число: максимум {fmt_int(MAX_QUANTITY)}.")
    value = int(digits)
    if value > MAX_QUANTITY:
        raise ValidationError(f"Слишком большое число: максимум {fmt_int(MAX_QUANTITY)}.")
    return value


# ----------------------------------------------------------------------------
# Форматирование
# ----------------------------------------------------------------------------
def fmt_int(value: int) -> str:
    return f"{value:,}".replace(",", "\u00a0")


def truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def user_display_name(user: User) -> str:
    name = clean_display_name(user.full_name or "") or (user.username or "") or str(user.id)
    return truncate(name, MAX_NAME_LEN)


def format_product_line(index: int, product: Product) -> str:
    return f"{index}. {product.display_name} — {fmt_int(product.quantity)} шт."


def format_operation_line(op: Operation, tz: ZoneInfo) -> str:

    when = op.created_at.astimezone(tz).strftime("%d.%m.%Y %H:%M")
    if op.delta > 0:
        delta = f"+{fmt_int(op.delta)}"
    elif op.delta < 0:
        delta = f"−{fmt_int(-op.delta)}"  # настоящий минус «−», как в ТЗ
    else:
        delta = "0"
    suffix = " (товар удалён)" if op.action == "delete" else ""
    return f"{when} — {op.user_name}: {delta} {op.product_name}{suffix}"


def paginate_text(
    header: str,
    lines: Iterable[str],
    footer: str = "",
    limit: int = TELEGRAM_TEXT_LIMIT,
) -> list[str]:


    chunks: list[str] = []
    buf = header
    for line in lines:
        line = truncate(line, limit)
        candidate = f"{buf}\n{line}" if buf else line
        if len(candidate) > limit and buf:
            chunks.append(buf)
            buf = line
        else:
            buf = candidate
    if footer:
        candidate = f"{buf}\n\n{footer}" if buf else footer
        if len(candidate) > limit and buf:
            chunks.append(buf)
            buf = footer
        else:
            buf = candidate
    if buf:
        chunks.append(buf)
    return chunks