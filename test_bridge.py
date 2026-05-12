print("START")

from app.bridges.alarm_calculator_bridge import make_alarm

print("IMPORTED")

result = make_alarm(
    8,
    30,
    40,
    25
)

print("RESULT:")
print(result)

print("END")