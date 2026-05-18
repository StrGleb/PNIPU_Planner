import ctypes
import datetime
from pathlib import Path

# Загружаем нативную C++ DLL для функций подсчета
dll_path = Path(__file__).parent / ".." / "native" / "bin" / "alarm_lib.dll"
dll_path = dll_path.resolve()

# Определение типов данных
lib = ctypes.CDLL(dll_path)
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

def time_to_minutes(time_text: str) -> int:
    """
    Преобразует строку времени (ЧЧ:ММ) в минуты с начала дня.
    Возвращает -1 если время некорректно.
    """
    try:
        hour_text, minute_text = time_text.strip().split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except (AttributeError, ValueError):
        return -1

    return lib.time_to_minutes(hour, minute)

def is_week_even(
    date: datetime.date,
    semester_start: str,
    first_week_even: bool,
) -> bool:
    """
    Определяет четность недели в семестре.
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


# Тест функций
if "__main__" == __name__:
    ...