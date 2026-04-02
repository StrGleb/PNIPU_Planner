#pragma once

#include <string>

struct AlarmInput {
    std::string lesson_time;
    int travel_minutes;
    int prep_minutes;
    int buffer_minutes; // запасное время

    bool use_weather;
    double weather_multiplier;
    bool round_to_five; // округление времени
};