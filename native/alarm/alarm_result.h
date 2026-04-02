#pragma once

#include <string>

struct AlarmResult {
    std::string lesson_time;
    int final_travel_minutes;
    int prep_minutes;
    int buffer_minutes;
    std::string leave_time;
    std::string alarm_time;

    bool weather_applied;
    double weather_multiplier;
    std::string comment;
};