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

PYBIND11_MODULE(planner_algorithm, m) {
    m.doc() = "Planner algorithm for task rating calculation";
    m.def("compute_rating_value", &compute_rating_value,
        "Calculate task rating based on priority and days until deadline",
        py::arg("priority"), py::arg("days_until"));
}
