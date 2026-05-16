#pragma once

#ifdef _WIN32
#define ALARM_API __declspec(dllexport)
#else
#define ALARM_API
#endif

extern "C"
{
    ALARM_API int make_alarm(
        int hour_start,
        int min_start,
        int time_to_get_ready,
        int time_to_way
    );

    ALARM_API int is_valid_time(int hour, int minute);

    ALARM_API int time_to_minutes(int hour, int minute);

    ALARM_API int normalize_duration_minutes(int minutes);

    ALARM_API int is_week_even(
        int day,
        int month,
        int year,
        int semester_start_day,
        int semester_start_month,
        int semester_start_year,
        int first_week_even
    );
}
