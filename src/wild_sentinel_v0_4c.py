import math

# =========================================================
# WILD SENTINEL V0.4c
#
# CONTROLLED WILDLIFE CROSSING TEST
#
# Purpose:
# Test whether a wildlife movement prediction can identify
# a dangerous human/wildlife time overlap during a sensor
# blackout.
#
# RESEARCH SIMULATION ONLY.
# NOT FOR REAL-WORLD SAFETY DECISIONS.
# =========================================================


# ---------------------------------------------------------
# MAP
# ---------------------------------------------------------

HOUSE = (0.0, 0.0)
SCHOOL = (100.0, 100.0)


ROUTES = {

    # Route A avoids the central crossing.

    "A": [
        (0, 0),
        (20, 5),
        (40, 15),
        (60, 30),
        (80, 60),
        (100, 100),
    ],

    # Route B passes directly through the wildlife crossing.

    "B": [
        (0, 0),
        (20, 20),
        (40, 40),
        (50, 50),
        (60, 60),
        (80, 80),
        (100, 100),
    ],

    # Route C is another alternative.

    "C": [
        (0, 0),
        (5, 25),
        (10, 50),
        (30, 70),
        (60, 85),
        (100, 100),
    ],
}


# ---------------------------------------------------------
# SENSORS
# ---------------------------------------------------------

SENSORS = {

    1: (35, 65),
    2: (50, 50),
    3: (65, 35),
}


# ---------------------------------------------------------
# LEOPARD
# ---------------------------------------------------------
#
# The leopard moves diagonally toward (85,15).
#
# Its speed is deliberately chosen so that it reaches
# approximately (50,50) around the same time that a person
# travelling Route B reaches (50,50).
#
# This creates the controlled encounter experiment.
# ---------------------------------------------------------

LEOPARD_START = (15.0, 85.0)

LEOPARD_END = (85.0, 15.0)

LEOPARD_SPEED = 2.05


# ---------------------------------------------------------
# HUMAN
# ---------------------------------------------------------

HUMAN_SPEED = 5.0

HUMAN_START_TIME = 10


# ---------------------------------------------------------
# TIME
# ---------------------------------------------------------

INTERVAL = 5

TOTAL_MINUTES = 45

WARNING_HORIZON = 15


# ---------------------------------------------------------
# SENSOR BLIND PERIOD
# ---------------------------------------------------------

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


def interpolate(start, end, fraction):

    return (
        start[0]
        + (end[0] - start[0])
        * fraction,

        start[1]
        + (end[1] - start[1])
        * fraction
    )


# ---------------------------------------------------------
# HUMAN POSITION
# ---------------------------------------------------------

def human_position(route, elapsed_minutes):

    if elapsed_minutes <= 0:

        return route[0]


    remaining = (
        HUMAN_SPEED
        * elapsed_minutes
    )


    for i in range(len(route) - 1):

        start = route[i]

        end = route[i + 1]

        segment = distance(
            start,
            end
        )


        if remaining <= segment:

            ratio = (
                remaining
                / segment
            )

            return interpolate(
                start,
                end,
                ratio
            )


        remaining -= segment


    return route[-1]


# ---------------------------------------------------------
# LEOPARD POSITION
# ---------------------------------------------------------

def leopard_position(minute):

    total_distance = distance(
        LEOPARD_START,
        LEOPARD_END
    )


    travelled = (
        LEOPARD_SPEED
        * minute
    )


    fraction = (
        travelled
        / total_distance
    )


    fraction = min(
        fraction,
        1.0
    )


    return interpolate(
        LEOPARD_START,
        LEOPARD_END,
        fraction
    )


# ---------------------------------------------------------
# SENSOR
# ---------------------------------------------------------

def sensor_detects(
    leopard,
    sensor,
    blind
):

    if blind:

        return False


    return (
        distance(
            leopard,
            sensor
        )
        <= 18
    )


# ---------------------------------------------------------
# PREDICT LEOPARD
# ---------------------------------------------------------

def predict_leopard(
    last_position,
    last_minute,
    future_minute
):

    dx = (
        LEOPARD_END[0]
        - LEOPARD_START[0]
    )

    dy = (
        LEOPARD_END[1]
        - LEOPARD_START[1]
    )


    total = math.hypot(
        dx,
        dy
    )


    vx = (
        dx
        / total
        * LEOPARD_SPEED
    )


    vy = (
        dy
        / total
        * LEOPARD_SPEED
    )


    elapsed = (
        future_minute
        - last_minute
    )


    return (

        last_position[0]
        + vx * elapsed,

        last_position[1]
        + vy * elapsed
    )


# ---------------------------------------------------------
# ROUTE RISK
# ---------------------------------------------------------

def route_risk(
    route,
    last_position,
    last_observation_minute,
    current_minute,
    uncertainty
):

    if last_position is None:

        return 0.0


    highest_risk = 0.0


    # Look ahead from NOW.

    for offset in range(
        1,
        WARNING_HORIZON + 1
    ):

        future_minute = (
            current_minute
            + offset
        )


        # Person has not left yet.

        if future_minute < HUMAN_START_TIME:

            continue


        # Position of person at that future time.

        human_elapsed = (
            future_minute
            - HUMAN_START_TIME
        )


        human = human_position(
            route,
            human_elapsed
        )


        # Predicted wildlife position at exactly the
        # same future time.

        animal = predict_leopard(
            last_position,
            last_observation_minute,
            future_minute
        )


        separation = distance(
            animal,
            human
        )


        # -------------------------------------------------
        # Encounter scoring
        # -------------------------------------------------

        if separation <= 5:

            score = 95

        elif separation <= 10:

            score = 80

        elif separation <= 15:

            score = 60

        elif separation <= 25:

            score = 30

        else:

            score = 5


        highest_risk = max(
            highest_risk,
            score
        )


    # Uncertainty expands the danger envelope.

    highest_risk += (
        uncertainty * 0.20
    )


    return min(
        highest_risk,
        100
    )


# ---------------------------------------------------------
# STATUS
# ---------------------------------------------------------

def status(score):

    if score >= 70:

        return "DANGER"

    elif score >= 40:

        return "CAUTION"

    else:

        return "LOW RISK"


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    last_position = None

    last_observation = None

    uncertainty = 15.0


    print()

    print(
        "======================================================"
    )

    print(
        "             WILD SENTINEL V0.4c"
    )

    print(
        "       HUMAN/WILDLIFE TIME-OVERLAP TEST"
    )

    print(
        "======================================================"
    )

    print()

    print(
        f"Mother departure: {HUMAN_START_TIME} minutes"
    )

    print(
        f"Leopard: {LEOPARD_START} -> {LEOPARD_END}"
    )

    print(
        f"Leopard speed: {LEOPARD_SPEED}"
    )

    print(
        f"Sensor blind period: "
        f"{BLIND_START}-{BLIND_END}"
    )

    print()

    print(
        "CONTROLLED TEST:"
    )

    print(
        "Route B contains the wildlife crossing."
    )

    print(
        "The leopard should reach that crossing"
    )

    print(
        "at approximately the same time as the mother."
    )

    print()

    print(
        "During the blind period, the animal is invisible"
    )

    print(
        "to the simulated sensors."
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

        actual_leopard = leopard_position(
            minute
        )


        blind = (
            BLIND_START
            <= minute
            <= BLIND_END
        )


        detections = []


        for sensor_id, sensor in SENSORS.items():

            if sensor_detects(
                actual_leopard,
                sensor,
                blind
            ):

                detections.append(
                    sensor_id
                )


        # -------------------------------------------------
        # Update sensor knowledge
        # -------------------------------------------------

        if detections:

            last_position = actual_leopard

            last_observation = minute

            uncertainty = max(
                5.0,
                uncertainty - 6.0
            )

        else:

            uncertainty = min(
                50.0,
                uncertainty + 5.0
            )


        # -------------------------------------------------
        # Human position on Route B
        # -------------------------------------------------

        if minute >= HUMAN_START_TIME:

            human = human_position(

                ROUTES["B"],

                minute
                - HUMAN_START_TIME
            )

        else:

            human = HOUSE


        # -------------------------------------------------
        # Route risks
        # -------------------------------------------------

        risks = {}


        for name, route in ROUTES.items():

            risks[name] = route_risk(

                route,

                last_position,

                last_observation,

                minute,

                uncertainty
            )


        safest = min(
            risks,
            key=risks.get
        )


        dangerous = [

            name

            for name, score
            in risks.items()

            if score >= 70
        ]


        # -------------------------------------------------
        # Output
        # -------------------------------------------------

        print(
            f"{minute:02d} min"
        )

        print(
            f"  Leopard actual: "
            f"({actual_leopard[0]:5.1f}, "
            f"{actual_leopard[1]:5.1f})"
        )

        print(
            f"  Mother Route B: "
            f"({human[0]:5.1f}, "
            f"{human[1]:5.1f})"
        )

        print(
            f"  Sensors: "
            f"{detections if detections else 'NONE'}"
        )

        print(
            f"  Last seen: "
            f"{last_observation}"
        )

        print(
            f"  Uncertainty: "
            f"{uncertainty:.1f}"
        )

        print()


        for name in (
            "A",
            "B",
            "C"
        ):

            score = risks[name]

            print(
                f"  Route {name}: "
                f"{score:5.1f}/100 "
                f"{status(score)}"
            )


        print()


        if len(dangerous) == 3:

            print(
                "  🚨 NO SAFE ROUTE — WAIT"
            )

        else:

            print(
                f"  >>> RECOMMENDED: "
                f"ROUTE {safest}"
            )


        if "B" in dangerous:

            print()

            print(
                "  🚨 WILDLIFE WARNING — ROUTE B"
            )

            print(
                "  Predicted human/wildlife "
                "time-overlap."
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
        "CONTROLLED TEST COMPLETE"
    )

    print(
        "======================================================"
    )

    print()

    print(
        "Success criterion:"
    )

    print(
        "Route B should become substantially more risky"
    )

    print(
        "than A/C around the predicted crossing."
    )

    print()

    print(
        "Most important:"
    )

    print(
        "The warning should continue during sensor blindness."
    )

    print()


if __name__ == "__main__":

    main()