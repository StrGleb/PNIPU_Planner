#pragma once

#include <string>

struct AlarmInput {
    std::string lesson_time;
    int travel_minutes;
    int prep_minutes;
    int buffer_minutes;

    bool use_weather = 0;
    double weather_multiplier = 1;
    bool round_to_five;
};