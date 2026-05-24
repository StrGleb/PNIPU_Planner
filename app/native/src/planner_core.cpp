#include "planner_core.h"

#include <algorithm>
#include <cstddef>
#include <cstring>
#include <numeric>
#include <string>
#include <vector>

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

    bool is_leap_year(int year)
    {
        return (year % 4 == 0 && year % 100 != 0) || year % 400 == 0;
    }

    int days_in_month(int year, int month)
    {
        static const int month_lengths[] = {
            31, 28, 31, 30, 31, 30,
            31, 31, 30, 31, 30, 31
        };

        if (month < 1 || month > 12) {
            return 0;
        }

        if (month == 2 && is_leap_year(year)) {
            return 29;
        }

        return month_lengths[month - 1];
    }

    bool parse_two_digits(const char* text, int offset, int& value)
    {
        if (text[offset] < '0' || text[offset] > '9') {
            return false;
        }
        if (text[offset + 1] < '0' || text[offset + 1] > '9') {
            return false;
        }

        value = (text[offset] - '0') * 10 + (text[offset + 1] - '0');
        return true;
    }

    bool parse_four_digits(const char* text, int offset, int& value)
    {
        value = 0;
        for (int i = 0; i < 4; ++i) {
            const char current = text[offset + i];
            if (current < '0' || current > '9') {
                return false;
            }
            value = value * 10 + (current - '0');
        }
        return true;
    }

    bool equals_text(const char* lhs, const char* rhs)
    {
        if (lhs == nullptr || rhs == nullptr) {
            return false;
        }

        return std::strcmp(lhs, rhs) == 0;
    }
}

int make_alarm(
    int hour_start,
    int min_start,
    int time_to_get_ready,
    int time_to_way
)
{
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

float compute_rating_value(int priority, int days_until)
{
    const float priority_score = priority * 30.0f;
    float urgency_score = 0.0f;

    if (days_until < 0) {
        urgency_score = 150.0f;
    }
    else if (days_until == 0) {
        urgency_score = 120.0f;
    }
    else if (days_until <= 14) {
        urgency_score = (1.0f - static_cast<float>(days_until) / 14.0f) * 100.0f;
    }

    return priority_score + urgency_score;
}

int is_valid_date_text(const char* text)
{
    if (text == nullptr || std::strlen(text) != 10) {
        return 0;
    }

    if (text[2] != '.' || text[5] != '.') {
        return 0;
    }

    int day = 0;
    int month = 0;
    int year = 0;
    if (!parse_two_digits(text, 0, day)) {
        return 0;
    }
    if (!parse_two_digits(text, 3, month)) {
        return 0;
    }
    if (!parse_four_digits(text, 6, year)) {
        return 0;
    }

    if (month < 1 || month > 12) {
        return 0;
    }

    const int max_day = days_in_month(year, month);
    if (day < 1 || day > max_day) {
        return 0;
    }

    return 1;
}

int normalize_priority(int priority)
{
    if (priority < 0) {
        return 0;
    }
    if (priority > 3) {
        return 3;
    }
    return priority;
}

int theme_mode_code(const char* theme)
{
    if (equals_text(theme, "light")) {
        return 1;
    }
    if (equals_text(theme, "dark")) {
        return 2;
    }
    return 0;
}

void sort_indices_by_int_desc(const int* values, int count, int* out_indices)
{
    if (count <= 0 || values == nullptr || out_indices == nullptr) {
        return;
    }

    std::vector<int> indices(static_cast<std::size_t>(count));
    std::iota(indices.begin(), indices.end(), 0);
    std::stable_sort(indices.begin(), indices.end(), [values](int lhs, int rhs) {
        return values[lhs] > values[rhs];
    });

    for (int i = 0; i < count; ++i) {
        out_indices[i] = indices[static_cast<std::size_t>(i)];
    }
}

int collect_task_indices_for_type_and_date(
    const char* const* task_types,
    const char* const* date_strings,
    int count,
    const char* expected_type,
    const char* expected_date,
    int* out_indices
)
{
    if (count <= 0 || task_types == nullptr || date_strings == nullptr || out_indices == nullptr) {
        return 0;
    }

    int out_count = 0;
    for (int i = 0; i < count; ++i) {
        if (equals_text(task_types[i], expected_type) && equals_text(date_strings[i], expected_date)) {
            out_indices[out_count] = i;
            ++out_count;
        }
    }

    return out_count;
}

int collect_task_indices_for_lesson(
    const char* const* lesson_ids,
    int count,
    const char* expected_lesson_id,
    int* out_indices
)
{
    if (count <= 0 || lesson_ids == nullptr || out_indices == nullptr) {
        return 0;
    }

    int out_count = 0;
    for (int i = 0; i < count; ++i) {
        if (equals_text(lesson_ids[i], expected_lesson_id)) {
            out_indices[out_count] = i;
            ++out_count;
        }
    }

    return out_count;
}

void sort_indices_by_double_desc(const double* values, int count, int* out_indices)
{
    if (count <= 0 || values == nullptr || out_indices == nullptr) {
        return;
    }

    std::vector<int> indices(static_cast<std::size_t>(count));
    std::iota(indices.begin(), indices.end(), 0);
    std::stable_sort(indices.begin(), indices.end(), [values](int lhs, int rhs) {
        return values[lhs] > values[rhs];
    });

    for (int i = 0; i < count; ++i) {
        out_indices[i] = indices[static_cast<std::size_t>(i)];
    }
}
