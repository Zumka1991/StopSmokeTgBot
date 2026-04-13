import aiosqlite
from datetime import datetime
from typing import Optional
import os

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/stopsmoke.db")

# Создаём директорию для БД если не существует
os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)


async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                quit_date TIMESTAMP,
                cigarettes_per_day INTEGER DEFAULT 20,
                price_per_pack REAL DEFAULT 150.0,
                cigarettes_in_pack INTEGER DEFAULT 20,
                notifications_enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                achievement_type TEXT,
                achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS relapses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                relapse_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                note TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        await db.commit()


async def add_user(user_id: int, username: str, first_name: str) -> bool:
    """Добавление нового пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
        )
        if await cursor.fetchone():
            return False

        await db.execute(
            """INSERT INTO users (user_id, username, first_name)
               VALUES (?, ?, ?)""",
            (user_id, username, first_name)
        )
        await db.commit()
        return True


async def get_user(user_id: int) -> Optional[dict]:
    """Получение данных пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None


async def set_quit_date(user_id: int, quit_date: datetime) -> bool:
    """Установка даты отказа от курения"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET quit_date = ? WHERE user_id = ?",
            (quit_date.isoformat(), user_id)
        )
        await db.commit()
        return True


async def update_user_settings(
    user_id: int,
    cigarettes_per_day: int = None,
    price_per_pack: float = None,
    cigarettes_in_pack: int = None
) -> bool:
    """Обновление настроек пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        updates = []
        values = []

        if cigarettes_per_day is not None:
            updates.append("cigarettes_per_day = ?")
            values.append(cigarettes_per_day)
        if price_per_pack is not None:
            updates.append("price_per_pack = ?")
            values.append(price_per_pack)
        if cigarettes_in_pack is not None:
            updates.append("cigarettes_in_pack = ?")
            values.append(cigarettes_in_pack)

        if updates:
            values.append(user_id)
            await db.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?",
                values
            )
            await db.commit()
        return True


async def toggle_notifications(user_id: int, enabled: bool) -> bool:
    """Включение/выключение уведомлений"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET notifications_enabled = ? WHERE user_id = ?",
            (1 if enabled else 0, user_id)
        )
        await db.commit()
        return True


async def get_users_with_notifications() -> list:
    """Получение пользователей с включенными уведомлениями"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM users
               WHERE notifications_enabled = 1 AND quit_date IS NOT NULL"""
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def add_relapse(user_id: int, note: str = None) -> bool:
    """Добавление записи о срыве"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO relapses (user_id, note) VALUES (?, ?)",
            (user_id, note)
        )
        await db.commit()
        return True


async def reset_quit_date(user_id: int) -> bool:
    """Сброс даты и начало заново"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET quit_date = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user_id)
        )
        await db.commit()
        return True


async def get_leaderboard(limit: int = 10, offset: int = 0) -> list:
    """Получение рейтинга пользователей"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT user_id, username, first_name, quit_date,
                      cigarettes_per_day, price_per_pack, cigarettes_in_pack
               FROM users
               WHERE quit_date IS NOT NULL
               ORDER BY quit_date ASC
               LIMIT ? OFFSET ?""",
            (limit, offset)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def add_achievement(user_id: int, achievement_type: str) -> bool:
    """Добавление достижения"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """SELECT id FROM achievements
               WHERE user_id = ? AND achievement_type = ?""",
            (user_id, achievement_type)
        )
        if await cursor.fetchone():
            return False

        await db.execute(
            "INSERT INTO achievements (user_id, achievement_type) VALUES (?, ?)",
            (user_id, achievement_type)
        )
        await db.commit()
        return True


async def get_user_achievements(user_id: int) -> list:
    """Получение достижений пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM achievements WHERE user_id = ? ORDER BY achieved_at",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_user_stats(user_id: int) -> dict:
    """Получение статистики срывов пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM relapses WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        relapse_count = row[0] if row else 0

        return {"relapse_count": relapse_count}
