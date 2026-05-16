import ctypes
import datetime
import os

# Загружаем нативную C++ DLL для функций подсчета
dll_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "native",
    "alarm_lib.dll"
)

lib = ctypes.CDLL(dll_path)

# Определяем сигнатуры функций DLL
lib.make_alarm.argtypes = [
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int
]

lib.make_alarm.restype = ctypes.c_int

lib.is_valid_time.argtypes = [
    ctypes.c_int,
    ctypes.c_int,
]

lib.is_valid_time.restype = ctypes.c_int

lib.time_to_minutes.argtypes = [
    ctypes.c_int,
    ctypes.c_int,
]

lib.time_to_minutes.restype = ctypes.c_int

lib.normalize_duration_minutes.argtypes = [
    ctypes.c_int,
]

lib.normalize_duration_minutes.restype = ctypes.c_int

lib.is_week_even.argtypes = [
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
]

lib.is_week_even.restype = ctypes.c_int



def is_valid_time(hour: int, minute: int) -> bool:
    """Проверяет корректность времени (часы 0-23, минуты 0-59)."""
    return bool(lib.is_valid_time(hour, minute))


def time_to_minutes(time_text: str) -> int:
    """Преобразует строку времени (ЧЧ:ММ) в минуты с начала дня.
    Возвращает -1 если время некорректно."""
    try:
        hour_text, minute_text = time_text.strip().split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except (AttributeError, ValueError):
        return -1

    return lib.time_to_minutes(hour, minute)


def normalize_duration_minutes(minutes: int) -> int:
    """Нормализует длительность: возвращает 0 если отрицательно, иначе исходное значение."""
    return lib.normalize_duration_minutes(minutes)


def is_week_even(date: datetime.date, semester_start: str, first_week_even: bool) -> bool:
    """Определяет четность недели в семестре.
    
    Args:
        date: Дата для проверки
        semester_start: Дата начала семестра в формате "ДД.ММ.ГГГГ"
        first_week_even: True если первая неделя четная
    
    Returns:
        True если неделя четная, False если нечетная
    """
    start = datetime.datetime.strptime(semester_start, "%d.%m.%Y").date()
    return bool(
        lib.is_week_even(
            date.day,
            date.month,
            date.year,
            start.day,
            start.month,
            start.year,
            int(first_week_even),
        )
    )


def make_alarm(hour_start, min_start, time_to_get_ready, time_to_way):
    """Рассчитывает время пробуждения перед парой.
    
    Args:
        hour_start: Час начала пары
        min_start: Минута начала пары
        time_to_get_ready: Время на сборы (минуты)
        time_to_way: Время на дорогу (минуты)
    
    Returns:
        Время пробуждения в формате "ЧЧ:ММ"
    """
    total_minutes = lib.make_alarm(
        hour_start,
        min_start,
        time_to_get_ready,
        time_to_way
    )

    hour = total_minutes // 60
    minute = total_minutes % 60

    return f"{hour:02}:{minute:02}"
