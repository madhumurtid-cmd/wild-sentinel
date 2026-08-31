"""
WILD SENTINEL V0.6
PROBABILISTIC HUMAN/WILDLIFE ENGINE

Prototype:
- Predicts wildlife movement after sensor loss.
- Expands uncertainty during sensor blindness.
- Reduces prediction confidence over time.
- Uses an explicit UNKNOWN state.
- Never recommends a route when safety cannot be established.

Simulation only. Not a real-world wildlife safety system.
"""

from dataclasses import dataclass
from math import hypot, exp


@dataclass
class Point:
    x: float
    y: float


class WildSentinelV06:

    def __init__(self):
        self.last_position = None
        self.velocity = Point(0.0, 0.0)
        self.last_observation_time = None

        self.uncertainty_growth_per_min = 1.75
        self.max_uncertainty = 35.0

        # Below this confidence, we refuse to recommend a route.
        self.minimum_confidence = 0.18

    # --------------------------------------------------
    # SENSOR OBSERVATION
    # --------------------------------------------------

    def observe(self, minute, x, y):

        position = Point(float(x), float(y))

        if (
            self.last_position is not None
            and self.last_observation_time is not None
        ):

            dt = minute - self.last_observation_time

            if dt > 0:

                self.velocity = Point(
                    (position.x - self.last_position.x) / dt,
                    (position.y - self.last_position.y) / dt
                )

        self.last_position = position
        self.last_observation_time = minute

    # --------------------------------------------------
    # PREDICTION
    # --------------------------------------------------

    def predict(self, minute):

        if self.last_position is None:

            return None, self.max_uncertainty, 0.0

        elapsed = max(
            0,
            minute - self.last_observation_time
        )

        predicted = Point(

            self.last_position.x
            + self.velocity.x * elapsed,

            self.last_position.y
            + self.velocity.y * elapsed
        )

        uncertainty = min(

            5.0
            + elapsed * self.uncertainty_growth_per_min,

            self.max_uncertainty
        )

        confidence = max(

            0.0,

            min(
                1.0,
                1.0
                - (
                    uncertainty
                    / self.max_uncertainty
                )
            )
        )

        return predicted, uncertainty, confidence

    # --------------------------------------------------
    # ROUTE RISK
    # --------------------------------------------------

    def route_risk(
        self,
        route_point,
        predicted,
        uncertainty,
        confidence
    ):

        if predicted is None:
            return 0.0

        distance = hypot(

            route_point.x - predicted.x,

            route_point.y - predicted.y
        )

        sigma = max(
            1.0,
            uncertainty
        )

        spatial_probability = exp(

            -(
                distance ** 2
            )
            /
            (
                2 * sigma ** 2
            )
        )

        risk = (

            spatial_probability
            * confidence
            * 100
        )

        return max(
            0.0,
            min(100.0, risk)
        )

    # --------------------------------------------------
    # CLASSIFICATION
    # --------------------------------------------------

    def classify(
        self,
        risk,
        confidence
    ):

        if confidence < self.minimum_confidence:

            return "UNKNOWN"

        if risk >= 80:
            return "DANGER"

        if risk >= 50:
            return "HIGH RISK"

        if risk >= 25:
            return "CAUTION"

        if risk >= 8:
            return "LOW RISK"

        return "SAFE"

    # --------------------------------------------------
    # RECOMMENDATION
    # --------------------------------------------------

    def recommend(
        self,
        routes,
        confidence
    ):

        if confidence < self.minimum_confidence:

            return "WAIT / DO NOT ENTER"

        candidates = []

        for name, risk, state in routes:

            if state in (
                "SAFE",
                "LOW RISK",
                "CAUTION"
            ):

                candidates.append(
                    (name, risk)
                )

        if not candidates:

            return "WAIT / DO NOT ENTER"

        return min(
            candidates,
            key=lambda item: item[1]
        )[0]

    # --------------------------------------------------
    # EVALUATE
    # --------------------------------------------------

    def evaluate(
        self,
        minute,
        sensor_visible,
        routes
    ):

        predicted, uncertainty, confidence = \
            self.predict(minute)

        if predicted is None:

            return {

                "minute": minute,

                "predicted": None,

                "uncertainty":
                    self.max_uncertainty,

                "confidence": 0.0,

                "routes": [],

                "recommendation":
                    "WAIT / DO NOT ENTER"
            }

        # Direct observation = very high confidence.
        effective_confidence = (

            1.0
            if sensor_visible
            else confidence
        )

        results = []

        for name, point in routes.items():

            risk = self.route_risk(

                point,

                predicted,

                uncertainty,

                effective_confidence
            )

            state = self.classify(

                risk,

                effective_confidence
            )

            results.append(
                (name, risk, state)
            )

        recommendation = self.recommend(

            results,

            effective_confidence
        )

        return {

            "minute": minute,

            "predicted": predicted,

            "uncertainty":
                uncertainty,

            "confidence":
                effective_confidence,

            "routes":
                results,

            "recommendation":
                recommendation
        }


# ======================================================
# DISPLAY
# ======================================================

def print_result(
    result,
    actual=None,
    sensor_visible=False
):

    print("-" * 60)

    print(
        f"{result['minute']:02d} min"
    )

    if actual:

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

    predicted = result["predicted"]

    if predicted:

        print(
            f"  Predicted position: "
            f"({predicted.x:5.1f}, "
            f"{predicted.y:5.1f})"
        )

    print(
        f"  Wildlife uncertainty: "
        f"{result['uncertainty']:5.1f}"
    )

    print(
        f"  Prediction confidence: "
        f"{result['confidence'] * 100:5.1f}%"
    )

    for name, risk, state in result["routes"]:

        print(
            f"  ROUTE {name}: "
            f"{risk:5.1f}% "
            f"{state}"
        )

    dangerous = [

        name

        for name, risk, state
        in result["routes"]

        if state in (
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
                "ROUTE " + name
                for name in dangerous
            )
        )

    if (
        result["recommendation"]
        == "WAIT / DO NOT ENTER"
    ):

        print()

        print(
            "  ⚠️ WILDLIFE LOCATION UNKNOWN"
        )

        print(
            "  No route can currently "
            "be classified as safe."
        )

    print()

    print(
        "  >>> RECOMMENDATION: "
        + result["recommendation"]
    )


# ======================================================
# V0.6 DEMONSTRATION
# ======================================================

def run_demo():

    print("""

========================================================
             WILD SENTINEL V0.6
       PROBABILISTIC HUMAN/WILDLIFE ENGINE
========================================================

V0.6 FEATURES

  ✓ Movement prediction
  ✓ Sensor-blind prediction
  ✓ Spatial uncertainty
  ✓ Confidence decay
  ✓ UNKNOWN state
  ✓ Conservative route selection
  ✓ No fake SAFE recommendation

========================================================
""")

    engine = WildSentinelV06()

    # Three simulated human routes.

    routes = {

        "A": Point(30, 70),

        "B": Point(50, 50),

        "C": Point(70, 30)
    }

    # Actual leopard track.
    #
    # IMPORTANT:
    # The engine does NOT automatically receive
    # these positions. It only receives positions
    # when the simulated sensor is visible.

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

    # Sensor blindness:
    #
    # 10-15 = visible
    # 20-35 = blind
    # 40 = visible

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

    for minute, actual in actual_track.items():

        visible = sensor_visible[minute]

        # Feed observation ONLY when sensor sees animal.

        if visible:

            engine.observe(

                minute,

                actual.x,

                actual.y
            )

        result = engine.evaluate(

            minute,

            visible,

            routes
        )

        print_result(

            result,

            actual,

            visible
        )

    print("""

========================================================
                 V0.6 TEST COMPLETE
========================================================

The engine has demonstrated:

1. Last-known movement retention
2. Prediction through sensor blindness
3. Increasing uncertainty
4. Decreasing confidence
5. Route exposure estimation
6. Explicit UNKNOWN state
7. Conservative "DO NOT ENTER" behaviour

IMPORTANT:

These are simulation scores.

They are NOT real-world wildlife probabilities.

========================================================
""")


if __name__ == "__main__":
    run_demo()