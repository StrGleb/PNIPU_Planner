#pragma once

#ifdef _WIN32
#define PLANNER_CORE_API __declspec(dllexport)
#else
#define PLANNER_CORE_API
#endif

extern "C"
{
    PLANNER_CORE_API int make_alarm(
        int hour_start,
        int min_start,
        int time_to_get_ready,
        int time_to_way
    );

    PLANNER_CORE_API int is_valid_time(int hour, int minute);

    PLANNER_CORE_API int time_to_minutes(int hour, int minute);

    PLANNER_CORE_API int normalize_duration_minutes(int minutes);

    PLANNER_CORE_API int is_week_even(
        int day,
        int month,
        int year,
        int semester_start_day,
        int semester_start_month,
        int semester_start_year,
        int first_week_even
    );

    PLANNER_CORE_API float compute_rating_value(int priority, int days_until);

    PLANNER_CORE_API int is_valid_date_text(const char* text);

    PLANNER_CORE_API int normalize_priority(int priority);

    PLANNER_CORE_API int theme_mode_code(const char* theme);

    PLANNER_CORE_API void sort_indices_by_int_desc(
        const int* values,
        int count,
        int* out_indices
    );

    PLANNER_CORE_API void sort_indices_by_double_desc(
        const double* values,
        int count,
        int* out_indices
    );

    PLANNER_CORE_API int collect_task_indices_for_type_and_date(
        const char* const* task_types,
        const char* const* date_strings,
        int count,
        const char* expected_type,
        const char* expected_date,
        int* out_indices
    );

    PLANNER_CORE_API int collect_task_indices_for_lesson(
        const char* const* lesson_ids,
        int count,
        const char* expected_lesson_id,
        int* out_indices
    );

    PLANNER_CORE_API int collect_task_indices_for_type_and_date_sorted(
        const char* const* task_types,
        const char* const* date_strings,
        const int* priorities,
        int count,
        const char* expected_type,
        const char* expected_date,
        int* out_indices
    );

    PLANNER_CORE_API int collect_task_indices_for_lesson_sorted(
        const char* const* lesson_ids,
        const int* priorities,
        int count,
        const char* expected_lesson_id,
        int* out_indices
    );

    PLANNER_CORE_API void compute_task_ratings(
        const int* priorities,
        const char* const* date_strings,
        int count,
        int today_day,
        int today_month,
        int today_year,
        double* out_ratings
    );

    PLANNER_CORE_API int collect_urgent_task_indices_sorted(
        const double* ratings,
        int count,
        double threshold,
        int* out_indices
    );

    PLANNER_CORE_API int collect_schedule_lesson_indices_for_day(
        const int* lesson_days,
        const int* lesson_start_minutes,
        int count,
        int expected_day,
        int* out_indices
    );

    PLANNER_CORE_API int select_active_template_index(
        const char* const* template_starts,
        int count,
        int target_day,
        int target_month,
        int target_year
    );

    PLANNER_CORE_API int derive_schedule_period_end_yyyymmdd(
        int start_day,
        int start_month,
        int start_year,
        int has_next_start,
        int next_start_day,
        int next_start_month,
        int next_start_year
    );

    PLANNER_CORE_API int select_next_lesson_index(
        const char* const* date_strings,
        const int* start_minutes,
        int count,
        int now_day,
        int now_month,
        int now_year,
        int now_minutes
    );

    PLANNER_CORE_API int compute_buffered_alarm_minutes(
        int lesson_start_minutes,
        int time_to_get_ready,
        int travel_minutes,
        int buffer_minutes
    );

    PLANNER_CORE_API int parse_schedule_xlsx(
        const char* xlsx_path,
        const char* output_json_path
    );

    PLANNER_CORE_API int copy_last_error_message(
        char* buffer,
        int capacity
    );
}
