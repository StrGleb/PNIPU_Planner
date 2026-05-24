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

    PLANNER_CORE_API int parse_schedule_xlsx(
        const char* xlsx_path,
        const char* output_json_path
    );

    PLANNER_CORE_API int copy_last_error_message(
        char* buffer,
        int capacity
    );
}
