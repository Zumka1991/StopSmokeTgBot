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
                rating_visible INTEGER DEFAULT 1,
                rating_last_confirmed TIMESTAMP,
                last_active TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Миграция: добавляем новые поля если их нет
        try:
            await db.execute(
                "ALTER TABLE users ADD COLUMN rating_visible INTEGER DEFAULT 1"
            )
        except Exception: pass
        try:
            await db.execute(
                "ALTER TABLE users ADD COLUMN rating_last_confirmed TIMESTAMP"
            )
        except Exception: pass
        try:
            await db.execute(
                "ALTER TABLE users ADD COLUMN last_active TIMESTAMP"
            )
        except Exception: pass
        try:
            await db.execute(
                "ALTER TABLE users ADD COLUMN referred_by INTEGER"
            )
        except Exception: pass
        try:
            await db.execute(
                "ALTER TABLE users ADD COLUMN ai_questions_today INTEGER DEFAULT 0"
            )
        except Exception: pass
        try:
            await db.execute(
                "ALTER TABLE users ADD COLUMN last_ai_question_date TEXT"
            )
        except Exception: pass

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

        await db.execute("""
            CREATE TABLE IF NOT EXISTS diary_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                entry_date DATE,
                entry_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS ai_chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS global_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        await db.commit()


async def add_user(user_id: int, username: str, first_name: str, referred_by: int = None) -> bool:
    """Добавление нового пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
        )
        if await cursor.fetchone():
            return False

        await db.execute(
            """INSERT INTO users (user_id, username, first_name, referred_by)
               VALUES (?, ?, ?, ?)""",
            (user_id, username, first_name, referred_by)
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


async def toggle_rating_visibility(user_id: int, visible: bool) -> bool:
    """Включение/выключение видимости в рейтинге"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET rating_visible = ?, rating_last_confirmed = ? WHERE user_id = ?",
            (1 if visible else 0, datetime.now().isoformat(), user_id)
        )
        await db.commit()
        return True


async def confirm_rating_participation(user_id: int) -> bool:
    """Подтверждение участия в рейтинге"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET rating_visible = 1, rating_last_confirmed = ?, last_active = ? WHERE user_id = ?",
            (datetime.now().isoformat(), datetime.now().isoformat(), user_id)
        )
        await db.commit()
        return True


async def update_user_activity(user_id: int) -> bool:
    """Обновление времени последней активности пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET last_active = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user_id)
        )
        await db.commit()
        return True


async def get_users_for_rating_check() -> list:
    """Получение пользователей для проверки подтверждения рейтинга"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM users
               WHERE quit_date IS NOT NULL AND rating_visible = 1
               ORDER BY last_active ASC"""
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


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
               WHERE quit_date IS NOT NULL AND rating_visible = 1
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


# ===== ДНЕВНИК =====

async def add_diary_entry(user_id: int, entry_date: str, entry_text: str) -> bool:
    """Добавление записи в дневник"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO diary_entries (user_id, entry_date, entry_text) VALUES (?, ?, ?)",
            (user_id, entry_date, entry_text)
        )
        await db.commit()
        return True


async def get_diary_dates(user_id: int) -> list:
    """Получение уникальных дат с записями"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """SELECT DISTINCT entry_date FROM diary_entries
               WHERE user_id = ?
               ORDER BY entry_date DESC""",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def get_diary_entries_by_date(user_id: int, entry_date: str) -> list:
    """Получение записей за определённую дату"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM diary_entries
               WHERE user_id = ? AND entry_date = ?
               ORDER BY created_at ASC""",
            (user_id, entry_date)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def delete_diary_entries_by_date(user_id: int, entry_date: str) -> int:
    """Удаление всех записей за определённую дату"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM diary_entries WHERE user_id = ? AND entry_date = ?",
            (user_id, entry_date)
        )
        await db.commit()
        return cursor.rowcount


async def make_all_users_visible() -> int:
    """Сделать всех пользователей с quit_date видимыми в рейтинге"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "UPDATE users SET rating_visible = 1 WHERE quit_date IS NOT NULL"
        )
        await db.commit()
        return cursor.rowcount


async def get_referral_count(user_id: int) -> int:
    """Получение количества приглашенных друзей"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def check_ai_limit(user_id: int) -> tuple[bool, int]:
    """Проверка дневного лимита вопросов ИИ (возвращает (можно_задать, осталось))"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT ai_questions_today, last_ai_question_date FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return False, 0

        today = datetime.now().date().isoformat()
        last_date = row["last_ai_question_date"]
        count = row["ai_questions_today"] or 0

        if last_date != today:
            # Новый день, сбрасываем счетчик
            await db.execute(
                "UPDATE users SET ai_questions_today = 0, last_ai_question_date = ? WHERE user_id = ?",
                (today, user_id)
            )
            await db.commit()
            return True, 10

        return count < 10, max(0, 10 - count)


async def increment_ai_usage(user_id: int):
    """Увеличение счетчика использования ИИ"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET ai_questions_today = ai_questions_today + 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def add_ai_chat_message(user_id: int, role: str, content: str):
    """Добавление сообщения в историю чата с ИИ"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO ai_chat_history (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content)
        )
        await db.commit()


async def get_ai_chat_history(user_id: int, limit: int = 10) -> list:
    """Получение истории чата с ИИ"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT role, content FROM ai_chat_history
               WHERE user_id = ?
               ORDER BY created_at ASC
               LIMIT ?""",
            (user_id, limit)
        )
        rows = await cursor.fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in rows]



async def clear_ai_chat_history(user_id: int):
    """Очистка истории чата с ИИ"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "DELETE FROM ai_chat_history WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def is_broadcast_sent(key: str) -> bool:
    """Проверка, была ли отправлена рассылка"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT value FROM global_settings WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        return row is not None and row[0] == "sent"


async def set_broadcast_sent(key: str):
    """Отметка о выполнении рассылки"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO global_settings (key, value) VALUES (?, ?)",
            (key, "sent")
        )
        await db.commit()


async def get_all_user_ids() -> list[int]:
    """Получение всех ID пользователей"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
