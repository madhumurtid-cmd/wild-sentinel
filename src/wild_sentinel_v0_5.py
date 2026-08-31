import math


# =========================================================
# WILD SENTINEL V0.5
# PROBABILISTIC HUMAN/WILDLIFE ENGINE
#
# RESEARCH SIMULATION ONLY
#
# Core question:
#
#   Can we predict a dangerous HUMAN/WILDLIFE
#   time-and-location overlap even when sensors
#   temporarily cannot see the animal?
#
# =========================================================


# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------

ROUTES = {

    # Route A avoids the main wildlife corridor.
    "A": [
        (0, 0),
        (20, 5),
        (40, 15),
        (60, 30),
        (80, 60),
        (100, 100),
    ],

    # Route B deliberately crosses the wildlife corridor.
    "B": [
        (0, 0),
        (20, 20),
        (40, 40),
        (50, 50),
        (60, 60),
        (80, 80),
        (100, 100),
    ],

    # Route C is an alternative.
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
# SENSOR NETWORK
# ---------------------------------------------------------

SENSORS = {
    1: (35, 65),
    2: (50, 50),
    3: (65, 35),
}


# ---------------------------------------------------------
# WILDLIFE
# ---------------------------------------------------------

LEOPARD_START = (15.0, 85.0)
LEOPARD_END = (85.0, 15.0)

LEOPARD_SPEED = 2.05


# ---------------------------------------------------------
# HUMAN
# ---------------------------------------------------------

HUMAN_DEPARTURE = 10
HUMAN_SPEED = 5.0


# ---------------------------------------------------------
# SIMULATION
# ---------------------------------------------------------

TIME_STEP = 5
TOTAL_TIME = 45


# ---------------------------------------------------------
# SENSOR BLACKOUT
# ---------------------------------------------------------

BLIND_START = 20
BLIND_END = 35


# ---------------------------------------------------------
# PREDICTION PARAMETERS
# ---------------------------------------------------------

ENCOUNTER_RADIUS = 10.0

FORECAST_HORIZON = 15

INITIAL_UNCERTAINTY = 5.0

UNCERTAINTY_GROWTH = 2.5

MAX_UNCERTAINTY = 35.0


# ---------------------------------------------------------
# GEOMETRY
# ---------------------------------------------------------

def distance(a, b):

    return math.hypot(
        a[0] - b[0],
        a[1] - b[1]
    )


def interpolate(a, b, fraction):

    return (
        a[0] + (b[0] - a[0]) * fraction,
        a[1] + (b[1] - a[1]) * fraction
    )


# ---------------------------------------------------------
# LEOPARD ACTUAL POSITION
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

    fraction = min(
        travelled / total_distance,
        1.0
    )

    return interpolate(
        LEOPARD_START,
        LEOPARD_END,
        fraction
    )


# ---------------------------------------------------------
# HUMAN POSITION
# ---------------------------------------------------------

def human_position(route, elapsed_minutes):

    if elapsed_minutes <= 0:

        return route[0]


    remaining_distance = (
        HUMAN_SPEED
        * elapsed_minutes
    )


    for i in range(len(route) - 1):

        start = route[i]

        end = route[i + 1]

        segment_length = distance(
            start,
            end
        )


        if remaining_distance <= segment_length:

            fraction = (
                remaining_distance
                / segment_length
            )

            return interpolate(
                start,
                end,
                fraction
            )


        remaining_distance -= segment_length


    return route[-1]


# ---------------------------------------------------------
# SENSOR DETECTION
# ---------------------------------------------------------

def detect_leopard(
    leopard_position_value,
    sensor_position
):

    detection_radius = 18.0

    return (
        distance(
            leopard_position_value,
            sensor_position
        )
        <= detection_radius
    )


# ---------------------------------------------------------
# PREDICT FUTURE LEOPARD POSITION
# ---------------------------------------------------------

def predict_leopard(
    last_position,
    last_observation,
    future_time
):

    if last_position is None:

        return None


    dx = (
        LEOPARD_END[0]
        - LEOPARD_START[0]
    )

    dy = (
        LEOPARD_END[1]
        - LEOPARD_START[1]
    )


    length = math.hypot(
        dx,
        dy
    )


    vx = (
        dx
        / length
        * LEOPARD_SPEED
    )

    vy = (
        dy
        / length
        * LEOPARD_SPEED
    )


    elapsed = (
        future_time
        - last_observation
    )


    return (
        last_position[0]
        + vx * elapsed,

        last_position[1]
        + vy * elapsed
    )


# ---------------------------------------------------------
# DISTANCE → PROBABILITY
# ---------------------------------------------------------

def distance_probability(
    separation,
    uncertainty
):

    effective_radius = (
        ENCOUNTER_RADIUS
        + uncertainty
    )


    if separation >= effective_radius:

        return 0.0


    probability = (
        1.0
        - (
            separation
            / effective_radius
        )
    )


    return max(
        0.0,
        min(
            1.0,
            probability
        )
    )


# ---------------------------------------------------------
# ROUTE ENCOUNTER PROBABILITY
# ---------------------------------------------------------

def route_encounter_probability(
    route,
    current_time,
    last_position,
    last_observation,
    uncertainty
):

    # No observation means we have no basis for a
    # predictive wildlife trajectory.

    if (
        last_position is None
        or last_observation is None
    ):

        return (
            0.0,
            None,
            None
        )


    highest_probability = 0.0

    best_time = None

    best_distance = None


    for offset in range(
        1,
        FORECAST_HORIZON + 1
    ):

        future_time = (
            current_time
            + offset
        )


        # Person must have departed.

        if future_time < HUMAN_DEPARTURE:

            continue


        human_elapsed = (
            future_time
            - HUMAN_DEPARTURE
        )


        human = human_position(
            route,
            human_elapsed
        )


        animal = predict_leopard(
            last_position,
            last_observation,
            future_time
        )


        if animal is None:

            continue


        separation = distance(
            animal,
            human
        )


        probability = distance_probability(
            separation,
            uncertainty
        )


        if probability > highest_probability:

            highest_probability = probability

            best_time = future_time

            best_distance = separation


    # -----------------------------------------------------
    # IMPORTANT:
    #
    # Always return the same three values.
    # -----------------------------------------------------

    return (
        highest_probability,
        best_time,
        best_distance
    )


# ---------------------------------------------------------
# RISK CLASSIFICATION
# ---------------------------------------------------------

def risk_status(probability):

    if probability >= 0.70:

        return "DANGER"

    elif probability >= 0.40:

        return "CAUTION"

    elif probability >= 0.15:

        return "LOW RISK"

    else:

        return "SAFE"


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    last_position = None

    last_observation = None

    uncertainty = MAX_UNCERTAINTY


    print()

    print(
        "======================================================"
    )

    print(
        "             WILD SENTINEL V0.5"
    )

    print(
        "     PROBABILISTIC HUMAN/WILDLIFE ENGINE"
    )

    print(
        "======================================================"
    )

    print()

    print(
        "Question:"
    )

    print(
        "Can Wild Sentinel predict a dangerous encounter"
    )

    print(
        "when the leopard disappears from the sensors?"
    )

    print()

    print(
        f"Mother departure: "
        f"{HUMAN_DEPARTURE} minutes"
    )

    print(
        f"Leopard: "
        f"{LEOPARD_START}"
        f" -> "
        f"{LEOPARD_END}"
    )

    print(
        f"Sensor blind period: "
        f"{BLIND_START}-{BLIND_END}"
    )

    print()

    print(
        "------------------------------------------------------"
    )


    # -----------------------------------------------------
    # TIME LOOP
    # -----------------------------------------------------

    for minute in range(
        0,
        TOTAL_TIME + 1,
        TIME_STEP
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


        # -------------------------------------------------
        # SENSOR OBSERVATION
        # -------------------------------------------------

        if not blind:

            for sensor_id, sensor in SENSORS.items():

                if detect_leopard(
                    actual_leopard,
                    sensor
                ):

                    detections.append(
                        sensor_id
                    )


        # -------------------------------------------------
        # UPDATE MODEL
        # -------------------------------------------------

        if detections:

            last_position = actual_leopard

            last_observation = minute

            uncertainty = INITIAL_UNCERTAINTY

        elif last_observation is not None:

            minutes_since_observation = (
                minute
                - last_observation
            )

            uncertainty = min(
                MAX_UNCERTAINTY,

                INITIAL_UNCERTAINTY
                +
                (
                    minutes_since_observation
                    * UNCERTAINTY_GROWTH
                )
            )


        # -------------------------------------------------
        # DISPLAY
        # -------------------------------------------------

        print()

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
            f"  Last observation: "
            f"{last_observation}"
        )

        print(
            f"  Wildlife uncertainty: "
            f"{uncertainty:4.1f}"
        )

        print()


        # -------------------------------------------------
        # CALCULATE ROUTE RISKS
        # -------------------------------------------------

        results = {}


        for route_name, route in ROUTES.items():

            (
                probability,
                best_time,
                best_distance
            ) = route_encounter_probability(

                route,

                minute,

                last_position,

                last_observation,

                uncertainty
            )


            results[route_name] = {
                "probability": probability,
                "time": best_time,
                "distance": best_distance
            }


            print(
                f"  ROUTE {route_name}: "
                f"{probability * 100:5.1f}% "
                f"{risk_status(probability)}"
            )


        # -------------------------------------------------
        # SAFEST ROUTE
        # -------------------------------------------------

        safest = min(
            results,
            key=lambda route:
            results[route]["probability"]
        )


        most_dangerous = max(
            results,
            key=lambda route:
            results[route]["probability"]
        )


        dangerous_probability = results[
            most_dangerous
        ]["probability"]


        print()


        # -------------------------------------------------
        # WARNING
        # -------------------------------------------------

        if dangerous_probability >= 0.70:

            print(
                "  🚨 WILDLIFE WARNING"
            )

            print(
                f"  Avoid ROUTE "
                f"{most_dangerous}"
            )


            overlap_time = results[
                most_dangerous
            ]["time"]


            separation = results[
                most_dangerous
            ]["distance"]


            if overlap_time is not None:

                print(
                    f"  Predicted overlap: "
                    f"~{overlap_time} min"
                )

                print(
                    f"  Predicted separation: "
                    f"{separation:.1f}"
                )


        print()

        print(
            f"  >>> RECOMMENDED ROUTE: "
            f"{safest}"
        )


        print()

        print(
            "------------------------------------------------------"
        )


    # -----------------------------------------------------
    # COMPLETE
    # -----------------------------------------------------

    print()

    print(
        "======================================================"
    )

    print(
        "V0.5 TEST COMPLETE"
    )

    print(
        "======================================================"
    )

    print()

    print(
        "Success criterion:"
    )

    print(
        "The route containing the predicted wildlife"
    )

    print(
        "corridor should show elevated risk."
    )

    print()

    print(
        "During sensor blindness, the model should"
    )

    print(
        "continue using the last known movement."
    )

    print()

    print(
        "NOTE:"
    )

    print(
        "The percentages are simulation scores,"
    )

    print(
        "not real-world wildlife probabilities."
    )

    print()


if __name__ == "__main__":

    main()