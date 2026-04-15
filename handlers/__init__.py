"""
Пакет хендлеров бота.
Импорт всех модулей с хендлерами — регистрация происходит автоматически через @dp decorators.
"""
from . import commands
from . import callbacks
from . import fsm_handlers


def register_handlers(dp):
    """Регистрация всех хендлеров (фактически уже зарегистрированы при импорте)"""
    pass
