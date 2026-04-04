#include "alarm_input_builder.h"

AlarmInput AlarmInputBuilder::build(
    const EventData& event,
    const RouteInfo& route,
    const WeatherInfo& weather,
    const UserPreferences& preferences
) const {
    AlarmInput input;

    input.event_time = event.event_time;
    input.travel_minutes = route.travel_minutes;
    input.prep_minutes = preferences.prep_minutes;
    input.buffer_minutes = preferences.buffer_minutes;
    input.use_weather = weather.use_weather;
    input.weather_multiplier = weather.weather_multiplier;
    input.round_to_five = preferences.round_to_five;

    return input;
}