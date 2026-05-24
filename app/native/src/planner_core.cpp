#include "planner_core.h"

#include <algorithm>
#include <cmath>
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

    void civil_from_days(int days, int& year, int& month, int& day)
    {
        days += 719468;
        const int era = (days >= 0 ? days : days - 146096) / 146097;
        const unsigned doe = static_cast<unsigned>(days - era * 146097);
        const unsigned yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
        year = static_cast<int>(yoe) + era * 400;
        const unsigned doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
        const unsigned mp = (5 * doy + 2) / 153;
        day = static_cast<int>(doy - (153 * mp + 2) / 5 + 1);
        month = static_cast<int>(mp < 10 ? mp + 3 : mp - 9);
        year += month <= 2;
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

    bool parse_date_text(const char* text, int& day, int& month, int& year)
    {
        if (text == nullptr || std::strlen(text) != 10) {
            return false;
        }

        if (text[2] != '.' || text[5] != '.') {
            return false;
        }

        if (!parse_two_digits(text, 0, day)) {
            return false;
        }
        if (!parse_two_digits(text, 3, month)) {
            return false;
        }
        if (!parse_four_digits(text, 6, year)) {
            return false;
        }

        if (month < 1 || month > 12) {
            return false;
        }

        const int max_day = days_in_month(year, month);
        return day >= 1 && day <= max_day;
    }

    void stable_sort_indices_by_int_desc(
        const int* values,
        std::vector<int>& indices
    )
    {
        std::stable_sort(indices.begin(), indices.end(), [values](int lhs, int rhs) {
            return values[lhs] > values[rhs];
        });
    }

    void stable_sort_indices_by_double_desc(
        const double* values,
        std::vector<int>& indices
    )
    {
        std::stable_sort(indices.begin(), indices.end(), [values](int lhs, int rhs) {
            return values[lhs] > values[rhs];
        });
    }

    void stable_sort_indices_by_int_asc(
        const int* values,
        std::vector<int>& indices
    )
    {
        std::stable_sort(indices.begin(), indices.end(), [values](int lhs, int rhs) {
            return values[lhs] < values[rhs];
        });
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
    int day = 0;
    int month = 0;
    int year = 0;
    return parse_date_text(text, day, month, year) ? 1 : 0;
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

int collect_task_indices_for_type_and_date_sorted(
    const char* const* task_types,
    const char* const* date_strings,
    const int* priorities,
    int count,
    const char* expected_type,
    const char* expected_date,
    int* out_indices
)
{
    if (
        count <= 0
        || task_types == nullptr
        || date_strings == nullptr
        || priorities == nullptr
        || out_indices == nullptr
    ) {
        return 0;
    }

    std::vector<int> indices;
    indices.reserve(static_cast<std::size_t>(count));
    for (int i = 0; i < count; ++i) {
        if (equals_text(task_types[i], expected_type) && equals_text(date_strings[i], expected_date)) {
            indices.push_back(i);
        }
    }

    stable_sort_indices_by_int_desc(priorities, indices);
    for (std::size_t i = 0; i < indices.size(); ++i) {
        out_indices[i] = indices[i];
    }

    return static_cast<int>(indices.size());
}

int collect_task_indices_for_lesson_sorted(
    const char* const* lesson_ids,
    const int* priorities,
    int count,
    const char* expected_lesson_id,
    int* out_indices
)
{
    if (
        count <= 0
        || lesson_ids == nullptr
        || priorities == nullptr
        || out_indices == nullptr
    ) {
        return 0;
    }

    std::vector<int> indices;
    indices.reserve(static_cast<std::size_t>(count));
    for (int i = 0; i < count; ++i) {
        if (equals_text(lesson_ids[i], expected_lesson_id)) {
            indices.push_back(i);
        }
    }

    stable_sort_indices_by_int_desc(priorities, indices);
    for (std::size_t i = 0; i < indices.size(); ++i) {
        out_indices[i] = indices[i];
    }

    return static_cast<int>(indices.size());
}

void compute_task_ratings(
    const int* priorities,
    const char* const* date_strings,
    int count,
    int today_day,
    int today_month,
    int today_year,
    double* out_ratings
)
{
    if (count <= 0 || priorities == nullptr || date_strings == nullptr || out_ratings == nullptr) {
        return;
    }

    const int today_days = days_from_civil(today_year, today_month, today_day);
    for (int i = 0; i < count; ++i) {
        int day = 0;
        int month = 0;
        int year = 0;
        if (!parse_date_text(date_strings[i], day, month, year)) {
            out_ratings[i] = 0.0;
            continue;
        }

        const int task_days = days_from_civil(year, month, day);
        const int days_until = task_days - today_days;
        out_ratings[i] = static_cast<double>(compute_rating_value(priorities[i], days_until));
    }
}

int collect_urgent_task_indices_sorted(
    const double* ratings,
    int count,
    double threshold,
    int* out_indices
)
{
    if (count <= 0 || ratings == nullptr || out_indices == nullptr) {
        return 0;
    }

    std::vector<int> indices;
    indices.reserve(static_cast<std::size_t>(count));
    for (int i = 0; i < count; ++i) {
        if (ratings[i] >= threshold) {
            indices.push_back(i);
        }
    }

    stable_sort_indices_by_double_desc(ratings, indices);
    for (std::size_t i = 0; i < indices.size(); ++i) {
        out_indices[i] = indices[i];
    }

    return static_cast<int>(indices.size());
}

int collect_schedule_lesson_indices_for_day(
    const int* lesson_days,
    const int* lesson_start_minutes,
    int count,
    int expected_day,
    int* out_indices
)
{
    if (
        count <= 0
        || lesson_days == nullptr
        || lesson_start_minutes == nullptr
        || out_indices == nullptr
    ) {
        return 0;
    }

    std::vector<int> indices;
    indices.reserve(static_cast<std::size_t>(count));
    for (int i = 0; i < count; ++i) {
        if (lesson_days[i] == expected_day) {
            indices.push_back(i);
        }
    }

    stable_sort_indices_by_int_asc(lesson_start_minutes, indices);
    for (std::size_t i = 0; i < indices.size(); ++i) {
        out_indices[i] = indices[i];
    }

    return static_cast<int>(indices.size());
}

int select_active_template_index(
    const char* const* template_starts,
    int count,
    int target_day,
    int target_month,
    int target_year
)
{
    if (count <= 0 || template_starts == nullptr) {
        return -1;
    }

    const int target_days = days_from_civil(target_year, target_month, target_day);
    int active_index = -1;
    int active_start_days = 0;

    for (int i = 0; i < count; ++i) {
        int day = 0;
        int month = 0;
        int year = 0;
        if (!parse_date_text(template_starts[i], day, month, year)) {
            continue;
        }

        const int start_days = days_from_civil(year, month, day);
        if (start_days <= target_days && (active_index < 0 || start_days >= active_start_days)) {
            active_index = i;
            active_start_days = start_days;
        }
    }

    if (active_index >= 0) {
        return active_index;
    }

    int first_valid_index = -1;
    int first_valid_days = 0;
    for (int i = 0; i < count; ++i) {
        int day = 0;
        int month = 0;
        int year = 0;
        if (!parse_date_text(template_starts[i], day, month, year)) {
            continue;
        }
        const int start_days = days_from_civil(year, month, day);
        if (first_valid_index < 0 || start_days < first_valid_days) {
            first_valid_index = i;
            first_valid_days = start_days;
        }
    }

    return first_valid_index;
}

int derive_schedule_period_end_yyyymmdd(
    int start_day,
    int start_month,
    int start_year,
    int has_next_start,
    int next_start_day,
    int next_start_month,
    int next_start_year
)
{
    int end_year = start_year;
    int end_month = 0;
    int end_day = 0;

    if (start_month >= 8) {
        end_year = start_year + 1;
        end_month = 1;
        end_day = 31;
    }
    else {
        end_month = 6;
        end_day = 30;
    }

    int end_days = days_from_civil(end_year, end_month, end_day);
    if (has_next_start != 0) {
        int next_start_days = days_from_civil(next_start_year, next_start_month, next_start_day) - 1;
        if (next_start_days < end_days) {
            end_days = next_start_days;
        }
    }

    civil_from_days(end_days, end_year, end_month, end_day);
    return end_year * 10000 + end_month * 100 + end_day;
}

int select_next_lesson_index(
    const char* const* date_strings,
    const int* start_minutes,
    int count,
    int now_day,
    int now_month,
    int now_year,
    int now_minutes
)
{
    if (count <= 0 || date_strings == nullptr || start_minutes == nullptr) {
        return -1;
    }

    const int now_days = days_from_civil(now_year, now_month, now_day);
    int best_index = -1;
    int best_days = 0;
    int best_start_minutes = 0;

    for (int i = 0; i < count; ++i) {
        int day = 0;
        int month = 0;
        int year = 0;
        if (!parse_date_text(date_strings[i], day, month, year)) {
            continue;
        }

        const int lesson_days = days_from_civil(year, month, day);
        const int lesson_start = start_minutes[i];
        if (lesson_days < now_days) {
            continue;
        }
        if (lesson_days == now_days && lesson_start <= now_minutes) {
            continue;
        }

        if (
            best_index < 0
            || lesson_days < best_days
            || (lesson_days == best_days && lesson_start < best_start_minutes)
        ) {
            best_index = i;
            best_days = lesson_days;
            best_start_minutes = lesson_start;
        }
    }

    return best_index;
}

int compute_buffered_alarm_minutes(
    int lesson_start_minutes,
    int time_to_get_ready,
    int travel_minutes,
    int buffer_minutes
)
{
    int alarm_minutes = lesson_start_minutes - time_to_get_ready - travel_minutes - buffer_minutes;
    while (alarm_minutes < 0) {
        alarm_minutes += 24 * 60;
    }
    return alarm_minutes % (24 * 60);
}

void sort_indices_by_double_desc(const double* values, int count, int* out_indices)
{
    if (count <= 0 || values == nullptr || out_indices == nullptr) {
        return;
    }

    std::vector<int> indices(static_cast<std::size_t>(count));
    std::iota(indices.begin(), indices.end(), 0);
    stable_sort_indices_by_double_desc(values, indices);

    for (int i = 0; i < count; ++i) {
        out_indices[i] = indices[static_cast<std::size_t>(i)];
    }
}
