import ctypes
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