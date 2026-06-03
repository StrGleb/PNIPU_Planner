#include <pybind11/pybind11.h>
namespace py = pybind11;


float compute_rating_value(int priority, int days_until) {
    /**
     * Вычисляет числовой рейтинг задачи
     * @param priority Приоритет задачи
     * @param days_until Дней до дедлайна (отриц. значение = просрочка)
     * @return float Итоговый рейтинг
    */

    float priority_score = priority * 30.0f;
    float urgency_score;

    if (days_until < 0) {
        urgency_score = 150.0f;
    }
    else if (days_until == 0) {
        urgency_score = 120.0f;
    }
    else if (days_until <= 14) {
        urgency_score = (1.0f - static_cast<float>(days_until) / 14.0f) * 100.0f;
    }
    else {
        urgency_score = 0.0f;
    }

    return priority_score + urgency_score;
}
