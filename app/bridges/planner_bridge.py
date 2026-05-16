import ctypes
import datetime
import os

dll_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "native",
    "alarm_lib.dll"
)

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


def is_valid_time(hour: int, minute: int) -> bool:
    return bool(lib.is_valid_time(hour, minute))


def time_to_minutes(time_text: str) -> int:
    try:
        hour_text, minute_text = time_text.strip().split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except (AttributeError, ValueError):
        return -1

    return lib.time_to_minutes(hour, minute)


def normalize_duration_minutes(minutes: int) -> int:
    return lib.normalize_duration_minutes(minutes)


def is_week_even(
    date: datetime.date,
    semester_start: str,
    first_week_even: bool,
) -> bool:
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


def make_alarm(
    hour_start,
    min_start,
    time_to_get_ready,
    time_to_way
):

    total_minutes = lib.make_alarm(
        hour_start,
        min_start,
        time_to_get_ready,
        time_to_way
    )

    hour = total_minutes // 60
    minute = total_minutes % 60

    return f"{hour:02}:{minute:02}"
