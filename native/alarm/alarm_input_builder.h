#pragma once

#include "alarm_input.h"
#include "../domain/event_data.h"
#include "../domain/route_info.h"
#include "../domain/weather_info.h"
#include "../domain/user_preferences.h"

class AlarmInputBuilder {
public:
    AlarmInput build(
        const EventData& event,
        const RouteInfo& route,
        const WeatherInfo& weather,
        const UserPreferences& preferences
    ) const;
};