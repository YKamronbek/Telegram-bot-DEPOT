from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Формат токена BotFather: 123456789:AAH... (числа, двоеточие, буквенно-цифровая часть)
_TOKEN_RE = re.compile(r"^\d{5,}:[A-Za-z0-9_-]{20,}$")

class ConfigError(Exception):
    """Ошибка в настройках: текст исключения понятен человеку."""

@dataclass(frozen=True, slots=True)
class Config:
    bot_token: str
    allowed_users: frozenset[int]
    db_path: Path
    timezone: ZoneInfo
    log_level: str

def _parse_allowed_users(raw: str) -> frozenset[int]:
    ids: set[int] = set()
    for part in re.split(r"[,\s;]+", raw.strip()):
        if not part:
            continue
        if not re.fullmatch(r"\d+", part):
            raise ConfigError(
                f"В ALLOWED_USERS найдено «{part}» — это не Telegram ID. "
                "Ожидается список чисел через запятую, например: 123456,789012"
            )
        ids.add(int(part))
    if not ids:
        raise ConfigError(
            "ALLOWED_USERS пуст: бот никого не пустит. "
            "Укажите Telegram ID через запятую, например: ALLOWED_USERS=123456,789012"
        )
    return frozenset(ids)

def load_config(env_file: Path | None = None) -> Config:

    load_dotenv(env_file or BASE_DIR / ".env", encoding="utf-8-sig")

    # Сюда передается именно имя ключа из файла .env, а не сам токен!
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise ConfigError(
            "BOT_TOKEN не задан. Создайте файл .env и впишите токен от @BotFather."
        )
    if not _TOKEN_RE.match(token):
        raise ConfigError(

        )

    allowed_users = _parse_allowed_users(os.getenv("ALLOWED_USERS", ""))
    db_path = Path(os.getenv("DB_PATH", "data/sklad.db").strip() or "data/sklad.db")
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path

    tz_name = os.getenv("TIMEZONE", "UTC").strip() or "UTC"
    try:
        timezone = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ConfigError(
            f"Неизвестный часовой пояс TIMEZONE={tz_name!r}. "
            "Примеры: UTC, Europe/Moscow, Asia/Tashkent"
        ) from exc

    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ConfigError(
            f"Неизвестный LOG_LEVEL={log_level!r}. Допустимо: DEBUG, INFO, WARNING, ERROR, CRITICAL"
        )

    return Config(
        bot_token=token,
        allowed_users=allowed_users,
        db_path=db_path,
        timezone=timezone,
        log_level=log_level,
    )