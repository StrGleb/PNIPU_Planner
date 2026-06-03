import datetime
from random import choice


def greeting_choose() -> str:
    """
    Выводит рандомное приветствие на главном экране:
    23:00–05:59 — Доброй ночи
    06:00–10:59 — Доброе утро
    11:00–16:59 — Добрый день
    17:00–22:59 — Добрый вечер

    ПЕРЕПИСАТЬ НА C++
    """
    greetings = ["Приветствую", "Добро пожаловать", "time"]
    greeting = choice(greetings)

    if greeting == "time":
        hour = datetime.datetime.now().hour
        if hour == 23 or 0 <= hour <= 5:
            greeting = "Доброй ночи"
        elif 6 <= hour <= 10:
            greeting = "Доброе утро"
        elif 11 <= hour <= 16:
            greeting = "Добрый день"
        else:
            greeting = "Добрый вечер"

    return greeting
