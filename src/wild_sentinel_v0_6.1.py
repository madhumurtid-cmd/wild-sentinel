"""
========================================================
             WILD SENTINEL V0.6.1
       HUMAN / WILDLIFE ENCOUNTER ENGINE
========================================================

V0.6.1 introduces:

1. Wildlife movement prediction
2. Human route movement prediction
3. Predicted separation
4. Encounter windows
5. Confidence-aware recommendations
6. Explicit UNKNOWN state
7. Prediction degradation awareness

IMPORTANT:
This is a simulation prototype.
It is NOT a real-world wildlife safety system.
"""


from dataclasses import dataclass
from math import hypot


# ======================================================
# BASIC GEOMETRY
# ======================================================

@dataclass
class Point:
    x: float
    y: float


def distance(a, b):
    return hypot(
        a.x - b.x,
        a.y - b.y
    )


def interpolate(a, b, fraction):

    return Point(
        a.x + (b.x - a.x) * fraction,
        a.y + (b.y - a.y) * fraction
    )


# ======================================================
# HUMAN ROUTE
# ======================================================

class HumanRoute:

    def __init__(self, name, waypoints):

        self.name = name
        self.waypoints = waypoints

    def position_at(self, minute):

        if minute <= self.waypoints[0][0]:

            return self.waypoints[0][1]

        for i in range(len(self.waypoints) - 1):

            t1, p1 = self.waypoints[i]
            t2, p2 = self.waypoints[i + 1]

            if t1 <= minute <= t2:

                duration = t2 - t1

                if duration == 0:
                    return p2

                fraction = (
                    minute - t1
                ) / duration

                return interpolate(
                    p1,
                    p2,
                    fraction
                )

        return self.waypoints[-1][1]


# ======================================================
# WILD SENTINEL ENGINE
# ======================================================

class WildSentinelV061:

    def __init__(self):

        self.last_position = None

        self.velocity = Point(
            0.0,
            0.0
        )

        self.last_observation_time = None

        self.prediction_uncertainty = 5.0

        self.uncertainty_growth = 1.75

        self.max_uncertainty = 35.0

        # Below this confidence:
        # DO NOT recommend a route.

        self.minimum_confidence = 0.35

    # ==================================================
    # SENSOR OBSERVATION
    # ==================================================

    def observe(
        self,
        minute,
        x,
        y
    ):

        position = Point(
            float(x),
            float(y)
        )

        if (
            self.last_position is not None
            and self.last_observation_time is not None
        ):

            dt = (
                minute
                - self.last_observation_time
            )

            if dt > 0:

                self.velocity = Point(

                    (
                        position.x
                        - self.last_position.x
                    ) / dt,

                    (
                        position.y
                        - self.last_position.y
                    ) / dt
                )

        self.last_position = position

        self.last_observation_time = minute

    # ==================================================
    # WILDLIFE PREDICTION
    # ==================================================

    def predict(
        self,
        minute
    ):

        if self.last_position is None:

            return (
                None,
                self.max_uncertainty,
                0.0
            )

        elapsed = max(
            0,
            minute
            - self.last_observation_time
        )

        predicted = Point(

            self.last_position.x
            + self.velocity.x * elapsed,

            self.last_position.y
            + self.velocity.y * elapsed
        )

        uncertainty = min(

            self.prediction_uncertainty
            + (
                elapsed
                * self.uncertainty_growth
            ),

            self.max_uncertainty
        )

        confidence = max(

            0.0,

            1.0
            - (
                uncertainty
                / self.max_uncertainty
            )
        )

        return (
            predicted,
            uncertainty,
            confidence
        )

    # ==================================================
    # ENCOUNTER ANALYSIS
    # ==================================================

    def encounter_analysis(
        self,
        route,
        current_minute,
        horizon=10,
        step=1
    ):

        encounters = []

        for offset in range(
            0,
            horizon + 1,
            step
        ):

            future_time = (
                current_minute
                + offset
            )

            wildlife, uncertainty, confidence = \
                self.predict(future_time)

            if wildlife is None:
                continue

            human = route.position_at(
                future_time
            )

            separation = distance(
                wildlife,
                human
            )

            # Conservative encounter threshold.
            # In a real system this would depend on:
            # terrain, species, visibility,
            # behaviour and human movement.

            threshold = max(
                3.0,
                uncertainty * 0.35
            )

            if separation <= threshold:

                encounters.append({

                    "minute":
                        future_time,

                    "separation":
                        separation,

                    "uncertainty":
                        uncertainty,

                    "confidence":
                        confidence
                })

        return encounters

    # ==================================================
    # ROUTE RISK
    # ==================================================

    def route_assessment(
        self,
        route,
        minute
    ):

        encounters = self.encounter_analysis(
            route,
            minute
        )

        predicted, uncertainty, confidence = \
            self.predict(minute)

        if predicted is None:

            return {

                "route":
                    route.name,

                "state":
                    "UNKNOWN",

                "risk":
                    0.0,

                "confidence":
                    0.0,

                "encounters":
                    []
            }

        # Find closest predicted encounter.

        if encounters:

            closest = min(
                encounters,
                key=lambda x:
                    x["separation"]
            )

            separation = closest[
                "separation"
            ]

            encounter_confidence = \
                closest["confidence"]

            # Convert separation to a risk score.

            risk = max(

                0.0,

                min(

                    100.0,

                    (
                        1.0
                        - (
                            separation
                            / max(
                                uncertainty,
                                1.0
                            )
                        )
                    )
                    * 100
                    * encounter_confidence
                )
            )

        else:

            # No predicted encounter.

            risk = 0.0

        # Confidence gate.

        if confidence < self.minimum_confidence:

            state = "UNKNOWN"

        elif risk >= 75:

            state = "DANGER"

        elif risk >= 50:

            state = "HIGH RISK"

        elif risk >= 25:

            state = "CAUTION"

        elif risk >= 8:

            state = "LOW RISK"

        else:

            state = "SAFE"

        return {

            "route":
                route.name,

            "state":
                state,

            "risk":
                risk,

            "confidence":
                confidence,

            "encounters":
                encounters
        }

    # ==================================================
    # RECOMMENDATION
    # ==================================================

    def recommend(
        self,
        assessments
    ):

        # First check prediction confidence.

        usable = [

            a

            for a in assessments

            if a["state"] != "UNKNOWN"
        ]

        if not usable:

            return (
                "WAIT / DO NOT ENTER"
            )

        safe = [

            a

            for a in usable

            if a["state"]
            in (
                "SAFE",
                "LOW RISK",
                "CAUTION"
            )
        ]

        if not safe:

            return (
                "WAIT / DO NOT ENTER"
            )

        best = min(
            safe,
            key=lambda a:
                a["risk"]
        )

        return (
            "ROUTE "
            + best["route"]
        )


# ======================================================
# DISPLAY
# ======================================================

def print_assessment(
    engine,
    minute,
    actual,
    sensor_visible,
    routes
):

    predicted, uncertainty, confidence = \
        engine.predict(minute)

    print()
    print("-" * 64)

    print(
        f"{minute:02d} min"
    )

    print(
        f"  Actual leopard: "
        f"({actual.x:5.1f}, "
        f"{actual.y:5.1f})"
    )

    print(
        "  Sensor: "
        + (
            "VISIBLE"
            if sensor_visible
            else "BLIND"
        )
    )

    if predicted:

        print(
            f"  Predicted wildlife: "
            f"({predicted.x:5.1f}, "
            f"{predicted.y:5.1f})"
        )

    print(
        f"  Uncertainty: "
        f"{uncertainty:5.1f}"
    )

    print(
        f"  Prediction confidence: "
        f"{confidence * 100:5.1f}%"
    )

    assessments = []

    for route in routes:

        assessment = \
            engine.route_assessment(
                route,
                minute
            )

        assessments.append(
            assessment
        )

        print()

        print(
            f"  ROUTE {route.name}: "
            f"{assessment['risk']:5.1f}% "
            f"{assessment['state']}"
        )

        encounters = \
            assessment["encounters"]

        if encounters:

            closest = min(
                encounters,
                key=lambda x:
                    x["separation"]
            )

            print(
                f"      Possible encounter: "
                f"~{closest['minute']} min"
            )

            print(
                f"      Predicted separation: "
                f"{closest['separation']:.1f}"
            )

    recommendation = \
        engine.recommend(
            assessments
        )

    dangerous = [

        a["route"]

        for a in assessments

        if a["state"]
        in (
            "DANGER",
            "HIGH RISK"
        )
    ]

    if dangerous:

        print()

        print(
            "  🚨 WILDLIFE WARNING"
        )

        print(
            "  Avoid: "
            + ", ".join(
                "ROUTE " + x
                for x in dangerous
            )
        )

    if recommendation == \
            "WAIT / DO NOT ENTER":

        print()

        print(
            "  ⚠️ PREDICTION "
            "INSUFFICIENT"
        )

        print(
            "  Wild Sentinel cannot "
            "confidently identify a "
            "safe route."
        )

    print()

    print(
        "  >>> RECOMMENDATION: "
        + recommendation
    )


# ======================================================
# V0.6.1 DEMO
# ======================================================

def run_demo():

    print("""
========================================================
             WILD SENTINEL V0.6.1
       HUMAN / WILDLIFE ENCOUNTER ENGINE
========================================================

TEST:

Leopard moves diagonally across the landscape.

Sensor blindness:
20 - 35 minutes

Wild Sentinel must:

  ✓ Continue predicting
  ✓ Track uncertainty
  ✓ Model moving humans
  ✓ Predict separation
  ✓ Identify encounter windows
  ✓ Reduce confidence
  ✓ Refuse unsafe recommendations
========================================================
""")

    engine = WildSentinelV061()

    # --------------------------------------------------
    # ACTUAL LEOPARD TRACK
    # --------------------------------------------------

    actual_track = {

        0: Point(15, 85),

        5: Point(22.2, 77.8),

        10: Point(29.5, 70.5),

        15: Point(36.7, 63.3),

        20: Point(44.0, 56.0),

        25: Point(51.2, 48.8),

        30: Point(58.5, 41.5),

        35: Point(65.7, 34.3),

        40: Point(73.0, 27.0),

        45: Point(80.2, 19.8)
    }

    # --------------------------------------------------
    # SENSOR VISIBILITY
    # --------------------------------------------------

    sensor_visible = {

        0: False,
        5: False,
        10: True,
        15: True,

        20: False,
        25: False,
        30: False,
        35: False,

        40: True,
        45: False
    }

    # --------------------------------------------------
    # HUMAN ROUTES
    # --------------------------------------------------

    route_a = HumanRoute(

        "A",

        [

            (0, Point(5, 95)),

            (15, Point(20, 80)),

            (30, Point(25, 60)),

            (45, Point(20, 40))
        ]
    )

    # Route B deliberately crosses
    # the predicted wildlife corridor.

    route_b = HumanRoute(

        "B",

        [

            (0, Point(5, 95)),

            (15, Point(30, 70)),

            (25, Point(50, 50)),

            (35, Point(70, 30)),

            (45, Point(90, 10))
        ]
    )

    route_c = HumanRoute(

        "C",

        [

            (0, Point(5, 95)),

            (15, Point(10, 60)),

            (30, Point(10, 30)),

            (45, Point(15, 10))
        ]
    )

    routes = [

        route_a,
        route_b,
        route_c
    ]

    # --------------------------------------------------
    # RUN SIMULATION
    # --------------------------------------------------

    for minute, actual in \
            actual_track.items():

        visible = \
            sensor_visible[minute]

        if visible:

            engine.observe(

                minute,

                actual.x,

                actual.y
            )

        print_assessment(

            engine,

            minute,

            actual,

            visible,

            routes
        )

    print("""
========================================================
                 V0.6.1 TEST COMPLETE
========================================================

NEXT TEST:

V0.7 will deliberately change the leopard's direction
during sensor blindness.

The objective will be to determine whether Wild Sentinel
recognises that its original prediction is becoming wrong.

========================================================
""")


if __name__ == "__main__":

    run_demo()