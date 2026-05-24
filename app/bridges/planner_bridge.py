import ctypes
import datetime
import os
import sys
from pathlib import Path


_NATIVE_BIN_DIR = (Path(__file__).resolve().parent / ".." / "native" / "bin").resolve()

if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
    os.add_dll_directory(str(_NATIVE_BIN_DIR))


def _candidate_library_names() -> list[str]:
    if sys.platform == "win32":
        return [
            "libplanner_core.dll",
            "planner_core.dll",
            "alarm_lib.dll",
        ]

    return [
        "libplanner_core.so",
        "planner_core.so",
        "libalarm_lib.so",
        "alarm_lib.so",
    ]


def _load_native_library():
    for filename in _candidate_library_names():
        library_path = (_NATIVE_BIN_DIR / filename).resolve()
        if not library_path.exists():
            continue

        try:
            return ctypes.CDLL(str(library_path))
        except OSError:
            continue

    return None


_lib = _load_native_library()
lib = _lib

if _lib is not None:
    if hasattr(_lib, "make_alarm"):
        _lib.make_alarm.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        _lib.make_alarm.restype = ctypes.c_int

    if hasattr(_lib, "is_valid_time"):
        _lib.is_valid_time.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
        ]
        _lib.is_valid_time.restype = ctypes.c_int

    if hasattr(_lib, "time_to_minutes"):
        _lib.time_to_minutes.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
        ]
        _lib.time_to_minutes.restype = ctypes.c_int

    if hasattr(_lib, "normalize_duration_minutes"):
        _lib.normalize_duration_minutes.argtypes = [ctypes.c_int]
        _lib.normalize_duration_minutes.restype = ctypes.c_int

    if hasattr(_lib, "is_week_even"):
        _lib.is_week_even.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        _lib.is_week_even.restype = ctypes.c_int

    if hasattr(_lib, "compute_rating_value"):
        _lib.compute_rating_value.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
        ]
        _lib.compute_rating_value.restype = ctypes.c_float

    if hasattr(_lib, "is_valid_date_text"):
        _lib.is_valid_date_text.argtypes = [ctypes.c_char_p]
        _lib.is_valid_date_text.restype = ctypes.c_int

    if hasattr(_lib, "normalize_priority"):
        _lib.normalize_priority.argtypes = [ctypes.c_int]
        _lib.normalize_priority.restype = ctypes.c_int

    if hasattr(_lib, "theme_mode_code"):
        _lib.theme_mode_code.argtypes = [ctypes.c_char_p]
        _lib.theme_mode_code.restype = ctypes.c_int

    if hasattr(_lib, "sort_indices_by_int_desc"):
        _lib.sort_indices_by_int_desc.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
        ]
        _lib.sort_indices_by_int_desc.restype = None

    if hasattr(_lib, "sort_indices_by_double_desc"):
        _lib.sort_indices_by_double_desc.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
        ]
        _lib.sort_indices_by_double_desc.restype = None

    if hasattr(_lib, "collect_task_indices_for_type_and_date"):
        _lib.collect_task_indices_for_type_and_date.argtypes = [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
        ]
        _lib.collect_task_indices_for_type_and_date.restype = ctypes.c_int

    if hasattr(_lib, "collect_task_indices_for_lesson"):
        _lib.collect_task_indices_for_lesson.argtypes = [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
        ]
        _lib.collect_task_indices_for_lesson.restype = ctypes.c_int

    if hasattr(_lib, "parse_schedule_xlsx"):
        _lib.parse_schedule_xlsx.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
        ]
        _lib.parse_schedule_xlsx.restype = ctypes.c_int

    if hasattr(_lib, "copy_last_error_message"):
        _lib.copy_last_error_message.argtypes = [
            ctypes.c_char_p,
            ctypes.c_int,
        ]
        _lib.copy_last_error_message.restype = ctypes.c_int


def has_native_core() -> bool:
    return _lib is not None


def has_native_schedule_parser() -> bool:
    return _lib is not None and hasattr(_lib, "parse_schedule_xlsx")


def _parse_time_text(time_text: str):
    try:
        hour_text, minute_text = time_text.strip().split(":", 1)
        return int(hour_text), int(minute_text)
    except (AttributeError, ValueError):
        return None


def _get_native_error_message() -> str:
    if _lib is None or not hasattr(_lib, "copy_last_error_message"):
        return ""

    buffer = ctypes.create_string_buffer(2048)
    size = _lib.copy_last_error_message(buffer, len(buffer))
    if size <= 0:
        return ""

    return buffer.value.decode("utf-8", errors = "replace").strip()


def make_alarm(hour: int, minute: int, prep: int, travel: int) -> int:
    if _lib is not None and hasattr(_lib, "make_alarm"):
        return _lib.make_alarm(hour, minute, prep, travel)

    alarm_minutes = hour * 60 + minute - prep - travel
    while alarm_minutes < 0:
        alarm_minutes += 24 * 60
    return alarm_minutes


def is_valid_time(hour: int, minute: int) -> bool:
    if _lib is not None and hasattr(_lib, "is_valid_time"):
        return bool(_lib.is_valid_time(hour, minute))
    return 0 <= hour <= 23 and 0 <= minute <= 59


def time_to_minutes(time_text: str) -> int:
    parsed = _parse_time_text(time_text)
    if parsed is None:
        return -1

    hour, minute = parsed
    if _lib is not None and hasattr(_lib, "time_to_minutes"):
        return _lib.time_to_minutes(hour, minute)

    if not is_valid_time(hour, minute):
        return -1
    return hour * 60 + minute


def normalize_duration_minutes(minutes: int) -> int:
    if _lib is not None and hasattr(_lib, "normalize_duration_minutes"):
        return _lib.normalize_duration_minutes(minutes)
    return max(0, int(minutes))


def is_week_even(
    date: datetime.date,
    semester_start: str,
    first_week_even: bool,
) -> bool:
    try:
        start = datetime.datetime.strptime(semester_start, "%d.%m.%Y").date()
    except Exception:
        return date.isocalendar()[1] % 2 == 0

    if _lib is not None and hasattr(_lib, "is_week_even"):
        return bool(
            _lib.is_week_even(
                date.day,
                date.month,
                date.year,
                start.day,
                start.month,
                start.year,
                int(first_week_even),
            )
        )

    weeks = (date - start).days // 7
    return (weeks % 2 == 0) == first_week_even


def compute_rating_value(priority: int, days_until: int) -> float:
    if _lib is not None and hasattr(_lib, "compute_rating_value"):
        return float(_lib.compute_rating_value(priority, days_until))

    priority_score = priority * 30.0
    if days_until < 0:
        urgency_score = 150.0
    elif days_until == 0:
        urgency_score = 120.0
    elif days_until <= 14:
        urgency_score = (1.0 - days_until / 14.0) * 100.0
    else:
        urgency_score = 0.0

    return priority_score + urgency_score


def is_valid_date_text(value: str) -> bool:
    if not isinstance(value, str):
        return False

    if _lib is not None and hasattr(_lib, "is_valid_date_text"):
        return bool(_lib.is_valid_date_text(value.encode("utf-8")))

    try:
        datetime.datetime.strptime(value, "%d.%m.%Y")
        return True
    except ValueError:
        return False


def normalize_priority(priority: int) -> int:
    if _lib is not None and hasattr(_lib, "normalize_priority"):
        return _lib.normalize_priority(priority)
    return max(0, min(3, int(priority)))


def normalize_theme(theme: str) -> str:
    if _lib is not None and hasattr(_lib, "theme_mode_code"):
        theme_code = _lib.theme_mode_code(str(theme).encode("utf-8"))
    else:
        normalized = str(theme).strip().lower()
        if normalized == "light":
            theme_code = 1
        elif normalized == "dark":
            theme_code = 2
        else:
            theme_code = 0

    return {
        0: "system",
        1: "light",
        2: "dark",
    }.get(theme_code, "system")


def sort_indices_by_int_desc(values: list[int]) -> list[int]:
    if not values:
        return []

    if _lib is not None and hasattr(_lib, "sort_indices_by_int_desc"):
        count = len(values)
        input_values = (ctypes.c_int * count)(*values)
        output_indices = (ctypes.c_int * count)()
        _lib.sort_indices_by_int_desc(input_values, count, output_indices)
        return list(output_indices)

    return sorted(range(len(values)), key = values.__getitem__, reverse = True)


def sort_indices_by_double_desc(values: list[float]) -> list[int]:
    if not values:
        return []

    if _lib is not None and hasattr(_lib, "sort_indices_by_double_desc"):
        count = len(values)
        input_values = (ctypes.c_double * count)(*values)
        output_indices = (ctypes.c_int * count)()
        _lib.sort_indices_by_double_desc(input_values, count, output_indices)
        return list(output_indices)

    return sorted(range(len(values)), key = values.__getitem__, reverse = True)


def collect_task_indices_for_type_and_date(
    task_types: list[str],
    date_strings: list[str],
    expected_type: str,
    expected_date: str,
) -> list[int]:
    if not task_types or not date_strings or len(task_types) != len(date_strings):
        return []

    if _lib is not None and hasattr(_lib, "collect_task_indices_for_type_and_date"):
        count = len(task_types)
        task_type_values = (ctypes.c_char_p * count)(
            *[value.encode("utf-8") for value in task_types]
        )
        date_values = (ctypes.c_char_p * count)(
            *[value.encode("utf-8") for value in date_strings]
        )
        output_indices = (ctypes.c_int * count)()
        matched_count = _lib.collect_task_indices_for_type_and_date(
            task_type_values,
            date_values,
            count,
            expected_type.encode("utf-8"),
            expected_date.encode("utf-8"),
            output_indices,
        )
        return list(output_indices[:matched_count])

    return [
        index
        for index, (task_type, date_string) in enumerate(zip(task_types, date_strings))
        if task_type == expected_type and date_string == expected_date
    ]


def collect_task_indices_for_lesson(
    lesson_ids: list[str],
    expected_lesson_id: str,
) -> list[int]:
    if not lesson_ids:
        return []

    if _lib is not None and hasattr(_lib, "collect_task_indices_for_lesson"):
        count = len(lesson_ids)
        lesson_id_values = (ctypes.c_char_p * count)(
            *[value.encode("utf-8") for value in lesson_ids]
        )
        output_indices = (ctypes.c_int * count)()
        matched_count = _lib.collect_task_indices_for_lesson(
            lesson_id_values,
            count,
            expected_lesson_id.encode("utf-8"),
            output_indices,
        )
        return list(output_indices[:matched_count])

    return [
        index
        for index, lesson_id in enumerate(lesson_ids)
        if lesson_id == expected_lesson_id
    ]


def parse_schedule_xlsx_file(xlsx_path: str | Path, output_json_path: str | Path) -> None:
    if not has_native_schedule_parser():
        raise RuntimeError(
            "Native XLSX parser is unavailable. Build planner_core for the current platform first."
        )

    xlsx_path_text = str(Path(xlsx_path))
    output_json_text = str(Path(output_json_path))
    ok = _lib.parse_schedule_xlsx(
        xlsx_path_text.encode("utf-8"),
        output_json_text.encode("utf-8"),
    )
    if ok:
        return

    message = _get_native_error_message() or "Unknown native XLSX parser error."
    raise RuntimeError(message)
