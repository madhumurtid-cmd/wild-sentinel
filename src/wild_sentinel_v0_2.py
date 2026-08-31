import math
import random

# =========================================================
# WILD SENTINEL V0.2
# Predictive wildlife movement from sparse observations
# =========================================================

SCHOOL = (100.0, 100.0)

ROUTE = [
    (0, 0),
    (20, 15),
    (40, 30),
    (60, 50),
    (80, 75),
    (100, 100),
]

SENSORS = [
    (25.0, 40.0),
    (50.0, 60.0),
    (75.0, 80.0),
]

START = (25.0, 70.0)

STEP = 7.0
TOTAL_MINUTES = 60
INTERVAL = 5

# Deliberate "blind" period.
# During this time the sensors cannot see the leopard.
BLIND_START = 20
BLIND_END = 35


def distance(a, b):
    return math.hypot(
        a[0] - b[0],
        a[1] - b[1]
    )


def normalise(dx, dy):
    d = math.hypot(dx, dy)

    if d == 0:
        return 0.0, 0.0

    return dx / d, dy / d


def move(position, velocity):
    return (
        position[0] + velocity[0],
        position[1] + velocity[1]
    )


def sensor_detection(position, sensor, blind=False):

    if blind:
        return False

    d = distance(position, sensor)

    if d < 12:
        probability = 0.90

    elif d < 22:
        probability = 0.55

    elif d < 32:
        probability = 0.20

    else:
        probability = 0.03

    return random.random() < probability


def nearest_route_distance(position):

    return min(
        distance(position, point)
        for point in ROUTE
    )


def calculate_risk(predicted_position, uncertainty):

    route_distance = nearest_route_distance(
        predicted_position
    )

    school_distance = distance(
        predicted_position,
        SCHOOL
    )

    if uncertainty > 35:
        return "UNKNOWN"

    if route_distance < 15 or school_distance < 25:
        return "DANGER"

    if route_distance < 30 or school_distance < 45:
        return "CAUTION"

    return "SAFE"


def predict_position(
    last_position,
    velocity,
    minutes_ahead
):

    return (
        last_position[0]
        + velocity[0] * minutes_ahead / INTERVAL,

        last_position[1]
        + velocity[1] * minutes_ahead / INTERVAL
    )


def main():

    random.seed(7)

    leopard = START

    # Initial direction toward the school.
    dx = SCHOOL[0] - leopard[0]
    dy = SCHOOL[1] - leopard[1]

    nx, ny = normalise(dx, dy)

    velocity = (
        nx * STEP,
        ny * STEP
    )

    last_observation = None
    previous_observation = None

    uncertainty = 8.0

    print()
    print("==============================================")
    print("           WILD SENTINEL V0.2")
    print("      PREDICTIVE WILDLIFE WARNING")
    print("==============================================")
    print()
    print("Species: LEOPARD")
    print("Simulation: sparse sensors + hidden animal")
    print(
        f"Blind period: {BLIND_START}-{BLIND_END} minutes"
    )
    print()

    for minute in range(
        0,
        TOTAL_MINUTES + 1,
        INTERVAL
    ):

        # -------------------------------------------------
        # Make movement slightly unpredictable.
        # -------------------------------------------------

        angle_change = random.uniform(
            -0.12,
            0.12
        )

        cos_a = math.cos(angle_change)
        sin_a = math.sin(angle_change)

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
                new_vx / speed * STEP,
                new_vy / speed * STEP
            )

        # Move the simulated leopard.
        leopard = move(
            leopard,
            velocity
        )

        # -------------------------------------------------
        # Sensor visibility
        # -------------------------------------------------

        blind = (
            BLIND_START
            <= minute
            <= BLIND_END
        )

        detections = []

        for i, sensor in enumerate(
            SENSORS,
            start=1
        ):

            detected = sensor_detection(
                leopard,
                sensor,
                blind
            )

            if detected:
                detections.append(i)

        # -------------------------------------------------
        # Update our knowledge of the animal.
        # -------------------------------------------------

        if detections:

            current_observation = leopard

            if previous_observation is not None:

                dx = (
                    current_observation[0]
                    - previous_observation[0]
                )

                dy = (
                    current_observation[1]
                    - previous_observation[1]
                )

                observed_speed = math.hypot(
                    dx,
                    dy
                )

                if observed_speed > 0:

                    velocity = (
                        dx,
                        dy
                    )

            previous_observation = (
                current_observation
            )

            last_observation = minute

            # Observation reduces uncertainty.
            uncertainty = max(
                5.0,
                uncertainty - 6.0
            )

        else:

            # No observation -> uncertainty grows.
            uncertainty = min(
                50.0,
                uncertainty + 5.0
            )

        # -------------------------------------------------
        # Prediction
        # -------------------------------------------------

        if (
            last_observation is not None
            and previous_observation is not None
        ):

            elapsed = (
                minute
                - last_observation
            )

            predicted = predict_position(
                previous_observation,
                velocity,
                elapsed
            )

        else:

            predicted = leopard

        # -------------------------------------------------
        # Risk assessment
        # -------------------------------------------------

        risk = calculate_risk(
            predicted,
            uncertainty
        )

        print(
            f"{minute:02d} min | "
            f"Observed: {str(bool(detections)):5s} | "
            f"Last seen: "
            f"{str(last_observation):>2s} | "
            f"Predicted: "
            f"({predicted[0]:5.1f}, "
            f"{predicted[1]:5.1f}) | "
            f"Uncertainty: "
            f"{uncertainty:4.1f} | "
            f"STATUS: {risk}"
        )

        # -------------------------------------------------
        # Forward prediction
        # -------------------------------------------------

        if minute in (
            15,
            25,
            35,
            45
        ):

            print(
                "   Forecast:",
                end=" "
            )

            for ahead in (
                5,
                10,
                15
            ):

                if previous_observation is not None:

                    forecast = predict_position(
                        previous_observation,
                        velocity,
                        ahead
                    )

                    print(
                        f"+{ahead}m "
                        f"({forecast[0]:.0f},"
                        f"{forecast[1]:.0f})",
                        end="  "
                    )

            print()

    print()
    print("==============================================")
    print("SIMULATION COMPLETE")
    print("==============================================")
    print()
    print(
        "During the blind period, the simulated "
        "sensors cannot see the leopard."
    )
    print(
        "Wild Sentinel attempts to maintain a "
        "prediction using its last known movement."
    )
    print()


if __name__ == "__main__":
    main()