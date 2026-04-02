#include "alarm/alarm_service.h"

#include <iostream>
#include <string>

int main() {
    AlarmService service;

    AlarmInput input;
    std::cin >> input.lesson_time
        >> input.travel_minutes
        >> input.prep_minutes
        >> input.buffer_minutes
        >> input.use_weather
        >> input.weather_multiplier
        >> input.round_to_five;

    AlarmResult result = service.calculate(input);

    std::cout << "Lesson time: " << result.lesson_time
        << "\nAlarm time: " << result.alarm_time
        << "\nLeave time: " << result.leave_time
        << "\nTravel time: " << result.final_travel_minutes
        << "\nComment: " << result.comment;

    return 0;
}