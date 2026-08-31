"""
========================================================
             WILD SENTINEL V0.7
       ADVERSARIAL PREDICTION ENGINE
========================================================

PURPOSE

V0.7 deliberately changes the wildlife direction while
the sensors are blind.

The engine must:

    1. Continue its original prediction
    2. Track increasing uncertainty
    3. Detect when new evidence contradicts prediction
    4. Calculate prediction divergence
    5. Classify model drift
    6. Recalculate the wildlife trajectory
    7. Invalidate stale predictions
    8. Avoid unsafe route recommendations

IMPORTANT

This is a simulation prototype.

The percentages and distances are simulated values.
They are NOT real-world wildlife probabilities.

========================================================
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

        a.x
        + (b.x - a.x) * fraction,

        a.y
        + (b.y - a.y) * fraction
    )


# ======================================================
# HUMAN ROUTE
# ======================================================

class HumanRoute:

    def __init__(
        self,
        name,
        waypoints
    ):

        self.name = name
        self.waypoints = waypoints

    def position_at(self, minute):

        if not self.waypoints:

            return None

        if minute <= self.waypoints[0][0]:

            return self.waypoints[0][1]

        for i in range(
            len(self.waypoints) - 1
        ):

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
# WILD SENTINEL V0.7
# ======================================================

class WildSentinelV07:

    def __init__(self):

        # ------------------------------------------------
        # Current wildlife state
        # ------------------------------------------------

        self.last_position = None

        self.velocity = Point(
            0.0,
            0.0
        )

        self.last_observation_time = None

        # ------------------------------------------------
        # Prediction parameters
        # ------------------------------------------------

        self.base_uncertainty = 5.0

        self.uncertainty_growth = 1.75

        self.max_uncertainty = 35.0

        self.minimum_confidence = 0.35

        # ------------------------------------------------
        # Adversarial monitoring
        # ------------------------------------------------

        self.last_predicted_position = None

        self.last_prediction_time = None

        self.prediction_error = 0.0

        self.divergence_state = "NONE"

        self.model_valid = True

        # ------------------------------------------------
        # Direction change detection
        # ------------------------------------------------

        self.previous_velocity = None

    # ==================================================
    # OBSERVE
    # ==================================================

    def observe(
        self,
        minute,
        x,
        y
    ):

        new_position = Point(
            float(x),
            float(y)
        )

        # ----------------------------------------------
        # First observation
        # ----------------------------------------------

        if self.last_position is None:

            self.last_position = new_position

            self.last_observation_time = minute

            self.model_valid = True

            return {
                "prediction_error": 0.0,
                "divergence": "NONE",
                "direction_change": False
            }

        # ----------------------------------------------
        # Calculate new velocity
        # ----------------------------------------------

        dt = (
            minute
            - self.last_observation_time
        )

        if dt <= 0:

            return {
                "prediction_error": 0.0,
                "divergence": "NONE",
                "direction_change": False
            }

        new_velocity = Point(

            (
                new_position.x
                - self.last_position.x
            ) / dt,

            (
                new_position.y
                - self.last_position.y
            ) / dt
        )

        # ----------------------------------------------
        # Compare with previous prediction
        # ----------------------------------------------

        prediction_error = 0.0

        if (
            self.last_predicted_position
            is not None
        ):

            prediction_error = distance(

                self.last_predicted_position,

                new_position
            )

        # ----------------------------------------------
        # Direction change detection
        # ----------------------------------------------

        direction_change = False

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

                # Significant directional change.
                if cosine < 0.80:

                    direction_change = True

        # ----------------------------------------------
        # Divergence classification
        # ----------------------------------------------

        if prediction_error <= 3:

            divergence = "NORMAL"

        elif prediction_error <= 7:

            divergence = "DRIFT"

        elif prediction_error <= 15:

            divergence = "SIGNIFICANT DIVERGENCE"

        else:

            divergence = "MODEL FAILURE"

        # ----------------------------------------------
        # Model validity
        # ----------------------------------------------

        if divergence == "MODEL FAILURE":

            self.model_valid = False

        elif divergence == \
                "SIGNIFICANT DIVERGENCE":

            self.model_valid = False

        elif direction_change:

            self.model_valid = False

        else:

            self.model_valid = True

        # ----------------------------------------------
        # Update state
        # ----------------------------------------------

        self.previous_velocity = \
            self.velocity

        self.velocity = new_velocity

        self.last_position = new_position

        self.last_observation_time = minute

        self.prediction_error = \
            prediction_error

        self.divergence_state = \
            divergence

        # A new observation means the new model can
        # be used from this point onward.

        if direction_change:

            self.divergence_state = \
                "DIRECTION CHANGE"

        self.model_valid = True

        return {

            "prediction_error":
                prediction_error,

            "divergence":
                self.divergence_state,

            "direction_change":
                direction_change
        }

    # ==================================================
    # PREDICT
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

        # Store the most recent prediction.

        self.last_predicted_position = \
            predicted

        self.last_prediction_time = \
            minute

        return (
            predicted,
            uncertainty,
            confidence
        )

    # ==================================================
    # PROXIMITY
    # ==================================================

    def proximity(
        self,
        separation
    ):

        if separation is None:

            return "UNKNOWN"

        if separation <= 1:

            return "CRITICAL"

        if separation <= 3:

            return "VERY CLOSE"

        if separation <= 7:

            return "CLOSE"

        if separation <= 15:

            return "NEAR"

        return "DISTANT"

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

            minute = (
                current_minute
                + offset
            )

            wildlife, uncertainty, confidence = \
                self.predict(
                    minute
                )

            human = route.position_at(
                minute
            )

            if wildlife is None:
                continue

            if human is None:
                continue

            separation = distance(
                wildlife,
                human
            )

            samples.append({

                "minute":
                    minute,

                "separation":
                    separation,

                "confidence":
                    confidence,

                "uncertainty":
                    uncertainty
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

            if confidence >= \
                    self.minimum_confidence:

                state = \
                    "CRITICAL ENCOUNTER"

            else:

                state = \
                    "POTENTIAL CRITICAL"

        elif separation <= 7:

            if confidence >= \
                    self.minimum_confidence:

                state = \
                    "HIGH EXPOSURE"

            else:

                state = \
                    "POTENTIAL EXPOSURE"

        elif confidence < \
                self.minimum_confidence:

            state = \
                "UNKNOWN"

        else:

            state = \
                "NO ENCOUNTER"

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
            not in (

                "UNKNOWN",

                "CRITICAL ENCOUNTER",

                "POTENTIAL CRITICAL",

                "HIGH EXPOSURE",

                "POTENTIAL EXPOSURE"
            )

            and a["confidence"]
            >= self.minimum_confidence
        ]

        if not usable:

            return (
                "WAIT / DO NOT ENTER"
            )

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
# ACTUAL ADVERSARIAL LEOPARD TRACK
# ======================================================

def actual_leopard_position(
    minute
):

    # --------------------------------------------------
    # PHASE 1
    #
    # Straight diagonal movement.
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
    # PHASE 2
    #
    # Leopard changes direction while blind.
    #
    # This is the adversarial event.
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
    # PHASE 3
    #
    # Continues after the turn.
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
# SENSOR SCHEDULE
# ======================================================

def sensor_visible(minute):

    return minute in (

        10,

        15,

        40,

        45
    )


# ======================================================
# DISPLAY
# ======================================================

def display(
    engine,
    minute,
    actual,
    visible,
    routes,
    observation_result=None
):

    predicted, uncertainty, confidence = \
        engine.predict(
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

    if predicted is None:

        print(
            "  Predicted wildlife: UNKNOWN"
        )

    else:

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

    # --------------------------------------------------
    # New evidence analysis.
    # --------------------------------------------------

    if observation_result:

        error = \
            observation_result[
                "prediction_error"
            ]

        divergence = \
            observation_result[
                "divergence"
            ]

        direction_change = \
            observation_result[
                "direction_change"
            ]

        print()

        print(
            "  🔎 MODEL VALIDATION"
        )

        print(
            f"  Prediction error: "
            f"{error:.1f}"
        )

        print(
            f"  Divergence: "
            f"{divergence}"
        )

        print(
            "  Direction change detected: "
            + (
                "YES"
                if direction_change
                else "NO"
            )
        )

        if direction_change:

            print()

            print(
                "  🚨 MOVEMENT MODEL CHANGE"
            )

            print(
                "  Wildlife direction changed."
            )

            print(
                "  Previous trajectory "
                "must not be trusted."
            )

    # --------------------------------------------------
    # Route analysis.
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
            f"{assessment.get('state', 'UNKNOWN')}"
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
            f"{assessment['confidence'] * 100:.1f}%"
        )

        if assessment[
            "encounter_time"
        ] is not None:

            print(
                f"      Encounter window: "
                f"~{assessment['encounter_time']} min"
            )

    # --------------------------------------------------
    # Recommendation.
    # --------------------------------------------------

    recommendation = \
        engine.recommend(
            assessments
        )

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

        for a in dangerous:

            print(
                f"  Avoid ROUTE "
                f"{a['route']}"
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
# MAIN TEST
# ======================================================

def run_demo():

    print("""
========================================================
             WILD SENTINEL V0.7
       ADVERSARIAL PREDICTION ENGINE
========================================================

TEST:

The leopard initially travels diagonally.

At approximately 20 minutes it changes direction
while the sensors are blind.

The engine does NOT know that the turn occurred.

At 40 minutes the sensor returns.

Wild Sentinel must determine whether its previous
straight-line prediction was wrong.

========================================================

EXPECTED BEHAVIOUR:

    SENSOR BLIND
          ↓
    CONTINUE PREDICTION
          ↓
    UNCERTAINTY INCREASES
          ↓
    SENSOR RETURNS
          ↓
    COMPARE PREDICTION vs OBSERVATION
          ↓
    DETECT DIVERGENCE
          ↓
    DETECT DIRECTION CHANGE
          ↓
    INVALIDATE STALE MODEL
          ↓
    RECALCULATE TRAJECTORY

========================================================
""")

    engine = WildSentinelV07()

    # --------------------------------------------------
    # Routes
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

    # Route C is deliberately placed near the
    # NEW trajectory after the leopard turns.

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
    # Run at five-minute intervals.
    # --------------------------------------------------

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
        # Only sensor-visible positions are given
        # to the engine.
        # ----------------------------------------------

        if visible:

            # Before observation, make a prediction
            # so that prediction-vs-observation can
            # be compared.

            engine.predict(
                minute
            )

            observation_result = \
                engine.observe(

                    minute,

                    actual.x,

                    actual.y
                )

        display(

            engine,

            minute,

            actual,

            visible,

            routes,

            observation_result
        )

    print("""
========================================================
                 V0.7 TEST COMPLETE
========================================================

V0.7 QUESTIONS:

1. Did Wild Sentinel continue predicting during blindness?

2. Did uncertainty increase?

3. When the sensor returned, did prediction error
   become visible?

4. Did the engine detect the direction change?

5. Did it stop trusting the old trajectory?

6. Did it recalculate the wildlife movement model?

7. Did it avoid blindly continuing the old prediction?

========================================================

NEXT:

V0.7.1 will make this harder.

Instead of waiting until the sensor returns,
Wild Sentinel will attempt to infer that the animal's
behaviour has probably changed using indirect evidence.

========================================================
""")


# ======================================================
# ENTRY POINT
# ======================================================

if __name__ == "__main__":

    run_demo()