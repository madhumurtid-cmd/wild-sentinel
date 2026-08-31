
"""
========================================================
             WILD SENTINEL V0.7.2
       BEHAVIOUR CHANGE DETECTION ENGINE
========================================================

PURPOSE
-------

V0.7.2 builds on V0.7.1.

It fixes the forecast timing problem and introduces
explicit behaviour-change detection.

The engine must NOT magically know what happened while
the sensor was blind.

Instead:

    SENSOR BLIND
          |
          v
    CONTINUE OLD MODEL
          |
          v
    UNCERTAINTY INCREASES
          |
          v
    SENSOR RETURNS
          |
          v
    COMPARE EXPECTED vs OBSERVED
          |
          v
    MEASURE ERROR
          |
          v
    ANALYSE NEW VELOCITY
          |
          v
    DETECT HEADING CHANGE
          |
          v
    SUSPECT / CONFIRM BEHAVIOUR CHANGE
          |
          v
    INVALIDATE OLD MODEL
          |
          v
    REBUILD TRAJECTORY

IMPORTANT
---------

This is a simulation.

The scores are NOT real-world wildlife
probabilities.

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

        a.x + (b.x - a.x) * fraction,

        a.y + (b.y - a.y) * fraction
    )


def magnitude(v):

    return hypot(
        v.x,
        v.y
    )


def dot(a, b):

    return (
        a.x * b.x
        +
        a.y * b.y
    )


def cosine_similarity(a, b):

    ma = magnitude(a)

    mb = magnitude(b)

    if ma == 0 or mb == 0:

        return 1.0

    return dot(a, b) / (ma * mb)


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

class WildSentinelV072:

    def __init__(self):

        # ----------------------------------------------
        # Latest observation
        # ----------------------------------------------

        self.last_position = None

        self.last_observation_time = None

        # ----------------------------------------------
        # Current velocity model
        # ----------------------------------------------

        self.velocity = Point(
            0.0,
            0.0
        )

        self.previous_velocity = None

        # ----------------------------------------------
        # Confidence
        # ----------------------------------------------

        self.base_uncertainty = 5.0

        self.uncertainty_growth = 1.75

        self.max_uncertainty = 35.0

        # ----------------------------------------------
        # Forecast ledger
        #
        # target time -> forecast
        # ----------------------------------------------

        self.forecast_ledger = {}

        # ----------------------------------------------
        # Validation history
        # ----------------------------------------------

        self.validation_history = []

        # ----------------------------------------------
        # Behaviour state
        # ----------------------------------------------

        self.behaviour_state = \
            "NO MODEL"

        self.model_state = \
            "UNINITIALISED"

        # ----------------------------------------------
        # Last known heading change
        # ----------------------------------------------

        self.heading_change_detected = False

    # ==================================================
    # CREATE FORECAST
    # ==================================================

    def forecast(
        self,
        target_minute,
        store=True
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
            +
            (
                elapsed
                *
                self.uncertainty_growth
            ),

            self.max_uncertainty
        )

        confidence = max(

            0.0,

            1.0
            -
            (
                uncertainty
                /
                self.max_uncertainty
            )
        )

        result = {

            "target_time":
                target_minute,

            "position":
                predicted,

            "uncertainty":
                uncertainty,

            "confidence":
                confidence
        }

        if store:

            self.forecast_ledger[
                target_minute
            ] = result

        return result

    # ==================================================
    # SCHEDULE FUTURE FORECASTS
    # ==================================================

    def schedule_forecasts(
        self,
        current_minute,
        horizon=30,
        step=5
    ):

        if self.last_position is None:

            return

        for offset in range(
            step,
            horizon + 1,
            step
        ):

            target = (
                current_minute
                + offset
            )

            self.forecast(
                target,
                store=True
            )

    # ==================================================
    # OBSERVATION
    # ==================================================

    def observe(
        self,
        minute,
        position
    ):

        validation = {

            "forecast_available":
                False,

            "prediction_error":
                None,

            "divergence":
                "NONE",

            "direction_change":
                False,

            "heading_similarity":
                None,

            "behaviour_change":
                "NONE",

            "model_rebuilt":
                False
        }

        # ----------------------------------------------
        # 1. Validate old forecast
        # ----------------------------------------------

        if minute in self.forecast_ledger:

            forecast = \
                self.forecast_ledger.pop(
                    minute
                )

            predicted = \
                forecast["position"]

            error = distance(
                predicted,
                position
            )

            validation[
                "forecast_available"
            ] = True

            validation[
                "prediction_error"
            ] = error

            # ------------------------------------------
            # Error classification
            # ------------------------------------------

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

            validation[
                "divergence"
            ] = divergence

        # ----------------------------------------------
        # 2. Calculate observed velocity
        # ----------------------------------------------

        new_velocity = None

        if self.last_position is not None:

            dt = (
                minute
                -
                self.last_observation_time
            )

            if dt > 0:

                new_velocity = Point(

                    (
                        position.x
                        -
                        self.last_position.x
                    )
                    /
                    dt,

                    (
                        position.y
                        -
                        self.last_position.y
                    )
                    /
                    dt
                )

        # ----------------------------------------------
        # 3. Compare old vs new heading
        # ----------------------------------------------

        direction_change = False

        similarity = None

        if (
            new_velocity is not None
            and
            self.velocity is not None
        ):

            if (
                magnitude(self.velocity)
                > 0.01
                and
                magnitude(new_velocity)
                > 0.01
            ):

                similarity = \
                    cosine_similarity(
                        self.velocity,
                        new_velocity
                    )

                validation[
                    "heading_similarity"
                ] = similarity

                # --------------------------------------
                # Heading change threshold
                #
                # cosine < 0.80 means approximately
                # more than 37 degrees of deviation.
                # --------------------------------------

                if similarity < 0.80:

                    direction_change = True

        validation[
            "direction_change"
        ] = direction_change

        # ----------------------------------------------
        # 4. Behaviour interpretation
        # ----------------------------------------------

        error = validation[
            "prediction_error"
        ]

        if direction_change:

            if (
                error is not None
                and
                error > 15
            ):

                behaviour = \
                    "CONFIRMED BEHAVIOUR CHANGE"

            else:

                behaviour = \
                    "POSSIBLE BEHAVIOUR CHANGE"

        elif (
            error is not None
            and
            error > 15
        ):

            behaviour = \
                "MODEL FAILURE / CAUSE UNKNOWN"

        elif (
            error is not None
            and
            error > 7
        ):

            behaviour = \
                "TRAJECTORY DRIFT"

        else:

            behaviour = "NONE"

        validation[
            "behaviour_change"
        ] = behaviour

        self.behaviour_state = behaviour

        # ----------------------------------------------
        # 5. Rebuild model
        # ----------------------------------------------

        if new_velocity is not None:

            # Keep previous velocity for comparison.

            self.previous_velocity = \
                self.velocity

            # Replace old movement model.

            self.velocity = \
                new_velocity

        if (
            behaviour
            in (
                "CONFIRMED BEHAVIOUR CHANGE",
                "POSSIBLE BEHAVIOUR CHANGE"
            )
        ):

            self.model_state = \
                "OLD MODEL INVALIDATED"

            # Delete forecasts generated by the
            # previous trajectory.

            self.forecast_ledger.clear()

            # New trajectory becomes authoritative.

            self.model_state = \
                "MODEL REBUILT"

            validation[
                "model_rebuilt"
            ] = True

        elif (
            validation["divergence"]
            ==
            "MODEL FAILURE"
        ):

            self.model_state = \
                "MODEL FAILURE"

        else:

            self.model_state = \
                "TRACKING"

        # ----------------------------------------------
        # 6. Save validation history
        # ----------------------------------------------

        self.validation_history.append({

            "time":
                minute,

            "error":
                error,

            "direction_change":
                direction_change,

            "behaviour":
                behaviour
        })

        # ----------------------------------------------
        # 7. Update observation
        # ----------------------------------------------

        self.last_position = position

        self.last_observation_time = minute

        self.heading_change_detected = \
            direction_change

        return validation

    # ==================================================
    # CURRENT FORECAST FOR DISPLAY
    # ==================================================

    def current_prediction(
        self,
        minute
    ):

        return self.forecast(
            minute,
            store=False
        )

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
            0,
            horizon + 1
        ):

            target = (
                current_minute
                + offset
            )

            prediction = \
                self.forecast(
                    target,
                    store=False
                )

            if prediction is None:

                continue

            human = \
                route.position_at(
                    target
                )

            if human is None:

                continue

            separation = distance(

                prediction["position"],

                human
            )

            samples.append({

                "minute":
                    target,

                "separation":
                    separation,

                "confidence":
                    prediction[
                        "confidence"
                    ]
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

        # ----------------------------------------------
        # Safety classification
        # ----------------------------------------------

        if confidence < 0.35:

            state = "UNKNOWN"

        elif separation <= 3:

            state = \
                "CRITICAL ENCOUNTER"

        elif separation <= 7:

            state = \
                "HIGH EXPOSURE"

        elif separation <= 15:

            state = \
                "CAUTION"

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
                if separation <= 15
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

        safe = [

            a

            for a in assessments

            if (
                a["state"]
                == "NO ENCOUNTER"
                and
                a["confidence"]
                >= 0.35
            )
        ]

        if not safe:

            return \
                "WAIT / DO NOT ENTER"

        best = max(

            safe,

            key=lambda x:
                x["minimum_separation"]
        )

        return (
            "ROUTE "
            +
            best["route"]
        )


# ======================================================
# ACTUAL LEOPARD MOVEMENT
# ======================================================

def actual_leopard_position(
    minute
):

    # --------------------------------------------------
    # 0-20:
    # diagonal movement
    # --------------------------------------------------

    if minute <= 20:

        fraction = (
            minute / 20
        )

        return interpolate(

            Point(
                15,
                85
            ),

            Point(
                44,
                56
            ),

            fraction
        )

    # --------------------------------------------------
    # 20-35:
    #
    # LEOPARD TURNS WHILE SENSOR IS BLIND
    # --------------------------------------------------

    if minute <= 35:

        fraction = (

            (minute - 20)
            /
            15
        )

        return interpolate(

            Point(
                44,
                56
            ),

            Point(
                70,
                70
            ),

            fraction
        )

    # --------------------------------------------------
    # 35-45:
    # new trajectory
    # --------------------------------------------------

    fraction = (

        (minute - 35)
        /
        10
    )

    return interpolate(

        Point(
            70,
            70
        ),

        Point(
            85,
            55
        ),

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
# PRINT
# ======================================================

def print_result(
    engine,
    minute,
    actual,
    visible,
    routes,
    validation
):

    prediction = \
        engine.current_prediction(
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
        +
        (
            "VISIBLE"
            if visible
            else
            "BLIND"
        )
    )

    if prediction is None:

        print(
            "  Predicted wildlife: UNKNOWN"
        )

        confidence = 0.0

    else:

        p = prediction["position"]

        print(
            f"  Predicted wildlife: "
            f"({p.x:5.1f}, "
            f"{p.y:5.1f})"
        )

        print(
            f"  Uncertainty: "
            f"{prediction['uncertainty']:5.1f}"
        )

        confidence = \
            prediction["confidence"]

    print(
        f"  Prediction confidence: "
        f"{confidence * 100:5.1f}%"
    )

    # --------------------------------------------------
    # Validation information
    # --------------------------------------------------

    if validation is not None:

        print()

        print(
            "  🔎 MODEL VALIDATION"
        )

        if validation[
            "forecast_available"
        ]:

            print(
                f"  Prediction error: "
                f"{validation['prediction_error']:.1f}"
            )

            print(
                f"  Divergence: "
                f"{validation['divergence']}"
            )

        else:

            print(
                "  Prediction error: "
                "NO PRIOR FORECAST"
            )

        similarity = \
            validation[
                "heading_similarity"
            ]

        if similarity is None:

            print(
                "  Heading comparison: "
                "INSUFFICIENT DATA"
            )

        else:

            print(
                f"  Heading similarity: "
                f"{similarity:.2f}"
            )

        print(
            "  Direction change: "
            +
            (
                "YES"
                if validation[
                    "direction_change"
                ]
                else
                "NO"
            )
        )

        print(
            f"  Behaviour state: "
            f"{validation['behaviour_change']}"
        )

        print(
            f"  Model state: "
            f"{engine.model_state}"
        )

        if validation[
            "model_rebuilt"
        ]:

            print()

            print(
                "  🔄 TRAJECTORY REBUILD"
            )

            print(
                "  Old movement model "
                "invalidated."
            )

            print(
                "  New movement vector "
                "accepted."
            )

    # --------------------------------------------------
    # Routes
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

        if assessment[
            "minimum_separation"
        ] is None:

            print(
                "      Minimum separation: "
                "UNKNOWN"
            )

        else:

            print(
                f"      Minimum separation: "
                f"{assessment['minimum_separation']:.1f}"
            )

        print(
            f"      Confidence: "
            f"{assessment['confidence'] * 100:.1f}% "
            f"("
            f"{confidence_label(assessment['confidence'])}"
            f")"
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
            "HIGH EXPOSURE"
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

    # --------------------------------------------------
    # Recommendation
    # --------------------------------------------------

    recommendation = \
        engine.recommend(
            assessments
        )

    if (
        recommendation
        ==
        "WAIT / DO NOT ENTER"
    ):

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
        +
        recommendation
    )


# ======================================================
# DEMO
# ======================================================

def run_demo():

    print("""
========================================================
             WILD SENTINEL V0.7.2
       BEHAVIOUR CHANGE DETECTION ENGINE
========================================================

ADVERSARIAL TEST

The leopard initially travels diagonally.

At approximately 20 minutes it changes direction
while the sensor is blind.

The engine does NOT know the turn occurred.

The sensor returns at 40 minutes.

V0.7.2 must distinguish:

    NORMAL MOVEMENT
          |
          v
    PREDICTION DRIFT
          |
          v
    MODEL FAILURE
          |
          v
    BEHAVIOUR CHANGE
          |
          v
    MODEL REBUILD

========================================================
""")

    engine = \
        WildSentinelV072()

    # --------------------------------------------------
    # Human routes
    # --------------------------------------------------

    route_a = HumanRoute(

        "A",

        [

            (
                0,
                Point(
                    5,
                    95
                )
            ),

            (
                15,
                Point(
                    15,
                    85
                )
            ),

            (
                30,
                Point(
                    20,
                    65
                )
            ),

            (
                45,
                Point(
                    20,
                    40
                )
            )
        ]
    )

    route_b = HumanRoute(

        "B",

        [

            (
                0,
                Point(
                    5,
                    95
                )
            ),

            (
                15,
                Point(
                    30,
                    70
                )
            ),

            (
                25,
                Point(
                    50,
                    50
                )
            ),

            (
                35,
                Point(
                    70,
                    30
                )
            ),

            (
                45,
                Point(
                    90,
                    10
                )
            )
        ]
    )

    route_c = HumanRoute(

        "C",

        [

            (
                0,
                Point(
                    5,
                    95
                )
            ),

            (
                15,
                Point(
                    5,
                    60
                )
            ),

            (
                25,
                Point(
                    35,
                    65
                )
            ),

            (
                35,
                Point(
                    65,
                    70
                )
            ),

            (
                45,
                Point(
                    85,
                    55
                )
            )
        ]
    )

    routes = [

        route_a,
        route_b,
        route_c
    ]

    # --------------------------------------------------
    # IMPORTANT FIX
    #
    # At 10 min the engine explicitly creates a
    # 15-minute forecast BEFORE the 15-minute
    # observation arrives.
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

        validation = None

        # ----------------------------------------------
        # SENSOR OBSERVATION
        # ----------------------------------------------

        if visible:

            validation = \
                engine.observe(

                    minute,

                    actual
                )

            # ------------------------------------------
            # Schedule future forecasts after updating
            # the movement model.
            # ------------------------------------------

            engine.schedule_forecasts(

                minute,

                horizon=30,

                step=5
            )

        # ----------------------------------------------
        # BLIND PERIOD
        # ----------------------------------------------

        print_result(

            engine,

            minute,

            actual,

            visible,

            routes,

            validation
        )

    print("""
========================================================
                 V0.7.2 TEST COMPLETE
========================================================

WHAT TO LOOK FOR

At 10 minutes:

    Prediction available.

At 15 minutes:

    Prediction error should be approximately 0.

    Direction change:
        NO

At 20-35 minutes:

    Sensor:
        BLIND

    Old trajectory continues.

    Uncertainty increases.

    The engine does NOT pretend to know the
    leopard has turned.

At 40 minutes:

    Sensor:
        VISIBLE

    Prediction error should become LARGE.

    Direction comparison should reveal that the
    observed movement is inconsistent with the
    previous trajectory.

    Behaviour state should become:

        CONFIRMED BEHAVIOUR CHANGE

    or, depending on the measured geometry:

        MODEL FAILURE / CAUSE UNKNOWN

    The old model should be invalidated.

    A new velocity vector should be calculated.

    Future route risk should then use the
    rebuilt trajectory.

========================================================

V0.7.2 PRINCIPLE

The system must distinguish:

    "I don't know where the animal is."

from:

    "I know where I predicted it would be,
     and the new evidence tells me that prediction
     is no longer trustworthy."

That distinction is fundamental to Wild Sentinel.

========================================================

NEXT:

V0.8 can introduce INDIRECT EVIDENCE.

The engine will attempt to detect that something
may have changed during sensor blindness using
signals such as:

    movement anomalies
    prey/activity changes
    repeated sensor disturbances
    environmental context
    human movement changes

WITHOUT requiring direct visual confirmation.

========================================================
""")


if __name__ == "__main__":

    run_demo()

