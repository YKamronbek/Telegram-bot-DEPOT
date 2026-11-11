from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from utils import clean_display_name, normalize_name, sort_key

logger = logging.getLogger(__name__)

BUSY_TIMEOUT_SECONDS = 15

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL UNIQUE,                 -- нормализованное название (для сравнения)
    display_name TEXT    NOT NULL,                        -- как ввёл пользователь
    quantity     INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    updated_at   TEXT    NOT NULL                         -- UTC, ISO 8601
);

CREATE TABLE IF NOT EXISTS operations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT    NOT NULL,
    user_id      INTEGER NOT NULL,
    user_name    TEXT    NOT NULL,
    delta        INTEGER NOT NULL,                        -- +20, -3; при удалении — минус остаток
    action       TEXT    NOT NULL CHECK (action IN ('add', 'remove', 'delete')),
    created_at   TEXT    NOT NULL                         -- UTC, ISO 8601
);
"""


@dataclass(frozen=True, slots=True)
class Product:
    id: int
    name: str
    display_name: str
    quantity: int
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Operation:
    id: int
    product_name: str
    user_id: int
    user_name: str
    delta: int
    action: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AddResult:
    display_name: str
    added: int
    total: int
    created: bool


@dataclass(frozen=True, slots=True)
class RemoveResult:
    display_name: str
    removed: int
    left: int


class ProductNotFoundError(Exception):
    """Товара нет в базе (например, его только что удалил другой пользователь)."""


class NotEnoughStockError(Exception):
    """Списывают больше, чем есть на складе."""

    def __init__(self, available: int) -> None:
        super().__init__(f"На складе только {available} шт.")
        self.available = available


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _product(row: aiosqlite.Row) -> Product:
    return Product(
        id=row["id"],
        name=row["name"],
        display_name=row["display_name"],
        quantity=row["quantity"],
        updated_at=_parse_dt(row["updated_at"]),
    )


def _operation(row: aiosqlite.Row) -> Operation:
    return Operation(
        id=row["id"],
        product_name=row["product_name"],
        user_id=row["user_id"],
        user_name=row["user_name"],
        delta=row["delta"],
        action=row["action"],
        created_at=_parse_dt(row["created_at"]),
    )


class Database:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    async def init(self) -> None:
        """Создаёт папку, файл базы и таблицы (если их ещё нет)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        async with self._connect() as conn:
            await conn.execute("PRAGMA journal_mode = WAL")
            await conn.executescript(SCHEMA)
        logger.info("База данных готова: %s", self._path)


    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[aiosqlite.Connection]:
        # isolation_level=None — транзакциями управляем вручную (BEGIN/COMMIT)
        async with aiosqlite.connect(
            self._path, timeout=BUSY_TIMEOUT_SECONDS, isolation_level=None
        ) as conn:
            conn.row_factory = aiosqlite.Row
            yield conn

    @asynccontextmanager
    async def _transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        async with self._connect() as conn:
            await conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                with suppress(Exception):
                    await conn.execute("ROLLBACK")
                raise
            else:
                await conn.execute("COMMIT")

    @staticmethod
    async def _log_operation(
        conn: aiosqlite.Connection,
        product_name: str,
        user_id: int,
        user_name: str,
        delta: int,
        action: str,
        when: str,
    ) -> None:
        await conn.execute(
            "INSERT INTO operations (product_name, user_id, user_name, delta, action, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (product_name, user_id, user_name, delta, action, when),
        )


    async def add_product(
        self, name: str, quantity: int, user_id: int, user_name: str
    ) -> AddResult:
        """Добавляет товар. Если такой уже есть (без учёта регистра и пробелов) — прибавляет количество."""
        display_name = clean_display_name(name)
        key = normalize_name(name)
        now = _now()
        async with self._transaction() as conn:
            cur = await conn.execute(
                "SELECT id, display_name, quantity FROM products WHERE name = ?", (key,)
            )
            row = await cur.fetchone()
            if row is None:
                await conn.execute(
                    "INSERT INTO products (name, display_name, quantity, updated_at) "
                    "VALUES (?, ?, ?, ?)",
                    (key, display_name, quantity, now),
                )
                shown, total, created = display_name, quantity, True
            else:
                total = row["quantity"] + quantity
                await conn.execute(
                    "UPDATE products SET quantity = ?, updated_at = ? WHERE id = ?",
                    (total, now, row["id"]),
                )
                shown, created = row["display_name"], False
            await self._log_operation(conn, shown, user_id, user_name, quantity, "add", now)
        return AddResult(display_name=shown, added=quantity, total=total, created=created)

    async def remove_quantity(
        self, product_id: int, quantity: int, user_id: int, user_name: str
    ) -> RemoveResult:

        now = _now()
        async with self._transaction() as conn:
            cur = await conn.execute(
                "SELECT display_name, quantity FROM products WHERE id = ?", (product_id,)
            )
            row = await cur.fetchone()
            if row is None:
                raise ProductNotFoundError(product_id)
            if quantity > row["quantity"]:
                raise NotEnoughStockError(row["quantity"])
            left = row["quantity"] - quantity
            await conn.execute(
                "UPDATE products SET quantity = ?, updated_at = ? WHERE id = ?",
                (left, now, product_id),
            )
            await self._log_operation(
                conn, row["display_name"], user_id, user_name, -quantity, "remove", now
            )
        return RemoveResult(display_name=row["display_name"], removed=quantity, left=left)

    async def delete_product(self, product_id: int, user_id: int, user_name: str) -> Product:

        now = _now()
        async with self._transaction() as conn:
            cur = await conn.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            row = await cur.fetchone()
            if row is None:
                raise ProductNotFoundError(product_id)
            product = _product(row)
            await conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
            await self._log_operation(
                conn, product.display_name, user_id, user_name, -product.quantity, "delete", now
            )
        return product


    async def get_product(self, product_id: int) -> Product | None:
        async with self._connect() as conn:
            cur = await conn.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            row = await cur.fetchone()
        return _product(row) if row else None

    async def get_products(self) -> list[Product]:

        async with self._connect() as conn:
            cur = await conn.execute("SELECT * FROM products")
            rows = await cur.fetchall()
        return sorted((_product(r) for r in rows), key=lambda p: sort_key(p.name))

    async def search_products(self, query: str) -> list[Product]:

        key = normalize_name(query)
        if not key:
            return []
        # instr() вместо LIKE: символы % и _ в запросе не считаются шаблонами
        async with self._connect() as conn:
            cur = await conn.execute("SELECT * FROM products WHERE instr(name, ?) > 0", (key,))
            rows = await cur.fetchall()
        return sorted((_product(r) for r in rows), key=lambda p: sort_key(p.name))

    async def get_history(self, limit: int = 20) -> list[Operation]:

        async with self._connect() as conn:
            cur = await conn.execute("SELECT * FROM operations ORDER BY id DESC LIMIT ?", (limit,))
            rows = await cur.fetchall()
        return [_operation(r) for r in reversed(rows)]