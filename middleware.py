"""
Middleware для отслеживания активности пользователя.
"""
import logging
import database as db

logger = logging.getLogger(__name__)


class ActivityTrackerMiddleware:
    """Middleware для отслеживания активности пользователя"""
    async def __call__(self, handler, event, data):
        user = data.get('event_from_user')
        if user:
            try:
                await db.update_user_activity(user.id)
            except Exception as e:
                logger.error(f"Ошибка обновления активности: {e}")
        return await handler(event, data)
