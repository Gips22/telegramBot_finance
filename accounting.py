"""Работа с расходами - их добавление, удаление, статистика."""
import datetime
import re
from typing import List, NamedTuple, Optional

import pytz

import db
import exceptions
from categories import Categories

class Message(NamedTuple):
    """Структура распаршенного сообщения о расходе"""
    amount: int
    category_text: str

class Expense(NamedTuple):
    """Структура добавленного в БД новго расхода"""
    id: Optional[int]
    amount: int
    category_name: str

# TODO: разобрать регулярку
def _parse_message(raw_message: str) -> Message:
    """Парсит пришедшее в бот сообщение"""
    # regexp_result = re.match(r"([\d ]+) (.*)", raw_message)
    # if not regexp_result or not regexp_result.group(0) \
    #         or not regexp_result.group(1) or not regexp_result.group(2):
    #     raise exceptions.NotCorrectMessage(
    #         "Не могу понять сообщение. Напишите сообщение в формате, "
    #         "например:\n1500 метро")
    message_part1, message_part2 = raw_message.split()
    if str(message_part1).isdigit() and str(message_part2).isalpha():
        amount = message_part1
        category_text = message_part2
    elif str(message_part2).isdigit() and str(message_part1).isalpha():
        amount = message_part2
        category_text = message_part1
    else:
        raise exceptions.NotCorrectMessage("Некорректное сообщение. Попробуйте ввести в другом формате")
    return Message(amount=amount, category_text=category_text)


def _get_now_formatted() -> str:
    """Возвращает сегодняшнюю дату строкой"""
    return _get_now_datetime().strftime("%Y-%m-%d %H:%M:%S")


def _get_now_datetime() -> datetime.datetime:
    """Возвращает сегодняшний datetime с учётом времненной зоны Мск."""
    tz = pytz.timezone("Europe/Moscow")
    now = datetime.datetime.now(tz)
    return now

def add_expense(raw_message: str) -> Expense:
    """Добавляет и сохраняет в БД новый расход. Принимает на вход сообщение из бота."""
    parsed_message = _parse_message(raw_message)
    category = Categories().get_category(parsed_message.category_text)

    inserted_row_id = db.insert("expense", {
        "amount": parsed_message.amount,
        "created": _get_now_formatted(),
        "category_codename": category.codename,
        "raw_text": raw_message
    })
    return Expense(id=None, amount=parsed_message.amount, category_name=category.name)


def _get_budget_limit():
    """Возвращает дневной лимит трат для основных базовых трат"""
    return db.fetchall("budget", ["daily_limit"])[0]["daily_limit"]  # TODO: тут понять индекс [0]["daily_limit"]


def get_today_statistics() -> str:
    """Возвращает статистику за сегодня"""
    cursor = db.get_cursor()
    cursor.execute("select sum(amount)"
                   "from expense where date(created)=date('now', 'localtime')")
    result = cursor.fetchone()
    if not result[0]:
        return "За сегодня расходов нет"
    all_today_expenses = result[0]
    cursor.execute("select sum(amount) "
                   "from expense where date(created)=date('now', 'localtime') "
                   "and category_codename in (select codename "
                   "from category where is_base_expense=true)")
    result = cursor.fetchone()
    base_today_expenses = result[0] if result[0] else 0
    return (f"Расходы сегодня: \n"
            f"всего - {all_today_expenses} руб. \n"
            f"базовые — {base_today_expenses} руб. из {_get_budget_limit()} руб.\n\n"
            f"За текущий месяц: /month")

def get_month_statistics() -> str:
    """Возвращает строкой статистику расходов за текущий месяц"""
    now = _get_now_datetime()
    first_day_of_month = f'{now.year:04d}-{now.month:02d}-01'  # TODO: посмотреть как считается данная формула

