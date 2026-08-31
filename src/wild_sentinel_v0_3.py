import math
import random

# =========================================================
# WILD SENTINEL V0.3
#
# Question:
# "Which route is safest for a person travelling
#  through a wildlife-conflict area?"
#
# IMPORTANT:
# This is a simulation/research prototype.
# It must NOT be used for real-world safety decisions.
# =========================================================


# ---------------------------------------------------------
# VILLAGE
# ---------------------------------------------------------

HOUSE = (0, 0)
SCHOOL = (100, 100)


# Three possible walking routes.
#
# Each route has several points representing the path.

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
# LEOPARD
# ---------------------------------------------------------

LEOPARD_START = (20, 75)

STEP = 6

TOTAL_MINUTES = 60

INTERVAL = 5


# The leopard will become invisible to our sensors
# during this period.

BLIND_START = 20
BLIND_END = 35


# ---------------------------------------------------------
# BASIC GEOMETRY
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
# SENSOR MODEL
# ---------------------------------------------------------

def sensor_detects(
    animal_position,
    sensor_position,
    blind=False
):

    # During the deliberate blind period,
    # every sensor misses the animal.

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
# ROUTE DISTANCE
# ---------------------------------------------------------

def route_distance(
    animal_position,
    route
):

    return min(
        distance(animal_position, point)
        for point in route
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
# ROUTE RISK
# ---------------------------------------------------------

def calculate_route_risk(
    predicted_position,
    uncertainty,
    route
):

    d = route_distance(
        predicted_position,
        route
    )

    # Base risk.

    if d < 12:

        risk = 80

    elif d < 22:

        risk = 55

    elif d < 35:

        risk = 30

    else:

        risk = 10


    # Uncertainty increases risk slightly.

    risk += uncertainty * 0.25


    # Keep between 0 and 100.

    return min(
        100,
        max(0, risk)
    )


# ---------------------------------------------------------
# STATUS
# ---------------------------------------------------------

def status_from_risk(risk):

    if risk >= 65:

        return "DANGER"

    elif risk >= 35:

        return "CAUTION"

    elif risk >= 15:

        return "LOW RISK"

    else:

        return "SAFE"


# ---------------------------------------------------------
# MAIN SIMULATION
# ---------------------------------------------------------

def main():

    random.seed(10)

    leopard = LEOPARD_START


    # Initial direction toward the village.

    dx = SCHOOL[0] - leopard[0]

    dy = SCHOOL[1] - leopard[1]

    nx, ny = normalise(
        dx,
        dy
    )

    velocity = (
        nx * STEP,
        ny * STEP
    )


    last_observation = None

    last_known_position = None

    previous_observation = None


    uncertainty = 10


    print()

    print(
        "======================================================"
    )

    print(
        "              WILD SENTINEL V0.3"
    )

    print(
        "        HUMAN ROUTE SAFETY SIMULATOR"
    )

    print(
        "======================================================"
    )

    print()

    print(
        "Scenario:"
    )

    print(
        "A mother is travelling from her house to school."
    )

    print(
        "There are three possible routes."
    )

    print(
        "A leopard is moving through dense vegetation."
    )

    print()

    print(
        "Sensor blind period:",
        f"{BLIND_START}-{BLIND_END} minutes"
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


        # ---------------------------------------------
        # Make animal movement slightly unpredictable.
        # ---------------------------------------------

        angle = random.uniform(
            -0.12,
            0.12
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
                new_vx / speed * STEP,
                new_vy / speed * STEP
            )


        # Move leopard.

        leopard = move(
            leopard,
            velocity
        )


        # ---------------------------------------------
        # Sensor visibility
        # ---------------------------------------------

        blind = (
            BLIND_START
            <= minute
            <= BLIND_END
        )


        detections = []


        for sensor_id, sensor_position in SENSORS.items():

            if sensor_detects(
                leopard,
                sensor_position,
                blind
            ):

                detections.append(
                    sensor_id
                )


        # ---------------------------------------------
        # Update knowledge
        # ---------------------------------------------

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

                velocity = (
                    dx,
                    dy
                )


            previous_observation = (
                current_observation
            )

            last_known_position = (
                current_observation
            )

            last_observation = minute


            # New information reduces uncertainty.

            uncertainty = max(
                5,
                uncertainty - 7
            )


        else:

            # No observation means uncertainty grows.

            uncertainty = min(
                50,
                uncertainty + 5
            )


        # ---------------------------------------------
        # Predict current position
        # ---------------------------------------------

        if (
            last_known_position is not None
            and last_observation is not None
        ):

            elapsed = (
                minute
                - last_observation
            )


            predicted_position = (

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

            predicted_position = leopard


        # ---------------------------------------------
        # Calculate route risks
        # ---------------------------------------------

        risks = {}


        for route_name, route in ROUTES.items():

            risks[route_name] = calculate_route_risk(

                predicted_position,

                uncertainty,

                route
            )


        # Find safest route.

        safest_route = min(
            risks,
            key=risks.get
        )


        print(
            f"{minute:02d} min | "
            f"Observed: "
            f"{str(bool(detections)):5s} | "
            f"Last seen: "
            f"{str(last_observation):>2s} | "
            f"Uncertainty: "
            f"{uncertainty:4.1f}"
        )


        print(
            f"    Route A: "
            f"{risks['A']:5.1f}% "
            f"{status_from_risk(risks['A'])}"
        )

        print(
            f"    Route B: "
            f"{risks['B']:5.1f}% "
            f"{status_from_risk(risks['B'])}"
        )

        print(
            f"    Route C: "
            f"{risks['C']:5.1f}% "
            f"{status_from_risk(risks['C'])}"
        )


        print(
            f"    >>> RECOMMENDED: "
            f"ROUTE {safest_route}"
        )


        # ---------------------------------------------
        # Important warning
        # ---------------------------------------------

        dangerous_routes = [

            r
            for r, risk in risks.items()
            if risk >= 65
        ]


        if dangerous_routes:

            print()

            print(
                "    🚨 WILDLIFE WARNING"
            )

            print(
                "    Avoid:",
                ", ".join(
                    dangerous_routes
                )
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


if __name__ == "__main__":

    main()