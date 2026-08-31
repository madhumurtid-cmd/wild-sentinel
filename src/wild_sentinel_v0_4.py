import math
import random

# =========================================================
# WILD SENTINEL V0.4
#
# Human + wildlife + time + route
# -> estimated encounter probability
# -> safest route
#
# RESEARCH SIMULATION ONLY.
# NOT FOR REAL-WORLD SAFETY DECISIONS.
# =========================================================


# ---------------------------------------------------------
# SCENARIO
# ---------------------------------------------------------

HOUSE = (0.0, 0.0)
SCHOOL = (100.0, 100.0)

HUMAN_SPEED = 5.0       # map units per minute
WARNING_HORIZON = 15    # minutes


# ---------------------------------------------------------
# THREE POSSIBLE ROUTES
# ---------------------------------------------------------

ROUTES = {

    "A": [
        (0, 0),
        (20, 10),
        (40, 25),
        (60, 45),
        (80, 70),
        (100, 100),
    ],

    "B": [
        (0, 0),
        (15, 25),
        (35, 45),
        (55, 60),
        (75, 80),
        (100, 100),
    ],

    "C": [
        (0, 0),
        (10, 40),
        (25, 60),
        (50, 75),
        (75, 90),
        (100, 100),
    ],
}


# ---------------------------------------------------------
# SENSOR NETWORK
# ---------------------------------------------------------

SENSORS = {

    1: (25, 40),
    2: (50, 60),
    3: (75, 80),
    4: (45, 85),
}


# ---------------------------------------------------------
# WILDLIFE
# ---------------------------------------------------------

LEOPARD_START = (20.0, 75.0)

LEOPARD_SPEED = 6.0

INTERVAL = 5

TOTAL_MINUTES = 60


# Deliberate sensor blind period.

BLIND_START = 20
BLIND_END = 35


# ---------------------------------------------------------
# GEOMETRY
# ---------------------------------------------------------

def distance(a, b):

    return math.hypot(
        a[0] - b[0],
        a[1] - b[1]
    )


def normalise(dx, dy):

    d = math.hypot(dx, dy)

    if d == 0:
        return 0, 0

    return dx / d, dy / d


def move(position, velocity):

    return (
        position[0] + velocity[0],
        position[1] + velocity[1]
    )


# ---------------------------------------------------------
# ROUTE LENGTH
# ---------------------------------------------------------

def route_length(route):

    total = 0

    for i in range(len(route) - 1):

        total += distance(
            route[i],
            route[i + 1]
        )

    return total


# ---------------------------------------------------------
# HUMAN TRAVEL TIME
# ---------------------------------------------------------

def human_travel_time(route):

    return route_length(route) / HUMAN_SPEED


# ---------------------------------------------------------
# SENSOR MODEL
# ---------------------------------------------------------

def sensor_detects(
    animal_position,
    sensor_position,
    blind=False
):

    if blind:
        return False

    d = distance(
        animal_position,
        sensor_position
    )

    if d < 12:
        probability = 0.90

    elif d < 22:
        probability = 0.60

    elif d < 32:
        probability = 0.25

    else:
        probability = 0.03

    return random.random() < probability


# ---------------------------------------------------------
# PREDICT ANIMAL POSITION
# ---------------------------------------------------------

def predict_animal_position(
    last_position,
    velocity,
    minutes_ahead
):

    return (

        last_position[0]
        + velocity[0]
        * minutes_ahead,

        last_position[1]
        + velocity[1]
        * minutes_ahead
    )


# ---------------------------------------------------------
# FIND CLOSEST POINT ON ROUTE
# ---------------------------------------------------------

def closest_route_distance(
    animal_position,
    route
):

    return min(

        distance(
            animal_position,
            point
        )

        for point in route
    )


# ---------------------------------------------------------
# HUMAN POSITION ALONG ROUTE
# ---------------------------------------------------------

def human_position_after(
    route,
    minutes
):

    remaining_distance = (
        HUMAN_SPEED * minutes
    )

    for i in range(len(route) - 1):

        start = route[i]
        end = route[i + 1]

        segment = distance(
            start,
            end
        )

        if remaining_distance <= segment:

            ratio = (
                remaining_distance
                / segment
            )

            return (

                start[0]
                + (end[0] - start[0])
                * ratio,

                start[1]
                + (end[1] - start[1])
                * ratio
            )

        remaining_distance -= segment

    return route[-1]


# ---------------------------------------------------------
# ENCOUNTER PROBABILITY
# ---------------------------------------------------------

def encounter_probability(
    route,
    animal_position,
    velocity,
    uncertainty
):

    probability = 0.0

    # Examine the next 15 minutes.

    for minute in range(
        1,
        WARNING_HORIZON + 1
    ):

        animal = predict_animal_position(
            animal_position,
            velocity,
            minute
        )

        human = human_position_after(
            route,
            minute
        )

        separation = distance(
            animal,
            human
        )

        # Smaller separation = greater potential
        # encounter probability.

        if separation < 8:

            probability += 0.30

        elif separation < 15:

            probability += 0.15

        elif separation < 25:

            probability += 0.05


    # Uncertainty adjustment.

    probability += (
        uncertainty * 0.003
    )


    # Cap at 100%.

    probability = min(
        probability,
        1.0
    )


    return probability


# ---------------------------------------------------------
# STATUS
# ---------------------------------------------------------

def status(probability):

    percentage = probability * 100

    if percentage >= 60:

        return "DANGER"

    elif percentage >= 30:

        return "CAUTION"

    else:

        return "LOW RISK"


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    random.seed(20)


    leopard = LEOPARD_START


    # Initial direction toward school.

    dx = SCHOOL[0] - leopard[0]

    dy = SCHOOL[1] - leopard[1]

    nx, ny = normalise(
        dx,
        dy
    )


    velocity = (
        nx * LEOPARD_SPEED,
        ny * LEOPARD_SPEED
    )


    last_known_position = None

    previous_observation = None

    last_observation = None

    uncertainty = 10


    print()

    print(
        "======================================================"
    )

    print(
        "              WILD SENTINEL V0.4"
    )

    print(
        "          HUMAN-ANIMAL SAFETY ENGINE"
    )

    print(
        "======================================================"
    )

    print()

    print(
        "Scenario:"
    )

    print(
        "Mother leaves HOUSE and walks to SCHOOL."
    )

    print(
        "Three possible routes are available."
    )

    print(
        "A leopard is moving through dense vegetation."
    )

    print()

    print(
        "The system estimates:"
    )

    print(
        "  • wildlife movement"
    )

    print(
        "  • human movement"
    )

    print(
        "  • time overlap"
    )

    print(
        "  • encounter probability"
    )

    print()


    # -----------------------------------------------------
    # SIMULATION
    # -----------------------------------------------------

    for minute in range(
        0,
        TOTAL_MINUTES + 1,
        INTERVAL
    ):


        # -----------------------------------------------
        # Slightly unpredictable animal movement.
        # -----------------------------------------------

        angle = random.uniform(
            -0.15,
            0.15
        )

        cos_a = math.cos(angle)

        sin_a = math.sin(angle)

        vx, vy = velocity

        new_vx = (
            vx * cos_a
            - vy * sin_a
        )

        new_vy = (
            vx * sin_a
            + vy * cos_a
        )

        speed = math.hypot(
            new_vx,
            new_vy
        )

        if speed > 0:

            velocity = (
                new_vx / speed
                * LEOPARD_SPEED,

                new_vy / speed
                * LEOPARD_SPEED
            )


        # Move leopard.

        leopard = move(
            leopard,
            velocity
        )


        # -----------------------------------------------
        # Sensor observations
        # -----------------------------------------------

        blind = (
            BLIND_START
            <= minute
            <= BLIND_END
        )


        detections = []


        for sensor_id, sensor in SENSORS.items():

            if sensor_detects(
                leopard,
                sensor,
                blind
            ):

                detections.append(
                    sensor_id
                )


        # -----------------------------------------------
        # Update knowledge
        # -----------------------------------------------

        if detections:

            current = leopard


            if previous_observation is not None:

                velocity = (

                    current[0]
                    - previous_observation[0],

                    current[1]
                    - previous_observation[1]
                )


            previous_observation = current

            last_known_position = current

            last_observation = minute


            uncertainty = max(
                5,
                uncertainty - 6
            )


        else:

            uncertainty = min(
                50,
                uncertainty + 5
            )


        # -----------------------------------------------
        # Prediction
        # -----------------------------------------------

        if (
            last_known_position is not None
            and last_observation is not None
        ):

            elapsed = (
                minute
                - last_observation
            )


            predicted_animal = (
                last_known_position[0]
                + velocity[0]
                * elapsed
                / INTERVAL,

                last_known_position[1]
                + velocity[1]
                * elapsed
                / INTERVAL
            )

        else:

            predicted_animal = leopard


        # -----------------------------------------------
        # ROUTE ANALYSIS
        # -----------------------------------------------

        probabilities = {}


        for route_name, route in ROUTES.items():

            probabilities[route_name] = (
                encounter_probability(

                    route,

                    predicted_animal,

                    velocity,

                    uncertainty
                )
            )


        safest = min(
            probabilities,
            key=probabilities.get
        )


        # -----------------------------------------------
        # OUTPUT
        # -----------------------------------------------

        print(
            f"{minute:02d} min"
        )

        print(
            f"  Wildlife observed: "
            f"{'YES' if detections else 'NO'}"
        )

        print(
            f"  Last observation: "
            f"{last_observation}"
        )

        print(
            f"  Uncertainty: "
            f"{uncertainty:.1f}"
        )

        print()


        for route_name in (
            "A",
            "B",
            "C"
        ):

            p = probabilities[
                route_name
            ]

            print(
                f"  ROUTE {route_name}: "
                f"{p * 100:5.1f}% "
                f"{status(p)}"
            )


        print()

        print(
            f"  >>> RECOMMENDED ROUTE: "
            f"{safest}"
        )


        dangerous = [

            r

            for r, p in probabilities.items()

            if p >= 0.60
        ]


        if dangerous:

            print()

            print(
                "  🚨 WILDLIFE WARNING"
            )

            print(
                "  Avoid:",
                ", ".join(dangerous)
            )


        print()
        print(
            "------------------------------------------------------"
        )


    print()

    print(
        "======================================================"
    )

    print(
        "SIMULATION COMPLETE"
    )

    print(
        "======================================================"
    )

    print()

    print(
        "The key output is NOT the animal's exact location."
    )

    print(
        "The key output is the safest human route."
    )

    print()


if __name__ == "__main__":

    main()