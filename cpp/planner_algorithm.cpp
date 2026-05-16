#include <pybind11/pybind11.h>

namespace py = pybind11;


float compute_rating_value(int priority, int days_until) {
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


bool is_more_urgent(int priority1, int days1, int priority2, int days2) {
    return compute_rating_value(priority1, days1) > compute_rating_value(priority2, days2);
}


const char* get_urgency_level(int priority, int days_until) {
    float rating = compute_rating_value(priority, days_until);
    if (rating >= 200.0f) return "critical";
    if (rating >= 100.0f) return "urgent";
    if (rating >= 50.0f) return "important";
    return "normal";
}

int get_notification_frequency(int priority, int days_until) {
    float rating = compute_rating_value(priority, days_until);
    if (rating >= 150.0f) return 1;
    if (rating >= 80.0f) return 2;
    if (rating >= 40.0f) return 3;
    return 7;
}


bool should_notify_today(int priority, int days_until, int days_since_last_notify) {
    int freq = get_notification_frequency(priority, days_until);
    return days_since_last_notify >= freq;
}


PYBIND11_MODULE(planner_algorithm, m) {
    m.doc() = "Planner algorithm for task rating and notification management";

    m.def("compute_rating_value", &compute_rating_value,
        "Calculate task rating based on priority and days until deadline",
        py::arg("priority"), py::arg("days_until"));

    m.def("is_more_urgent", &is_more_urgent,
        "Compare two tasks by urgency",
        py::arg("priority1"), py::arg("days1"), py::arg("priority2"), py::arg("days2"));

    m.def("get_urgency_level", &get_urgency_level,
        "Get urgency level as string",
        py::arg("priority"), py::arg("days_until"));

    m.def("get_notification_frequency", &get_notification_frequency,
        "Get recommended notification frequency in days",
        py::arg("priority"), py::arg("days_until"));

    m.def("should_notify_today", &should_notify_today,
        "Check if notification should be sent today",
        py::arg("priority"), py::arg("days_until"), py::arg("days_since_last_notify"));
}
