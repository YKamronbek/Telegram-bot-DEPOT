from aiogram.fsm.state import State, StatesGroup


class AddProduct(StatesGroup):
    name = State()
    quantity = State()


class RemoveProduct(StatesGroup):
    choose = State()
    quantity = State()


class FindProduct(StatesGroup):
    query = State()


class DeleteProduct(StatesGroup):
    choose = State()
    confirm = State()