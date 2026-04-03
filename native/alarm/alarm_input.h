#pragma once

#include <string>

struct AlarmInput {
    std::string event_time;
    int travel_minutes;
    int prep_minutes;
    int buffer_minutes;

    bool use_weather = false;
    double weather_multiplier = 1.0;
    bool round_to_five;
};