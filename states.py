"""
FSM состояния бота.
"""
from aiogram.fsm.state import State, StatesGroup


class DiaryState(StatesGroup):
    waiting_for_text = State()


class AIState(StatesGroup):
    waiting_for_question = State()
