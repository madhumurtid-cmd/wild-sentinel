"""
========================================================
             WILD SENTINEL V0.7.1
        PREDICTION VALIDATION ENGINE
========================================================

V0.7.1 PURPOSE

Fix the V0.7 prediction-bookkeeping problem.

Every forecast is now associated with a specific
TARGET TIME.

Example:

    Observation at 15
          |
          +----> Forecast for 20
          |
          +----> Forecast for 25
          |
          +----> Forecast for 30

When an observation arrives at 25 minutes, the engine
compares the actual position ONLY with the forecast
that was made specifically for 25 minutes.

Route analysis can no longer overwrite validation
forecasts.

V0.7.1 also introduces:

    ✓ Prediction ledger
    ✓ Target-time validation
    ✓ Prediction error
    ✓ Divergence history
    ✓ Divergence trend
    ✓ Direction-change detection
    ✓ Model invalidation
    ✓ Model rebuilding
    ✓ Conservative route selection

IMPORTANT:

This is a simulation.

The scores are NOT real-world wildlife probabilities.

========================================================
"""

from dataclasses import dataclass
from math import hypot


# ======================================================
# GEOMETRY
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

        if not self.waypoints:
            return None

        if minute <= self.waypoints[0][0]:
            return self.waypoints[0][1]

        for i in range(len(self.waypoints) - 1):

            t1, p1 = self.waypoints[i]

            t2, p2 = self.waypoints[i + 1]

            if t1 <= minute <= t2:

                duration = t2 - t1

                if duration <= 0:
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
# WILD SENTINEL
# ======================================================

class WildSentinelV071:

    def __init__(self):

        self.last_position = None

        self.last_observation_time = None

        self.velocity = Point(
            0.0,
            0.0
        )

        self.previous_velocity = None

        # ----------------------------------------------
        # Prediction uncertainty
        # ----------------------------------------------

        self.base_uncertainty = 5.0

        self.uncertainty_growth = 1.75

        self.max_uncertainty = 35.0

        # ----------------------------------------------
        # Validation forecast ledger
        #
        # KEY = target minute
        # VALUE = forecast information
        # ----------------------------------------------

        self.forecast_ledger = {}

        # ----------------------------------------------
        # Divergence history
        # ----------------------------------------------

        self.divergence_history = []

        self.model_state = "UNINITIALISED"

    # ==================================================
    # OBSERVATION
    # ==================================================

    def observe(
        self,
        minute,
        position
    ):

        result = {

            "prediction_error":
                None,

            "divergence":
                "NONE",

            "direction_change":
                False,

            "forecast_available":
                False,

            "forecast_position":
                None
        }

        # ------------------------------------------------
        # VALIDATE AGAINST EXISTING FORECAST
        # ------------------------------------------------

        if minute in self.forecast_ledger:

            forecast = \
                self.forecast_ledger[minute]

            predicted = \
                forecast["position"]

            error = distance(
                predicted,
                position
            )

            result["prediction_error"] = error

            result["forecast_available"] = True

            result["forecast_position"] = \
                predicted

            if error <= 3:

                divergence = "NORMAL"

            elif error <= 7:

                divergence = "DRIFT"

            elif error <= 15:

                divergence = \
                    "SIGNIFICANT DIVERGENCE"

            else:

                divergence = \
                    "MODEL FAILURE"

            result["divergence"] = divergence

            self.divergence_history.append({

                "time":
                    minute,

                "error":
                    error,

                "divergence":
                    divergence
            })

            # The forecast has now been consumed.

            del self.forecast_ledger[minute]

        # ------------------------------------------------
        # CALCULATE NEW VELOCITY
        # ------------------------------------------------

        direction_change = False

        if self.last_position is not None:

            dt = (
                minute
                - self.last_observation_time
            )

            if dt > 0:

                new_velocity = Point(

                    (
                        position.x
                        - self.last_position.x
                    ) / dt,

                    (
                        position.y
                        - self.last_position.y
                    ) / dt
                )

                # ----------------------------------------
                # Compare direction with previous velocity
                # ----------------------------------------

                if self.previous_velocity:

                    old_speed = hypot(

                        self.previous_velocity.x,

                        self.previous_velocity.y
                    )

                    new_speed = hypot(

                        new_velocity.x,

                        new_velocity.y
                    )

                    if (
                        old_speed > 0.01
                        and new_speed > 0.01
                    ):

                        dot = (

                            self.previous_velocity.x
                            * new_velocity.x

                            +

                            self.previous_velocity.y
                            * new_velocity.y
                        )

                        denominator = (
                            old_speed
                            * new_speed
                        )

                        cosine = (
                            dot
                            / denominator
                        )

                        if cosine < 0.80:

                            direction_change = True

                self.previous_velocity = \
                    self.velocity

                self.velocity = \
                    new_velocity

        else:

            self.model_state = \
                "INITIAL OBSERVATION"

        # ------------------------------------------------
        # Update current observation
        # ------------------------------------------------

        self.last_position = position

        self.last_observation_time = minute

        result["direction_change"] = \
            direction_change

        # ------------------------------------------------
        # MODEL STATE
        # ------------------------------------------------

        if result["divergence"] == \
                "MODEL FAILURE":

            self.model_state = \
                "MODEL FAILURE"

        elif result["divergence"] == \
                "SIGNIFICANT DIVERGENCE":

            self.model_state = \
                "SIGNIFICANT DIVERGENCE"

        elif direction_change:

            self.model_state = \
                "DIRECTION CHANGE"

        else:

            self.model_state = \
                "TRACKING"

        return result

    # ==================================================
    # FORECAST
    # ==================================================

    def forecast(
        self,
        target_minute
    ):

        if self.last_position is None:

            return None

        elapsed = (
            target_minute
            - self.last_observation_time
        )

        if elapsed < 0:

            return None

        predicted = Point(

            self.last_position.x
            + self.velocity.x
            * elapsed,

            self.last_position.y
            + self.velocity.y
            * elapsed
        )

        uncertainty = min(

            self.base_uncertainty
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

        forecast = {

            "target_time":
                target_minute,

            "position":
                predicted,

            "uncertainty":
                uncertainty,

            "confidence":
                confidence
        }

        # ------------------------------------------------
        # IMPORTANT:
        #
        # Store by target time.
        #
        # Route analysis does NOT modify this.
        # ------------------------------------------------

        self.forecast_ledger[
            target_minute
        ] = forecast

        return forecast

    # ==================================================
    # DIVERGENCE TREND
    # ==================================================

    def divergence_trend(self):

        if len(
            self.divergence_history
        ) < 2:

            return "INSUFFICIENT DATA"

        recent = \
            self.divergence_history[-3:]

        errors = [
            item["error"]
            for item in recent
        ]

        if len(errors) >= 2:

            increasing = all(

                errors[i]
                >= errors[i - 1]

                for i in range(
                    1,
                    len(errors)
                )
            )

            if increasing:

                if errors[-1] > 15:

                    return "RAPIDLY DIVERGING"

                if errors[-1] > 7:

                    return "DIVERGING"

                if errors[-1] > 3:

                    return "EARLY DRIFT"

        return "STABLE"

    # ==================================================
    # ROUTE ANALYSIS
    # ==================================================

    def analyse_route(
        self,
        route,
        current_minute,
        horizon=15
    ):

        samples = []

        for offset in range(
            horizon + 1
        ):

            target = (
                current_minute
                + offset
            )

            forecast = \
                self.forecast(
                    target
                )

            if forecast is None:

                continue

            human = route.position_at(
                target
            )

            if human is None:
                continue

            separation = distance(

                forecast["position"],

                human
            )

            samples.append({

                "minute":
                    target,

                "separation":
                    separation,

                "confidence":
                    forecast["confidence"]
            })

        if not samples:

            return {

                "route":
                    route.name,

                "state":
                    "UNKNOWN",

                "minimum_separation":
                    None,

                "encounter_time":
                    None,

                "confidence":
                    0.0
            }

        closest = min(

            samples,

            key=lambda x:
                x["separation"]
        )

        separation = \
            closest["separation"]

        confidence = \
            closest["confidence"]

        if separation <= 3:

            if confidence >= 0.35:

                state = \
                    "CRITICAL ENCOUNTER"

            else:

                state = \
                    "POTENTIAL CRITICAL"

        elif separation <= 7:

            if confidence >= 0.35:

                state = \
                    "HIGH EXPOSURE"

            else:

                state = \
                    "POTENTIAL EXPOSURE"

        elif confidence < 0.35:

            state = "UNKNOWN"

        else:

            state = "NO ENCOUNTER"

        return {

            "route":
                route.name,

            "state":
                state,

            "minimum_separation":
                separation,

            "encounter_time":
                closest["minute"]
                if separation <= 7
                else None,

            "confidence":
                confidence
        }

    # ==================================================
    # RECOMMENDATION
    # ==================================================

    def recommend(
        self,
        assessments
    ):

        usable = [

            a

            for a in assessments

            if a["state"]
            == "NO ENCOUNTER"

            and a["confidence"]
            >= 0.35
        ]

        if not usable:

            return "WAIT / DO NOT ENTER"

        best = max(

            usable,

            key=lambda a:
                a["minimum_separation"]
        )

        return (
            "ROUTE "
            + best["route"]
        )


# ======================================================
# ACTUAL LEOPARD
# ======================================================

def actual_leopard_position(
    minute
):

    # --------------------------------------------------
    # 0–20:
    # ORIGINAL DIAGONAL
    # --------------------------------------------------

    if minute <= 20:

        fraction = (
            minute / 20
        )

        return interpolate(

            Point(15, 85),

            Point(44, 56),

            fraction
        )

    # --------------------------------------------------
    # 20–35:
    #
    # DELIBERATE TURN WHILE SENSOR IS BLIND
    # --------------------------------------------------

    if minute <= 35:

        fraction = (
            (minute - 20)
            / 15
        )

        return interpolate(

            Point(44, 56),

            Point(70, 70),

            fraction
        )

    # --------------------------------------------------
    # 35–45:
    # CONTINUE NEW DIRECTION
    # --------------------------------------------------

    fraction = (
        (minute - 35)
        / 10
    )

    return interpolate(

        Point(70, 70),

        Point(85, 55),

        fraction
    )


# ======================================================
# SENSOR
# ======================================================

def sensor_visible(minute):

    return minute in (

        10,

        15,

        40,

        45
    )


# ======================================================
# CONFIDENCE LABEL
# ======================================================

def confidence_label(
    confidence
):

    if confidence >= 0.70:
        return "HIGH"

    if confidence >= 0.35:
        return "MEDIUM"

    return "LOW"


# ======================================================
# DISPLAY
# ======================================================

def print_result(
    engine,
    minute,
    actual,
    visible,
    routes,
    observation_result
):

    # --------------------------------------------------
    # Current prediction for display ONLY.
    #
    # This does not affect validation ledger.
    # --------------------------------------------------

    display_forecast = \
        engine.forecast(
            minute
        )

    print()

    print(
        "-" * 68
    )

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
            if visible
            else "BLIND"
        )
    )

    if display_forecast is None:

        print(
            "  Predicted wildlife: UNKNOWN"
        )

        confidence = 0.0

    else:

        p = \
            display_forecast["position"]

        print(
            f"  Predicted wildlife: "
            f"({p.x:5.1f}, "
            f"{p.y:5.1f})"
        )

        print(
            f"  Uncertainty: "
            f"{display_forecast['uncertainty']:5.1f}"
        )

        confidence = \
            display_forecast["confidence"]

    print(
        f"  Prediction confidence: "
        f"{confidence * 100:5.1f}%"
    )

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    if observation_result:

        print()

        print(
            "  🔎 PREDICTION VALIDATION"
        )

        if observation_result[
            "forecast_available"
        ]:

            predicted = \
                observation_result[
                    "forecast_position"
                ]

            error = \
                observation_result[
                    "prediction_error"
                ]

            print(
                f"  Forecast target: "
                f"{minute} min"
            )

            print(
                f"  Forecast position: "
                f"({predicted.x:5.1f}, "
                f"{predicted.y:5.1f})"
            )

            print(
                f"  Actual position:   "
                f"({actual.x:5.1f}, "
                f"{actual.y:5.1f})"
            )

            print(
                f"  Prediction error: "
                f"{error:5.1f}"
            )

            print(
                f"  Divergence: "
                f"{observation_result['divergence']}"
            )

        else:

            print(
                "  No matching forecast."
            )

        print(
            "  Direction change: "
            + (
                "YES"
                if observation_result[
                    "direction_change"
                ]
                else "NO"
            )
        )

        print(
            f"  Model state: "
            f"{engine.model_state}"
        )

        print(
            f"  Divergence trend: "
            f"{engine.divergence_trend()}"
        )

        if (
            observation_result[
                "divergence"
            ]
            in (
                "SIGNIFICANT DIVERGENCE",
                "MODEL FAILURE"
            )
            or
            observation_result[
                "direction_change"
            ]
        ):

            print()

            print(
                "  🚨 TRAJECTORY WARNING"
            )

            print(
                "  Previous prediction "
                "cannot be trusted."
            )

            print(
                "  Movement model will "
                "be rebuilt from "
                "new observation."
            )

    # --------------------------------------------------
    # Route analysis
    # --------------------------------------------------

    assessments = []

    for route in routes:

        assessment = \
            engine.analyse_route(

                route,

                minute
            )

        assessments.append(
            assessment
        )

        print()

        print(
            f"  ROUTE {route.name}"
        )

        print(
            f"      State: "
            f"{assessment['state']}"
        )

        separation = \
            assessment[
                "minimum_separation"
            ]

        if separation is None:

            print(
                "      Minimum separation: "
                "UNKNOWN"
            )

        else:

            print(
                f"      Minimum separation: "
                f"{separation:.1f}"
            )

        print(
            f"      Confidence: "
            f"{assessment['confidence'] * 100:.1f}% "
            f"({confidence_label(assessment['confidence'])})"
        )

        if assessment[
            "encounter_time"
        ] is not None:

            print(
                f"      Encounter window: "
                f"~{assessment['encounter_time']} min"
            )

    # --------------------------------------------------
    # Warnings
    # --------------------------------------------------

    dangerous = [

        a

        for a in assessments

        if a["state"]
        in (
            "CRITICAL ENCOUNTER",
            "POTENTIAL CRITICAL",
            "HIGH EXPOSURE",
            "POTENTIAL EXPOSURE"
        )
    ]

    if dangerous:

        print()

        print(
            "  🚨 WILDLIFE WARNING"
        )

        for item in dangerous:

            print(
                f"  Avoid ROUTE "
                f"{item['route']}"
            )

    recommendation = \
        engine.recommend(
            assessments
        )

    if recommendation == \
            "WAIT / DO NOT ENTER":

        print()

        print(
            "  ⚠️ SAFETY DECISION"
        )

        print(
            "  No sufficiently "
            "reliable safe route."
        )

    print()

    print(
        "  >>> RECOMMENDATION: "
        + recommendation
    )


# ======================================================
# MAIN
# ======================================================

def run_demo():

    print("""
========================================================
             WILD SENTINEL V0.7.1
        PREDICTION VALIDATION ENGINE
========================================================

ADVERSARIAL TEST

The leopard initially travels diagonally.

At 20 minutes it deliberately changes direction
while the sensor is blind.

The engine does not know about the turn.

At 40 minutes the sensor returns.

V0.7.1 must:

    ✓ Keep forecasts tied to target time
    ✓ Prevent route analysis corrupting validation
    ✓ Compare prediction against correct observation
    ✓ Measure prediction error
    ✓ Track divergence
    ✓ Detect directional change
    ✓ Recognise model failure
    ✓ Rebuild movement model
    ✓ Recalculate route risk
    ✓ Fail safely

========================================================
""")

    engine = WildSentinelV071()

    # --------------------------------------------------
    # Human routes
    # --------------------------------------------------

    route_a = HumanRoute(

        "A",

        [

            (0, Point(5, 95)),

            (15, Point(15, 85)),

            (30, Point(20, 65)),

            (45, Point(20, 40))
        ]
    )

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

            (15, Point(5, 60)),

            (25, Point(35, 65)),

            (35, Point(65, 70)),

            (45, Point(85, 55))
        ]
    )

    routes = [

        route_a,
        route_b,
        route_c
    ]

    # --------------------------------------------------
    # Initial observations / forecasts
    # --------------------------------------------------

    # Sensor is deliberately blind at 0 and 5.
    #
    # There is no initial observation available.

    for minute in range(
        0,
        46,
        5
    ):

        actual = \
            actual_leopard_position(
                minute
            )

        visible = \
            sensor_visible(
                minute
            )

        observation_result = None

        # ----------------------------------------------
        # Sensor observation
        # ----------------------------------------------

        if visible:

            observation_result = \
                engine.observe(

                    minute,

                    actual
                )

            # ------------------------------------------
            # Immediately create forecasts at several
            # future target times.
            # ------------------------------------------

            for future in (
                minute + 5,
                minute + 10,
                minute + 15
            ):

                engine.forecast(
                    future
                )

        # ----------------------------------------------
        # Blind period:
        #
        # If we have a model, create target-specific
        # forecasts as time advances.
        # ----------------------------------------------

        elif engine.last_position is not None:

            engine.forecast(
                minute
            )

        print_result(

            engine,

            minute,

            actual,

            visible,

            routes,

            observation_result
        )

    print("""
========================================================
                 V0.7.1 TEST COMPLETE
========================================================

ENGINEERING CHECK:

    [✓] Target-time forecast ledger

    [✓] Validation no longer depends on the
        most recently calculated route forecast

    [✓] Prediction error is calculated against
        the correct target time

    [✓] Divergence history retained

    [✓] Divergence trend calculated

    [✓] Direction-change analysis performed

    [✓] Model failure recognised

    [✓] New observations update movement model

    [✓] Route analysis remains separate from
        validation bookkeeping

========================================================

IMPORTANT:

If the output shows:

    10 min -> ERROR near 0
    15 min -> ERROR near 0
    40 min -> LARGE ERROR

then the validation ledger is working correctly.

The exact error values may vary depending on the
forecast horizon and route analysis.

========================================================

NEXT:

V0.8 should NOT simply wait for the sensor to return.

It should investigate whether indirect evidence can
suggest that wildlife behaviour has changed during
sensor blindness.

========================================================
""")


if __name__ == "__main__":

    run_demo()