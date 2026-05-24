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

    if hasattr(_lib, "collect_task_indices_for_type_and_date_sorted"):
        _lib.collect_task_indices_for_type_and_date_sorted.argtypes = [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
        ]
        _lib.collect_task_indices_for_type_and_date_sorted.restype = ctypes.c_int

    if hasattr(_lib, "collect_task_indices_for_lesson_sorted"):
        _lib.collect_task_indices_for_lesson_sorted.argtypes = [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
        ]
        _lib.collect_task_indices_for_lesson_sorted.restype = ctypes.c_int

    if hasattr(_lib, "compute_task_ratings"):
        _lib.compute_task_ratings.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
        ]
        _lib.compute_task_ratings.restype = None

    if hasattr(_lib, "collect_urgent_task_indices_sorted"):
        _lib.collect_urgent_task_indices_sorted.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
            ctypes.c_double,
            ctypes.POINTER(ctypes.c_int),
        ]
        _lib.collect_urgent_task_indices_sorted.restype = ctypes.c_int

    if hasattr(_lib, "collect_schedule_lesson_indices_for_day"):
        _lib.collect_schedule_lesson_indices_for_day.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
        ]
        _lib.collect_schedule_lesson_indices_for_day.restype = ctypes.c_int

    if hasattr(_lib, "select_active_template_index"):
        _lib.select_active_template_index.argtypes = [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        _lib.select_active_template_index.restype = ctypes.c_int

    if hasattr(_lib, "derive_schedule_period_end_yyyymmdd"):
        _lib.derive_schedule_period_end_yyyymmdd.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        _lib.derive_schedule_period_end_yyyymmdd.restype = ctypes.c_int

    if hasattr(_lib, "select_next_lesson_index"):
        _lib.select_next_lesson_index.argtypes = [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        _lib.select_next_lesson_index.restype = ctypes.c_int

    if hasattr(_lib, "compute_buffered_alarm_minutes"):
        _lib.compute_buffered_alarm_minutes.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        _lib.compute_buffered_alarm_minutes.restype = ctypes.c_int

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


def collect_task_indices_for_type_and_date_sorted(
    task_types: list[str],
    date_strings: list[str],
    priorities: list[int],
    expected_type: str,
    expected_date: str,
) -> list[int]:
    if (
        not task_types
        or not date_strings
        or not priorities
        or len(task_types) != len(date_strings)
        or len(task_types) != len(priorities)
    ):
        return []

    if _lib is not None and hasattr(_lib, "collect_task_indices_for_type_and_date_sorted"):
        count = len(task_types)
        task_type_values = (ctypes.c_char_p * count)(*[value.encode("utf-8") for value in task_types])
        date_values = (ctypes.c_char_p * count)(*[value.encode("utf-8") for value in date_strings])
        priority_values = (ctypes.c_int * count)(*priorities)
        output_indices = (ctypes.c_int * count)()
        matched_count = _lib.collect_task_indices_for_type_and_date_sorted(
            task_type_values,
            date_values,
            priority_values,
            count,
            expected_type.encode("utf-8"),
            expected_date.encode("utf-8"),
            output_indices,
        )
        return list(output_indices[:matched_count])

    indices = collect_task_indices_for_type_and_date(
        task_types,
        date_strings,
        expected_type,
        expected_date,
    )
    return sorted(indices, key = lambda index: priorities[index], reverse = True)


def collect_task_indices_for_lesson_sorted(
    lesson_ids: list[str],
    priorities: list[int],
    expected_lesson_id: str,
) -> list[int]:
    if not lesson_ids or not priorities or len(lesson_ids) != len(priorities):
        return []

    if _lib is not None and hasattr(_lib, "collect_task_indices_for_lesson_sorted"):
        count = len(lesson_ids)
        lesson_id_values = (ctypes.c_char_p * count)(*[value.encode("utf-8") for value in lesson_ids])
        priority_values = (ctypes.c_int * count)(*priorities)
        output_indices = (ctypes.c_int * count)()
        matched_count = _lib.collect_task_indices_for_lesson_sorted(
            lesson_id_values,
            priority_values,
            count,
            expected_lesson_id.encode("utf-8"),
            output_indices,
        )
        return list(output_indices[:matched_count])

    indices = collect_task_indices_for_lesson(lesson_ids, expected_lesson_id)
    return sorted(indices, key = lambda index: priorities[index], reverse = True)


def compute_task_ratings_for_dates(
    priorities: list[int],
    date_strings: list[str],
    today: datetime.date,
) -> list[float]:
    if not priorities or not date_strings or len(priorities) != len(date_strings):
        return []

    if _lib is not None and hasattr(_lib, "compute_task_ratings"):
        count = len(priorities)
        priority_values = (ctypes.c_int * count)(*priorities)
        date_values = (ctypes.c_char_p * count)(*[value.encode("utf-8") for value in date_strings])
        output_ratings = (ctypes.c_double * count)()
        _lib.compute_task_ratings(
            priority_values,
            date_values,
            count,
            today.day,
            today.month,
            today.year,
            output_ratings,
        )
        return list(output_ratings)

    result: list[float] = []
    for priority, date_string in zip(priorities, date_strings):
        try:
            task_date = datetime.datetime.strptime(date_string, "%d.%m.%Y").date()
        except ValueError:
            result.append(0.0)
            continue

        days_until = (task_date - today).days
        result.append(compute_rating_value(priority, days_until))
    return result


def collect_urgent_task_indices_sorted(
    ratings: list[float],
    threshold: float,
) -> list[int]:
    if not ratings:
        return []

    if _lib is not None and hasattr(_lib, "collect_urgent_task_indices_sorted"):
        count = len(ratings)
        rating_values = (ctypes.c_double * count)(*ratings)
        output_indices = (ctypes.c_int * count)()
        matched_count = _lib.collect_urgent_task_indices_sorted(
            rating_values,
            count,
            float(threshold),
            output_indices,
        )
        return list(output_indices[:matched_count])

    return sorted(
        [index for index, rating in enumerate(ratings) if rating >= threshold],
        key = ratings.__getitem__,
        reverse = True,
    )


def collect_schedule_lesson_indices_for_day(
    lesson_days: list[int],
    lesson_start_minutes: list[int],
    expected_day: int,
) -> list[int]:
    if not lesson_days or not lesson_start_minutes or len(lesson_days) != len(lesson_start_minutes):
        return []

    if _lib is not None and hasattr(_lib, "collect_schedule_lesson_indices_for_day"):
        count = len(lesson_days)
        day_values = (ctypes.c_int * count)(*lesson_days)
        start_minute_values = (ctypes.c_int * count)(*lesson_start_minutes)
        output_indices = (ctypes.c_int * count)()
        matched_count = _lib.collect_schedule_lesson_indices_for_day(
            day_values,
            start_minute_values,
            count,
            expected_day,
            output_indices,
        )
        return list(output_indices[:matched_count])

    indices = [index for index, day in enumerate(lesson_days) if day == expected_day]
    return sorted(indices, key = lesson_start_minutes.__getitem__)


def select_active_template_index(
    template_starts: list[str],
    target_date: datetime.date,
) -> int:
    if not template_starts:
        return -1

    if _lib is not None and hasattr(_lib, "select_active_template_index"):
        count = len(template_starts)
        start_values = (ctypes.c_char_p * count)(*[value.encode("utf-8") for value in template_starts])
        return int(
            _lib.select_active_template_index(
                start_values,
                count,
                target_date.day,
                target_date.month,
                target_date.year,
            )
        )

    parsed: list[tuple[int, datetime.date]] = []
    for index, value in enumerate(template_starts):
        try:
            parsed.append((index, datetime.datetime.strptime(value, "%d.%m.%Y").date()))
        except ValueError:
            continue

    if not parsed:
        return -1

    candidates = [item for item in parsed if item[1] <= target_date]
    if candidates:
        return max(candidates, key = lambda item: item[1])[0]
    return min(parsed, key = lambda item: item[1])[0]


def derive_schedule_period_end_date(
    start_date: datetime.date,
    next_start: datetime.date | None,
) -> datetime.date:
    if _lib is not None and hasattr(_lib, "derive_schedule_period_end_yyyymmdd"):
        encoded = int(
            _lib.derive_schedule_period_end_yyyymmdd(
                start_date.day,
                start_date.month,
                start_date.year,
                int(next_start is not None),
                next_start.day if next_start else 0,
                next_start.month if next_start else 0,
                next_start.year if next_start else 0,
            )
        )
        year = encoded // 10000
        month = (encoded // 100) % 100
        day = encoded % 100
        return datetime.date(year, month, day)

    if start_date.month >= 8:
        result = datetime.date(start_date.year + 1, 1, 31)
    else:
        result = datetime.date(start_date.year, 6, 30)
    if next_start is not None:
        result = min(result, next_start - datetime.timedelta(days = 1))
    return result


def select_next_lesson_index(
    date_strings: list[str],
    start_minutes: list[int],
    now: datetime.datetime,
) -> int:
    if not date_strings or not start_minutes or len(date_strings) != len(start_minutes):
        return -1

    now_minutes = now.hour * 60 + now.minute
    if _lib is not None and hasattr(_lib, "select_next_lesson_index"):
        count = len(date_strings)
        date_values = (ctypes.c_char_p * count)(*[value.encode("utf-8") for value in date_strings])
        minute_values = (ctypes.c_int * count)(*start_minutes)
        return int(
            _lib.select_next_lesson_index(
                date_values,
                minute_values,
                count,
                now.day,
                now.month,
                now.year,
                now_minutes,
            )
        )

    best_index = -1
    best_date: datetime.date | None = None
    best_start = 0
    for index, (date_string, start_minute) in enumerate(zip(date_strings, start_minutes)):
        try:
            lesson_date = datetime.datetime.strptime(date_string, "%d.%m.%Y").date()
        except ValueError:
            continue
        if lesson_date < now.date():
            continue
        if lesson_date == now.date() and start_minute <= now_minutes:
            continue
        if best_index < 0 or lesson_date < best_date or (lesson_date == best_date and start_minute < best_start):
            best_index = index
            best_date = lesson_date
            best_start = start_minute
    return best_index


def compute_buffered_alarm_minutes(
    lesson_start_minutes: int,
    prep_minutes: int,
    travel_minutes: int,
    buffer_minutes: int,
) -> int:
    if _lib is not None and hasattr(_lib, "compute_buffered_alarm_minutes"):
        return int(
            _lib.compute_buffered_alarm_minutes(
                lesson_start_minutes,
                prep_minutes,
                travel_minutes,
                buffer_minutes,
            )
        )

    alarm_minutes = lesson_start_minutes - prep_minutes - travel_minutes - buffer_minutes
    while alarm_minutes < 0:
        alarm_minutes += 24 * 60
    return alarm_minutes % (24 * 60)


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
