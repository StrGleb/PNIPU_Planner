#include "alarm/alarm_service.h"

#include <iostream>
#include <string>

void run_manual_mode() {
    AlarmService service;
    AlarmInput input;

    std::cout << "Enter lesson time (HH:MM): ";
    std::cin >> input.lesson_time;

    std::cout << "Enter travel minutes: ";
    std::cin >> input.travel_minutes;

    std::cout << "Enter prep minutes: ";
    std::cin >> input.prep_minutes;

    std::cout << "Enter buffer minutes: ";
    std::cin >> input.buffer_minutes;

    std::cout << "Use weather coefficient? (1 - yes, 0 - no): ";
    std::cin >> input.use_weather;

    if (input.use_weather) {
        std::cout << "Enter weather coefficient: ";
        std::cin >> input.weather_multiplier;
    }

    std::cout << "Round alarm time to 5 minutes? (1 - yes, 0 - no): ";
    std::cin >> input.round_to_five;

    AlarmResult result = service.calculate(input);

    std::cout << "\nAlarm time: " << result.alarm_time
        << "\nLeave time: " << result.leave_time
        << "\nTravel time: " << result.final_travel_minutes
        << "\nComment: " << result.comment;
}

void run_strict_mode() {
    AlarmService service;
    AlarmInput input;

    std::cin >> input.lesson_time
        >> input.travel_minutes
        >> input.prep_minutes
        >> input.buffer_minutes
        >> input.use_weather;

    if (input.use_weather)
        std::cin >> input.weather_multiplier;
    else input.weather_multiplier = 1;

    std::cin >> input.round_to_five;

    AlarmResult result = service.calculate(input);

    std::cout << result.alarm_time << '\n'
              << result.leave_time << '\n'
              << result.final_travel_minutes << '\n'
              << result.comment << '\n';
}

int main(int argc, char* argv[]) {
    try {
        if (argc > 1 && std::string(argv[1]) == "--strict")
            run_strict_mode();
        else
            run_manual_mode();
    }

    catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << '\n';
        return 1;
    }

    return 0;
}