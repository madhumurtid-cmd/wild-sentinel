import math
import random

# ---------------------------------------------------------
# WILD SENTINEL V0.1
# Simple wildlife movement + human safety simulator
# ---------------------------------------------------------

# Village / school
SCHOOL = (100, 100)

# A person starts here
HOUSE = (0, 0)

# Simulated leopard starts somewhere in the forest
LEOPARD = (25, 70)

# Walking route from house to school
ROUTE = [
    (0, 0),
    (20, 15),
    (40, 30),
    (60, 50),
    (80, 75),
    (100, 100),
]

# Sensor locations
SENSORS = [
    (25, 40),
    (50, 60),
    (75, 80),
]


def distance(a, b):
    """Distance between two points."""
    return math.sqrt(
        (a[0] - b[0]) ** 2 +
        (a[1] - b[1]) ** 2
    )


def move_towards(position, target, step=5):
    """Move an animal a small distance toward a target."""
    dx = target[0] - position[0]
    dy = target[1] - position[1]

    d = math.sqrt(dx * dx + dy * dy)

    if d == 0:
        return position

    return (
        position[0] + (dx / d) * step,
        position[1] + (dy / d) * step,
    )


def sensor_detection(animal_position, sensor_position):
    """
    Simulate a crude sensor.

    Detection becomes more likely when the animal
    gets closer to the sensor.
    """

    d = distance(animal_position, sensor_position)

    if d < 10:
        probability = 0.90
    elif d < 20:
        probability = 0.60
    elif d < 30:
        probability = 0.25
    else:
        probability = 0.05

    return random.random() < probability


def calculate_risk(animal_position):
    """
    Basic risk calculation.

    Later this becomes our real prediction model.
    """

    route_distance = min(
        distance(animal_position, point)
        for point in ROUTE
    )

    school_distance = distance(animal_position, SCHOOL)

    if route_distance < 15:
        return "DANGER"

    if route_distance < 30 or school_distance < 40:
        return "CAUTION"

    return "SAFE"


def main():

    leopard = LEOPARD

    print("\n===================================")
    print("       WILD SENTINEL V0.1")
    print("===================================\n")

    for minute in range(0, 61, 5):

        # Leopard moves toward the village/school
        leopard = move_towards(
            leopard,
            SCHOOL,
            step=7
        )

        detections = []

        for i, sensor in enumerate(SENSORS, start=1):

            if sensor_detection(leopard, sensor):
                detections.append(i)

        risk = calculate_risk(leopard)

        print(
            f"Time: {minute:02d} min | "
            f"Leopard: ({leopard[0]:.1f}, {leopard[1]:.1f}) | "
            f"Sensors: {detections or 'none'} | "
            f"STATUS: {risk}"
        )

    print("\nSimulation complete.")


if __name__ == "__main__":
    main()