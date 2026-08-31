import math

# =========================================================
# WILD SENTINEL V0.4b
#
# CONTROLLED WILDLIFE CROSSING TEST
#
# Purpose:
# Test whether the system can warn a human about a
# predicted wildlife encounter even after the animal
# disappears from the sensors.
#
# RESEARCH SIMULATION ONLY.
# NOT FOR REAL-WORLD SAFETY DECISIONS.
# =========================================================


# ---------------------------------------------------------
# MAP
# ---------------------------------------------------------

HOUSE = (0.0, 0.0)
SCHOOL = (100.0, 100.0)


# Three routes.
#
# Route B deliberately passes through the wildlife
# crossing zone.

ROUTES = {

    "A": [
        (0, 0),
        (20, 5),
        (40, 15),
        (60, 30),
        (80, 60),
        (100, 100),
    ],

    "B": [
        (0, 0),
        (20, 20),
        (40, 40),
        (60, 60),
        (80, 80),
        (100, 100),
    ],

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
# SENSOR LOCATIONS
# ---------------------------------------------------------

SENSORS = {

    1: (35, 35),
    2: (55, 55),
    3: (75, 75),
}


# ---------------------------------------------------------
# LEOPARD MOVEMENT
# ---------------------------------------------------------
#
# The leopard crosses Route B.
#
# We intentionally control the movement rather than using
# random wandering. This makes the experiment measurable.
#
# Starting position:
#
#       🐆
#
#       ↓
#
# Route B:  -----------------
#
# ---------------------------------------------------------

LEOPARD_START = (15.0, 85.0)

LEOPARD_END = (85.0, 15.0)

LEOPARD_SPEED = 5.0


# ---------------------------------------------------------
# HUMAN
# ---------------------------------------------------------

HUMAN_SPEED = 5.0


# ---------------------------------------------------------
# TIME
# ---------------------------------------------------------

INTERVAL = 5

TOTAL_MINUTES = 60

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
# ROUTE LENGTH
# ---------------------------------------------------------

def route_length(route):

    total = 0.0

    for i in range(len(route) - 1):

        total += distance(
            route[i],
            route[i + 1]
        )

    return total


# ---------------------------------------------------------
# HUMAN POSITION
# ---------------------------------------------------------

def human_position(
    route,
    minutes
):

    travel_distance = (
        HUMAN_SPEED * minutes
    )

    remaining = travel_distance

    for i in range(len(route) - 1):

        start = route[i]
        end = route[i + 1]

        segment_length = distance(
            start,
            end
        )

        if remaining <= segment_length:

            fraction = (
                remaining
                / segment_length
            )

            return interpolate(
                start,
                end,
                fraction
            )

        remaining -= segment_length

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
        1.0,
        fraction
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
        <= 22
    )


# ---------------------------------------------------------
# PREDICT LEOPARD
# ---------------------------------------------------------

def predict_leopard(
    last_position,
    last_minute,
    current_minute
):

    elapsed = (
        current_minute
        - last_minute
    )

    # The controlled leopard travels diagonally.
    #
    # Calculate its direction.

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

    return (

        last_position[0]
        + vx * elapsed,

        last_position[1]
        + vy * elapsed
    )


# ---------------------------------------------------------
# RISK SCORE
# ---------------------------------------------------------

def calculate_risk(
    route,
    leopard_position_now,
    last_observation,
    uncertainty
):

    if last_observation is None:

        return 0.0


    highest_risk = 0.0


    # Look ahead through the next 15 minutes.

    for future_minute in range(
        1,
        WARNING_HORIZON + 1
    ):

        animal = predict_leopard(

            leopard_position_now,

            last_observation[1],

            last_observation[1]
            + future_minute
        )


        human = human_position(

            route,

            future_minute
        )


        separation = distance(
            animal,
            human
        )


        # Strong risk when the two trajectories
        # come close at approximately the same time.

        if separation <= 5:

            score = 95

        elif separation <= 10:

            score = 75

        elif separation <= 15:

            score = 55

        elif separation <= 25:

            score = 30

        else:

            score = 5


        highest_risk = max(
            highest_risk,
            score
        )


    # Uncertainty increases the risk envelope.

    highest_risk += (
        uncertainty * 0.20
    )


    return min(
        100,
        highest_risk
    )


# ---------------------------------------------------------
# STATUS
# ---------------------------------------------------------

def status(score):

    if score >= 70:

        return "DANGER"

    if score >= 40:

        return "CAUTION"

    return "LOW RISK"


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    last_position = None

    last_observation_minute = None

    uncertainty = 10.0


    print()

    print(
        "======================================================"
    )

    print(
        "             WILD SENTINEL V0.4b"
    )

    print(
        "       CONTROLLED WILDLIFE CROSSING TEST"
    )

    print(
        "======================================================"
    )

    print()

    print(
        "🐆 Leopard trajectory:"
    )

    print(
        f"   {LEOPARD_START} → {LEOPARD_END}"
    )

    print()

    print(
        "👩 Human:"
    )

    print(
        "   HOUSE → SCHOOL"
    )

    print()

    print(
        "🚫 Sensor blind period:"
    )

    print(
        f"   {BLIND_START}-{BLIND_END} minutes"
    )

    print()

    print(
        "The test asks:"
    )

    print(
        "Can Wild Sentinel remember a threat after"
    )

    print(
        "the leopard disappears from the sensors?"
    )

    print()


    # -----------------------------------------------------
    # RUN SIMULATION
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
        # UPDATE KNOWLEDGE
        # -------------------------------------------------

        if detections:

            last_position = actual_leopard

            last_observation_minute = minute

            uncertainty = max(
                5,
                uncertainty - 5
            )

        else:

            uncertainty = min(
                50,
                uncertainty + 5
            )


        # -------------------------------------------------
        # PREDICTED CURRENT POSITION
        # -------------------------------------------------

        if (
            last_position is not None
            and last_observation_minute is not None
        ):

            predicted_now = predict_leopard(

                last_position,

                last_observation_minute,

                minute
            )

        else:

            predicted_now = actual_leopard


        observation = None

        if last_position is not None:

            observation = (

                last_position,

                last_observation_minute
            )


        # -------------------------------------------------
        # ROUTE RISK
        # -------------------------------------------------

        risks = {}


        for name, route in ROUTES.items():

            risks[name] = calculate_risk(

                route,

                predicted_now,

                observation,

                uncertainty
            )


        # -------------------------------------------------
        # SAFEST ROUTE
        # -------------------------------------------------

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
        # OUTPUT
        # -------------------------------------------------

        print(
            f"{minute:02d} min"
        )

        print(
            f"  Actual leopard: "
            f"({actual_leopard[0]:5.1f}, "
            f"{actual_leopard[1]:5.1f})"
        )

        print(
            f"  Sensors: "
            f"{detections if detections else 'NONE'}"
        )

        print(
            f"  Last seen: "
            f"{last_observation_minute}"
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
        "Route B should become significantly more dangerous"
    )

    print(
        "than Routes A and C, including during the blind period."
    )

    print()


if __name__ == "__main__":

    main()