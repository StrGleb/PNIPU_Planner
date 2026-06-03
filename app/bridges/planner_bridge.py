import ctypes
import datetime
import os
import platform
import sys
from pathlib import Path

_NATIVE_LIB_ROOT = (Path(__file__).resolve().parent / ".." / "native" / "jniLibs").resolve()


def _candidate_library_names() -> list[str]:
    if sys.platform == "win32":
        return [
            "libplanner_core.dll",
            "planner_core.dll",
        ]

    return [
        "libplanner_core.so",
        "planner_core.so",
    ]


def _android_abi_hints() -> list[str]:
    machine = platform.machine().lower()
    ordered_hints: list[str] = []

    if "aarch64" in machine or "arm64" in machine:
        ordered_hints.append("arm64-v8a")
    elif "arm" in machine:
        ordered_hints.append("armeabi-v7a")
    elif "x86_64" in machine or "amd64" in machine:
        ordered_hints.append("x86_64")
    elif "86" in machine:
        ordered_hints.append("x86")

    ordered_hints.extend(["arm64-v8a", "armeabi-v7a", "x86_64", "x86"])
    return list(dict.fromkeys(ordered_hints))


def _candidate_native_dirs() -> list[Path]:
    candidate_dirs = [(_NATIVE_LIB_ROOT / abi).resolve() for abi in _android_abi_hints()]
    return [directory for directory in dict.fromkeys(candidate_dirs) if directory.exists()]


_NATIVE_SEARCH_DIRS = _candidate_native_dirs()
_NATIVE_BIN_DIR = _NATIVE_SEARCH_DIRS[0] if _NATIVE_SEARCH_DIRS else (_NATIVE_LIB_ROOT / "arm64-v8a").resolve()

if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
    for native_dir in _NATIVE_SEARCH_DIRS:
        os.add_dll_directory(str(native_dir))


def _candidate_library_refs() -> list[str]:
    names = _candidate_library_names()
    refs: list[str] = []

    if hasattr(sys, "getandroidapilevel"):
        refs.extend(names)

    for native_dir in _NATIVE_SEARCH_DIRS or [_NATIVE_BIN_DIR]:
        refs.extend(str((native_dir / name).resolve()) for name in names)

    return list(dict.fromkeys(refs))


def _load_native_library():
    errors: list[str] = []

    if sys.platform != "win32":
        cpp_shared = _NATIVE_BIN_DIR / "libc++_shared.so"
        if cpp_shared.exists():
            try:
                ctypes.CDLL(str(cpp_shared))
                errors.append(f"Loaded dependency: {cpp_shared}")
            except OSError as error:
                errors.append(f"Failed to load dependency {cpp_shared}: {error}")
        else:
            errors.append(f"Dependency not found: {cpp_shared}")

    for reference in _candidate_library_refs():
        try:
            reference_path = Path(reference)

            if reference_path.is_absolute():
                if not reference_path.exists():
                    errors.append(f"Not found: {reference_path}")
                    continue

                loaded = ctypes.CDLL(str(reference_path))
                errors.append(f"Loaded native library: {reference_path}")
                return loaded

            loaded = ctypes.CDLL(reference)
            errors.append(f"Loaded native library by name: {reference}")
            return loaded

        except OSError as error:
            errors.append(f"Failed to load {reference}: {error}")

    raise RuntimeError(
        "Native planner core load failed.\n"
        + "\n".join(errors)
        + f"\nExpected directory: {_NATIVE_BIN_DIR}"
    )


_lib = _load_native_library()
lib = _lib

_NATIVE_SIGNATURES: dict[str, tuple[list[object], object]] = {
    "make_alarm": ([ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int], ctypes.c_int),
    "is_valid_time": ([ctypes.c_int, ctypes.c_int], ctypes.c_int),
    "time_to_minutes": ([ctypes.c_int, ctypes.c_int], ctypes.c_int),
    "normalize_duration_minutes": ([ctypes.c_int], ctypes.c_int),
    "normalize_hour_24": ([ctypes.c_int], ctypes.c_int),
    "normalize_end_minutes_for_day_span": ([ctypes.c_int, ctypes.c_int], ctypes.c_int),
    "week_type_code": ([ctypes.c_char_p], ctypes.c_int),
    "days_to_mask": ([ctypes.POINTER(ctypes.c_int), ctypes.c_int], ctypes.c_int),
    "is_alarm_within_recheck_window": (
        [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int],
        ctypes.c_int,
    ),
    "can_recheck_alarm_now": (
        [ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int],
        ctypes.c_int,
    ),
    "is_week_even": (
        [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ],
        ctypes.c_int,
    ),
    "compute_rating_value": ([ctypes.c_int, ctypes.c_int], ctypes.c_float),
    "is_valid_date_text": ([ctypes.c_char_p], ctypes.c_int),
    "parse_date_text_yyyymmdd": ([ctypes.c_char_p], ctypes.c_int),
    "normalize_priority": ([ctypes.c_int], ctypes.c_int),
    "theme_mode_code": ([ctypes.c_char_p], ctypes.c_int),
    "sort_indices_by_int_desc": (
        [ctypes.POINTER(ctypes.c_int), ctypes.c_int, ctypes.POINTER(ctypes.c_int)],
        None,
    ),
    "sort_indices_by_double_desc": (
        [ctypes.POINTER(ctypes.c_double), ctypes.c_int, ctypes.POINTER(ctypes.c_int)],
        None,
    ),
    "sort_date_text_indices_asc": (
        [ctypes.POINTER(ctypes.c_char_p), ctypes.c_int, ctypes.POINTER(ctypes.c_int)],
        ctypes.c_int,
    ),
    "collect_task_indices_for_type_and_date": (
        [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
        ],
        ctypes.c_int,
    ),
    "collect_task_indices_for_lesson": (
        [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
        ],
        ctypes.c_int,
    ),
    "collect_task_indices_for_type_and_date_sorted": (
        [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
        ],
        ctypes.c_int,
    ),
    "collect_task_indices_for_lesson_sorted": (
        [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
        ],
        ctypes.c_int,
    ),
    "compute_task_ratings": (
        [
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
        ],
        None,
    ),
    "collect_urgent_task_indices_sorted": (
        [ctypes.POINTER(ctypes.c_double), ctypes.c_int, ctypes.c_double, ctypes.POINTER(ctypes.c_int)],
        ctypes.c_int,
    ),
    "collect_schedule_lesson_indices_for_day": (
        [
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
        ],
        ctypes.c_int,
    ),
    "select_active_template_index": (
        [ctypes.POINTER(ctypes.c_char_p), ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int],
        ctypes.c_int,
    ),
    "derive_schedule_period_end_yyyymmdd": (
        [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_char_p,
        ],
        ctypes.c_int,
    ),
    "derive_schedule_template_end_yyyymmdd": (
        [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.c_int,
        ],
        ctypes.c_int,
    ),
    "is_session_schedule": ([ctypes.c_char_p, ctypes.c_char_p], ctypes.c_int),
    "select_next_lesson_index": (
        [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ],
        ctypes.c_int,
    ),
    "select_next_lesson_index_with_horizon": (
        [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ],
        ctypes.c_int,
    ),
    "compute_buffered_alarm_minutes": (
        [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int],
        ctypes.c_int,
    ),
    "collect_lesson_indices_for_date_sorted": (
        [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
        ],
        ctypes.c_int,
    ),
    "collect_date_text_indices_in_range_sorted": (
        [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
        ],
        ctypes.c_int,
    ),
    "find_lesson_index_for_date_time_subject": (
        [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
        ],
        ctypes.c_int,
    ),
    "collect_alarm_indices_for_target_date_sorted": (
        [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
        ],
        ctypes.c_int,
    ),
    "collect_alarm_indices_on_or_after_date": (
        [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
        ],
        ctypes.c_int,
    ),
    "build_next_one_time_target_date_yyyymmdd": (
        [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int],
        ctypes.c_int,
    ),
    "collect_expired_one_time_alarm_indices": (
        [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
        ],
        ctypes.c_int,
    ),
    "collect_triggered_alarm_indices": (
        [
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
        ],
        ctypes.c_int,
    ),
    "collect_matching_dates_for_weekday_parity": (
        [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
        ],
        ctypes.c_int,
    ),
    "collect_template_occurrence_pairs": (
        [
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
        ],
        ctypes.c_int,
    ),
    "parse_schedule_xlsx": ([ctypes.c_char_p, ctypes.c_char_p], ctypes.c_int),
    "copy_last_error_message": ([ctypes.c_char_p, ctypes.c_int], ctypes.c_int),
}


def _configure_native_signatures() -> None:
    if _lib is None:
        return

    for name, (argtypes, restype) in _NATIVE_SIGNATURES.items():
        if not hasattr(_lib, name):
            continue
        native_function = getattr(_lib, name)
        native_function.argtypes = argtypes
        native_function.restype = restype


_configure_native_signatures()


def _require_native_function(name: str):
    if _lib is None:
        raise RuntimeError(
            f"Native planner core is unavailable. Expected DLL/SO in '{_NATIVE_BIN_DIR}'."
        )

    if not hasattr(_lib, name):
        raise RuntimeError(f"Native planner core does not export '{name}'.")

    return getattr(_lib, name)


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


def _encode_text_values(values: list[str]):
    return (ctypes.c_char_p * len(values))(*[str(value).encode("utf-8") for value in values])


def _decode_yyyymmdd(encoded: int) -> str:
    year = encoded // 10000
    month = (encoded // 100) % 100
    day = encoded % 100
    return f"{day:02d}.{month:02d}.{year:04d}"


def _decode_yyyymmdd_date(encoded: int) -> datetime.date:
    year = encoded // 10000
    month = (encoded // 100) % 100
    day = encoded % 100
    return datetime.date(year, month, day)


def _get_native_error_message() -> str:
    if _lib is None or not hasattr(_lib, "copy_last_error_message"):
        return ""

    native_function = _require_native_function("copy_last_error_message")
    buffer = ctypes.create_string_buffer(2048)
    size = native_function(buffer, len(buffer))
    if size <= 0:
        return ""

    return buffer.value.decode("utf-8", errors="replace").strip()


def make_alarm(hour: int, minute: int, prep: int, travel: int) -> int:
    native_function = _require_native_function("make_alarm")
    return int(native_function(int(hour), int(minute), int(prep), int(travel)))


def is_valid_time(hour: int, minute: int) -> bool:
    native_function = _require_native_function("is_valid_time")
    return bool(native_function(int(hour), int(minute)))


def time_to_minutes(time_text: str) -> int:
    parsed = _parse_time_text(time_text)
    if parsed is None:
        return -1

    hour, minute = parsed
    native_function = _require_native_function("time_to_minutes")
    return int(native_function(hour, minute))


def normalize_duration_minutes(minutes: int) -> int:
    native_function = _require_native_function("normalize_duration_minutes")
    return int(native_function(int(minutes)))


def normalize_hour_24(hour: int) -> int:
    native_function = _require_native_function("normalize_hour_24")
    return int(native_function(int(hour)))


def normalize_end_minutes_for_day_span(start_minutes: int, end_minutes: int) -> int:
    native_function = _require_native_function("normalize_end_minutes_for_day_span")
    return int(native_function(int(start_minutes), int(end_minutes)))


def week_type_code(week_type: str) -> int:
    native_function = _require_native_function("week_type_code")
    return int(native_function(str(week_type).encode("utf-8")))


def days_to_mask(days: list[int]) -> int:
    if not days:
        return 0

    native_function = _require_native_function("days_to_mask")
    values = (ctypes.c_int * len(days))(*[int(day) for day in days])
    return int(native_function(values, len(days)))


def is_alarm_within_recheck_window(
    alarm_hour: int,
    alarm_minute: int,
    now_hour: int,
    now_minute: int,
    lead_minutes: int,
) -> bool:
    native_function = _require_native_function("is_alarm_within_recheck_window")
    return bool(
        native_function(
            int(alarm_hour),
            int(alarm_minute),
            int(now_hour),
            int(now_minute),
            int(lead_minutes),
        )
    )


def can_recheck_alarm_now(
    rechecked_at: str,
    now: datetime.datetime,
    cooldown_minutes: int,
) -> bool:
    native_function = _require_native_function("can_recheck_alarm_now")
    return bool(
        native_function(
            str(rechecked_at).encode("utf-8"),
            now.day,
            now.month,
            now.year,
            now.hour,
            now.minute,
            int(cooldown_minutes),
        )
    )


def is_week_even(
    date: datetime.date,
    semester_start: str,
    first_week_even: bool,
) -> bool:
    try:
        start = datetime.datetime.strptime(semester_start, "%d.%m.%Y").date()
    except Exception:
        return date.isocalendar()[1] % 2 == 0

    native_function = _require_native_function("is_week_even")
    return bool(
        native_function(
            date.day,
            date.month,
            date.year,
            start.day,
            start.month,
            start.year,
            int(first_week_even),
        )
    )


def compute_rating_value(priority: int, days_until: int) -> float:
    native_function = _require_native_function("compute_rating_value")
    return float(native_function(int(priority), int(days_until)))


def is_valid_date_text(value: str) -> bool:
    if not isinstance(value, str):
        return False

    native_function = _require_native_function("is_valid_date_text")
    return bool(native_function(value.encode("utf-8")))


def parse_date_text_to_date(value: str) -> datetime.date | None:
    if not isinstance(value, str):
        return None

    native_function = _require_native_function("parse_date_text_yyyymmdd")
    encoded = int(native_function(value.encode("utf-8")))
    if encoded <= 0:
        return None
    return _decode_yyyymmdd_date(encoded)


def normalize_priority(priority: int) -> int:
    native_function = _require_native_function("normalize_priority")
    return int(native_function(int(priority)))


def normalize_theme(theme: str) -> str:
    native_function = _require_native_function("theme_mode_code")
    theme_code = int(native_function(str(theme).encode("utf-8")))
    return {
        0: "system",
        1: "light",
        2: "dark",
    }.get(theme_code, "system")


def sort_indices_by_int_desc(values: list[int]) -> list[int]:
    if not values:
        return []

    native_function = _require_native_function("sort_indices_by_int_desc")
    count = len(values)
    input_values = (ctypes.c_int * count)(*values)
    output_indices = (ctypes.c_int * count)()
    native_function(input_values, count, output_indices)
    return list(output_indices)


def sort_indices_by_double_desc(values: list[float]) -> list[int]:
    if not values:
        return []

    native_function = _require_native_function("sort_indices_by_double_desc")
    count = len(values)
    input_values = (ctypes.c_double * count)(*values)
    output_indices = (ctypes.c_int * count)()
    native_function(input_values, count, output_indices)
    return list(output_indices)


def sort_date_text_indices_asc(date_strings: list[str]) -> list[int]:
    if not date_strings:
        return []

    native_function = _require_native_function("sort_date_text_indices_asc")
    count = len(date_strings)
    date_values = _encode_text_values(date_strings)
    output_indices = (ctypes.c_int * count)()
    matched_count = native_function(date_values, count, output_indices)
    return list(output_indices[:matched_count])


def collect_task_indices_for_type_and_date(
    task_types: list[str],
    date_strings: list[str],
    expected_type: str,
    expected_date: str,
) -> list[int]:
    if not task_types or not date_strings or len(task_types) != len(date_strings):
        return []

    native_function = _require_native_function("collect_task_indices_for_type_and_date")
    count = len(task_types)
    task_type_values = _encode_text_values(task_types)
    date_values = _encode_text_values(date_strings)
    output_indices = (ctypes.c_int * count)()
    matched_count = native_function(
        task_type_values,
        date_values,
        count,
        expected_type.encode("utf-8"),
        expected_date.encode("utf-8"),
        output_indices,
    )
    return list(output_indices[:matched_count])


def collect_task_indices_for_lesson(
    lesson_ids: list[str],
    expected_lesson_id: str,
) -> list[int]:
    if not lesson_ids:
        return []

    native_function = _require_native_function("collect_task_indices_for_lesson")
    count = len(lesson_ids)
    lesson_id_values = _encode_text_values(lesson_ids)
    output_indices = (ctypes.c_int * count)()
    matched_count = native_function(
        lesson_id_values,
        count,
        expected_lesson_id.encode("utf-8"),
        output_indices,
    )
    return list(output_indices[:matched_count])


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

    native_function = _require_native_function("collect_task_indices_for_type_and_date_sorted")
    count = len(task_types)
    task_type_values = _encode_text_values(task_types)
    date_values = _encode_text_values(date_strings)
    priority_values = (ctypes.c_int * count)(*priorities)
    output_indices = (ctypes.c_int * count)()
    matched_count = native_function(
        task_type_values,
        date_values,
        priority_values,
        count,
        expected_type.encode("utf-8"),
        expected_date.encode("utf-8"),
        output_indices,
    )
    return list(output_indices[:matched_count])


def collect_task_indices_for_lesson_sorted(
    lesson_ids: list[str],
    priorities: list[int],
    expected_lesson_id: str,
) -> list[int]:
    if not lesson_ids or not priorities or len(lesson_ids) != len(priorities):
        return []

    native_function = _require_native_function("collect_task_indices_for_lesson_sorted")
    count = len(lesson_ids)
    lesson_id_values = _encode_text_values(lesson_ids)
    priority_values = (ctypes.c_int * count)(*priorities)
    output_indices = (ctypes.c_int * count)()
    matched_count = native_function(
        lesson_id_values,
        priority_values,
        count,
        expected_lesson_id.encode("utf-8"),
        output_indices,
    )
    return list(output_indices[:matched_count])


def compute_task_ratings_for_dates(
    priorities: list[int],
    date_strings: list[str],
    today: datetime.date,
) -> list[float]:
    if not priorities or not date_strings or len(priorities) != len(date_strings):
        return []

    native_function = _require_native_function("compute_task_ratings")
    count = len(priorities)
    priority_values = (ctypes.c_int * count)(*priorities)
    date_values = _encode_text_values(date_strings)
    output_ratings = (ctypes.c_double * count)()
    native_function(
        priority_values,
        date_values,
        count,
        today.day,
        today.month,
        today.year,
        output_ratings,
    )
    return list(output_ratings)


def collect_urgent_task_indices_sorted(
    ratings: list[float],
    threshold: float,
) -> list[int]:
    if not ratings:
        return []

    native_function = _require_native_function("collect_urgent_task_indices_sorted")
    count = len(ratings)
    rating_values = (ctypes.c_double * count)(*ratings)
    output_indices = (ctypes.c_int * count)()
    matched_count = native_function(rating_values, count, float(threshold), output_indices)
    return list(output_indices[:matched_count])


def collect_schedule_lesson_indices_for_day(
    lesson_days: list[int],
    lesson_start_minutes: list[int],
    expected_day: int,
) -> list[int]:
    if (
        not lesson_days
        or not lesson_start_minutes
        or len(lesson_days) != len(lesson_start_minutes)
    ):
        return []

    native_function = _require_native_function("collect_schedule_lesson_indices_for_day")
    count = len(lesson_days)
    day_values = (ctypes.c_int * count)(*lesson_days)
    start_minute_values = (ctypes.c_int * count)(*lesson_start_minutes)
    output_indices = (ctypes.c_int * count)()
    matched_count = native_function(
        day_values,
        start_minute_values,
        count,
        int(expected_day),
        output_indices,
    )
    return list(output_indices[:matched_count])


def select_active_template_index(
    template_starts: list[str],
    target_date: datetime.date,
) -> int:
    if not template_starts:
        return -1

    native_function = _require_native_function("select_active_template_index")
    count = len(template_starts)
    start_values = _encode_text_values(template_starts)
    return int(
        native_function(
            start_values,
            count,
            target_date.day,
            target_date.month,
            target_date.year,
        )
    )


def derive_schedule_period_end_date(
    start_date: datetime.date,
    next_start: datetime.date | None,
    template_title: str = "",
    schedule_type: str = "weekly",
) -> datetime.date:
    native_function = _require_native_function("derive_schedule_period_end_yyyymmdd")
    encoded = int(
        native_function(
            start_date.day,
            start_date.month,
            start_date.year,
            int(next_start is not None),
            next_start.day if next_start else 0,
            next_start.month if next_start else 0,
            next_start.year if next_start else 0,
            str(template_title).encode("utf-8"),
            str(schedule_type).encode("utf-8"),
        )
    )
    return _decode_yyyymmdd_date(encoded)


def derive_schedule_template_end_date(
    start_date: datetime.date,
    next_start: datetime.date | None,
    template_title: str = "",
    schedule_type: str = "weekly",
    dated_date_texts: list[str] | None = None,
) -> datetime.date:
    native_function = _require_native_function("derive_schedule_template_end_yyyymmdd")
    date_values = _encode_text_values(dated_date_texts or [])
    encoded = int(
        native_function(
            start_date.day,
            start_date.month,
            start_date.year,
            int(next_start is not None),
            next_start.day if next_start else 0,
            next_start.month if next_start else 0,
            next_start.year if next_start else 0,
            str(template_title).encode("utf-8"),
            str(schedule_type).encode("utf-8"),
            date_values,
            len(dated_date_texts or []),
        )
    )
    return _decode_yyyymmdd_date(encoded)


def is_session_schedule_template(schedule_type: str, template_title: str = "") -> bool:
    native_function = _require_native_function("is_session_schedule")
    return bool(
        native_function(
            str(schedule_type).encode("utf-8"),
            str(template_title).encode("utf-8"),
        )
    )


def select_next_lesson_index(
    date_strings: list[str],
    start_minutes: list[int],
    now: datetime.datetime,
    max_days_ahead: int = -1,
) -> int:
    if not date_strings or not start_minutes or len(date_strings) != len(start_minutes):
        return -1

    count = len(date_strings)
    date_values = _encode_text_values(date_strings)
    minute_values = (ctypes.c_int * count)(*start_minutes)
    now_minutes = now.hour * 60 + now.minute

    if hasattr(_lib, "select_next_lesson_index_with_horizon"):
        native_function = _require_native_function("select_next_lesson_index_with_horizon")
        return int(
            native_function(
                date_values,
                minute_values,
                count,
                now.day,
                now.month,
                now.year,
                now_minutes,
                int(max_days_ahead),
            )
        )

    if max_days_ahead >= 0:
        raise RuntimeError("Native planner core does not support lesson horizon filtering.")

    native_function = _require_native_function("select_next_lesson_index")
    return int(
        native_function(
            date_values,
            minute_values,
            count,
            now.day,
            now.month,
            now.year,
            now_minutes,
        )
    )


def compute_buffered_alarm_minutes(
    lesson_start_minutes: int,
    prep_minutes: int,
    travel_minutes: int,
    buffer_minutes: int,
) -> int:
    native_function = _require_native_function("compute_buffered_alarm_minutes")
    return int(
        native_function(
            int(lesson_start_minutes),
            int(prep_minutes),
            int(travel_minutes),
            int(buffer_minutes),
        )
    )


def collect_lesson_indices_for_date_sorted(
    date_strings: list[str],
    start_minutes: list[int],
    expected_date: str,
) -> list[int]:
    if not date_strings or not start_minutes or len(date_strings) != len(start_minutes):
        return []

    native_function = _require_native_function("collect_lesson_indices_for_date_sorted")
    count = len(date_strings)
    date_values = _encode_text_values(date_strings)
    minute_values = (ctypes.c_int * count)(*start_minutes)
    output_indices = (ctypes.c_int * count)()
    matched_count = native_function(
        date_values,
        minute_values,
        count,
        expected_date.encode("utf-8"),
        output_indices,
    )
    return list(output_indices[:matched_count])


def collect_date_text_indices_in_range_sorted(
    date_strings: list[str],
    start_minutes: list[int],
    start_date: datetime.date,
    end_date: datetime.date,
) -> list[int]:
    if (
        not date_strings
        or not start_minutes
        or len(date_strings) != len(start_minutes)
        or end_date < start_date
    ):
        return []

    native_function = _require_native_function("collect_date_text_indices_in_range_sorted")
    count = len(date_strings)
    date_values = _encode_text_values(date_strings)
    minute_values = (ctypes.c_int * count)(*start_minutes)
    output_indices = (ctypes.c_int * count)()
    matched_count = native_function(
        date_values,
        minute_values,
        count,
        start_date.day,
        start_date.month,
        start_date.year,
        end_date.day,
        end_date.month,
        end_date.year,
        output_indices,
    )
    return list(output_indices[:matched_count])


def find_lesson_index_for_date_time_subject(
    date_strings: list[str],
    start_minutes: list[int],
    subjects: list[str],
    expected_date: str,
    expected_start_minutes: int,
    expected_subject: str,
) -> int:
    if (
        not date_strings
        or not start_minutes
        or not subjects
        or len(date_strings) != len(start_minutes)
        or len(date_strings) != len(subjects)
    ):
        return -1

    native_function = _require_native_function("find_lesson_index_for_date_time_subject")
    count = len(date_strings)
    date_values = _encode_text_values(date_strings)
    minute_values = (ctypes.c_int * count)(*start_minutes)
    subject_values = _encode_text_values(subjects)
    return int(
        native_function(
            date_values,
            minute_values,
            subject_values,
            count,
            expected_date.encode("utf-8"),
            int(expected_start_minutes),
            expected_subject.encode("utf-8"),
        )
    )


def collect_alarm_indices_for_target_date_sorted(
    target_dates: list[str],
    enabled_flags: list[int],
    alarm_minutes: list[int],
    expected_date: str,
) -> list[int]:
    if (
        not target_dates
        or not enabled_flags
        or not alarm_minutes
        or len(target_dates) != len(enabled_flags)
        or len(target_dates) != len(alarm_minutes)
    ):
        return []

    native_function = _require_native_function("collect_alarm_indices_for_target_date_sorted")
    count = len(target_dates)
    date_values = _encode_text_values(target_dates)
    enabled_values = (ctypes.c_int * count)(*enabled_flags)
    minute_values = (ctypes.c_int * count)(*alarm_minutes)
    output_indices = (ctypes.c_int * count)()
    matched_count = native_function(
        date_values,
        enabled_values,
        minute_values,
        count,
        expected_date.encode("utf-8"),
        output_indices,
    )
    return list(output_indices[:matched_count])


def collect_alarm_indices_on_or_after_date(
    target_dates: list[str],
    today: datetime.date,
) -> list[int]:
    if not target_dates:
        return []

    native_function = _require_native_function("collect_alarm_indices_on_or_after_date")
    count = len(target_dates)
    date_values = _encode_text_values(target_dates)
    output_indices = (ctypes.c_int * count)()
    matched_count = native_function(
        date_values,
        count,
        today.day,
        today.month,
        today.year,
        output_indices,
    )
    return list(output_indices[:matched_count])


def build_next_one_time_target_date(
    hour: int,
    minute: int,
    now: datetime.datetime,
) -> str:
    native_function = _require_native_function("build_next_one_time_target_date_yyyymmdd")
    encoded = int(
        native_function(
            int(hour),
            int(minute),
            now.day,
            now.month,
            now.year,
            now.hour * 60 + now.minute,
        )
    )
    return _decode_yyyymmdd(encoded)


def collect_expired_one_time_alarm_indices(
    target_dates: list[str],
    enabled_flags: list[int],
    one_time_flags: list[int],
    today: datetime.date,
) -> list[int]:
    if (
        not target_dates
        or not enabled_flags
        or not one_time_flags
        or len(target_dates) != len(enabled_flags)
        or len(target_dates) != len(one_time_flags)
    ):
        return []

    native_function = _require_native_function("collect_expired_one_time_alarm_indices")
    count = len(target_dates)
    target_date_values = _encode_text_values(target_dates)
    enabled_values = (ctypes.c_int * count)(*enabled_flags)
    one_time_values = (ctypes.c_int * count)(*one_time_flags)
    output_indices = (ctypes.c_int * count)()
    matched_count = native_function(
        target_date_values,
        enabled_values,
        one_time_values,
        count,
        today.day,
        today.month,
        today.year,
        output_indices,
    )
    return list(output_indices[:matched_count])


def collect_triggered_alarm_indices(
    enabled_flags: list[int],
    alarm_hours: list[int],
    alarm_minutes: list[int],
    has_target_dates: list[int],
    target_dates: list[str],
    week_type_codes: list[int],
    day_masks: list[int],
    now: datetime.datetime,
    is_even_week: bool,
) -> list[int]:
    if (
        not enabled_flags
        or not alarm_hours
        or not alarm_minutes
        or not has_target_dates
        or not target_dates
        or not week_type_codes
        or not day_masks
    ):
        return []

    count = len(enabled_flags)
    if any(
        len(values) != count
        for values in [
            alarm_hours,
            alarm_minutes,
            has_target_dates,
            target_dates,
            week_type_codes,
            day_masks,
        ]
    ):
        return []

    native_function = _require_native_function("collect_triggered_alarm_indices")
    enabled_values = (ctypes.c_int * count)(*enabled_flags)
    hour_values = (ctypes.c_int * count)(*alarm_hours)
    minute_values = (ctypes.c_int * count)(*alarm_minutes)
    has_target_date_values = (ctypes.c_int * count)(*has_target_dates)
    target_date_values = _encode_text_values(target_dates)
    week_type_value_array = (ctypes.c_int * count)(*week_type_codes)
    day_mask_values = (ctypes.c_int * count)(*day_masks)
    output_indices = (ctypes.c_int * count)()
    matched_count = native_function(
        enabled_values,
        hour_values,
        minute_values,
        has_target_date_values,
        target_date_values,
        week_type_value_array,
        day_mask_values,
        count,
        now.day,
        now.month,
        now.year,
        now.hour,
        now.minute,
        int(is_even_week),
        output_indices,
    )
    return list(output_indices[:matched_count])


def collect_matching_dates_for_weekday_parity(
    start_date: datetime.date,
    end_date: datetime.date,
    semester_start: datetime.date,
    first_week_even: bool,
    expected_weekday: int,
    expected_is_even: bool,
) -> list[datetime.date]:
    if end_date < start_date:
        return []

    native_function = _require_native_function("collect_matching_dates_for_weekday_parity")
    max_days = (end_date - start_date).days + 1
    output_dates = (ctypes.c_int * max_days)()
    matched_count = native_function(
        start_date.day,
        start_date.month,
        start_date.year,
        end_date.day,
        end_date.month,
        end_date.year,
        semester_start.day,
        semester_start.month,
        semester_start.year,
        int(first_week_even),
        int(expected_weekday),
        int(expected_is_even),
        output_dates,
        max_days,
    )
    return [_decode_yyyymmdd_date(int(encoded)) for encoded in output_dates[:matched_count]]


def collect_template_occurrence_pairs(
    lesson_days: list[int],
    lesson_start_minutes: list[int],
    lesson_even_flags: list[int],
    start_date: datetime.date,
    end_date: datetime.date,
    semester_start: datetime.date,
    first_week_even: bool,
) -> list[tuple[int, datetime.date]]:
    if (
        not lesson_days
        or not lesson_start_minutes
        or not lesson_even_flags
        or len(lesson_days) != len(lesson_start_minutes)
        or len(lesson_days) != len(lesson_even_flags)
        or end_date < start_date
    ):
        return []

    native_function = _require_native_function("collect_template_occurrence_pairs")
    count = len(lesson_days)
    max_weeks = ((end_date - start_date).days // 7) + 2
    capacity = max(1, count * max_weeks)
    lesson_day_values = (ctypes.c_int * count)(*lesson_days)
    start_minute_values = (ctypes.c_int * count)(*lesson_start_minutes)
    even_flag_values = (ctypes.c_int * count)(*lesson_even_flags)
    output_lesson_indices = (ctypes.c_int * capacity)()
    output_dates = (ctypes.c_int * capacity)()
    matched_count = native_function(
        lesson_day_values,
        start_minute_values,
        even_flag_values,
        count,
        start_date.day,
        start_date.month,
        start_date.year,
        end_date.day,
        end_date.month,
        end_date.year,
        semester_start.day,
        semester_start.month,
        semester_start.year,
        int(first_week_even),
        output_lesson_indices,
        output_dates,
        capacity,
    )

    result: list[tuple[int, datetime.date]] = []
    for index in range(matched_count):
        result.append(
            (
                int(output_lesson_indices[index]),
                _decode_yyyymmdd_date(int(output_dates[index])),
            )
        )
    return result


def parse_schedule_xlsx_file(xlsx_path: str | Path, output_json_path: str | Path) -> None:
    native_function = _require_native_function("parse_schedule_xlsx")
    xlsx_path_text = str(Path(xlsx_path))
    output_json_text = str(Path(output_json_path))
    ok = native_function(
        xlsx_path_text.encode("utf-8"),
        output_json_text.encode("utf-8"),
    )
    if ok:
        return

    message = _get_native_error_message() or "Unknown native XLSX parser error."
    raise RuntimeError(message)
