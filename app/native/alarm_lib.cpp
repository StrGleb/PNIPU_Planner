#include "alarm_lib.h"

namespace
{
    int days_from_civil(int year, int month, int day)
    {
        year -= month <= 2;
        const int era = (year >= 0 ? year : year - 399) / 400;
        const unsigned yoe = static_cast<unsigned>(year - era * 400);
        const unsigned doy = (153 * (month + (month > 2 ? -3 : 9)) + 2) / 5
            + static_cast<unsigned>(day) - 1;
        const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
        return era * 146097 + static_cast<int>(doe) - 719468;
    }

    int floor_div(int value, int divisor)
    {
        int quotient = value / divisor;
        int remainder = value % divisor;
        if (remainder != 0 && ((remainder < 0) != (divisor < 0))) {
            --quotient;
        }
        return quotient;
    }
}

int make_alarm(
    int hour_start,
    int min_start,
    int time_to_get_ready,
    int time_to_way
) {
    int start_minutes = hour_start * 60 + min_start;
    int alarm_minutes = start_minutes - time_to_get_ready - time_to_way;

    while (alarm_minutes < 0) {
        alarm_minutes += 24 * 60;
    }

    return alarm_minutes;
}

int is_valid_time(int hour, int minute)
{
    return hour >= 0 && hour <= 23 && minute >= 0 && minute <= 59;
}

int time_to_minutes(int hour, int minute)
{
    if (!is_valid_time(hour, minute)) {
        return -1;
    }

    return hour * 60 + minute;
}

int normalize_duration_minutes(int minutes)
{
    return minutes < 0 ? 0 : minutes;
}

int is_week_even(
    int day,
    int month,
    int year,
    int semester_start_day,
    int semester_start_month,
    int semester_start_year,
    int first_week_even
)
{
    const int current_days = days_from_civil(year, month, day);
    const int semester_start_days = days_from_civil(
        semester_start_year,
        semester_start_month,
        semester_start_day
    );
    const int weeks_elapsed = floor_div(current_days - semester_start_days, 7);
    const int same_parity_as_first = weeks_elapsed % 2 == 0;

    return same_parity_as_first == (first_week_even != 0);
}
