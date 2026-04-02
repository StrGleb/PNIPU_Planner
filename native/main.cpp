#include "alarm/alarm_service.h"

#include <iostream>
#include <string>

int main() {
    AlarmService service;

    AlarmInput input;
    
    std::cout << "Enter the start time of the pair in HH:MM format: ";
    std::cin >> input.lesson_time;
        
    std::cout << "Enter travel time, fees, and extra time: ";
    std::cin >> input.travel_minutes
        >> input.prep_minutes
        >> input.buffer_minutes;

    std::cout << "Should I use a weather coefficient? (1 - yes, 0 - no) ";
    std::cin >> input.use_weather;

    if (input.use_weather) {
        std::cout << "Enter the coefficient of weather: ";
        std::cin >> input.weather_multiplier;
    }

    std::cout << "Use time rounding for alarm? (1 - yes, 0 - no) ";
    std::cin >> input.round_to_five;

    AlarmResult result = service.calculate(input);

    std::cout << "\nAlarm time: " << result.alarm_time 
        << "\nLeave time: " << result.leave_time
        << "\nTravel time: " << result.final_travel_minutes
        << "\nComment: " << result.comment;

    return 0;
}