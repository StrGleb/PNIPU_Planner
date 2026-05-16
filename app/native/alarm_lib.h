#pragma once

#ifdef _WIN32
#define ALARM_API __declspec(dllexport)
#else
#define ALARM_API
#endif

extern "C"
{
    // Рассчитывает время пробуждения перед парой
    // hour_start - час начала пары, min_start - минута начала
    // time_to_get_ready - время на сборы, time_to_way - время на дорогу
    // возвращает время пробуждения в минутах с начала дня
    ALARM_API int make_alarm(
        int hour_start,
        int min_start,
        int time_to_get_ready,
        int time_to_way
    );

    // Проверяет корректность времени (часы 0-23, минуты 0-59)
    ALARM_API int is_valid_time(int hour, int minute);

    // Преобразует время (час, минута) в минуты с начала дня
    // возвращает -1 если время некорректно
    ALARM_API int time_to_minutes(int hour, int minute);

    // Нормализует длительность: если отрицательно то возвращает 0
    ALARM_API int normalize_duration_minutes(int minutes);

    // Определяет четность недели в семестре
    // first_week_even: 1 если первая неделя четная
    // возвращает: 1 если неделя четная, 0 если нечетная
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
