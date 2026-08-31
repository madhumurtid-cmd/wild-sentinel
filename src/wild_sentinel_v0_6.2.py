"""
========================================================
             WILD SENTINEL V0.6.2
          ENCOUNTER INTELLIGENCE ENGINE
========================================================

V0.6.2 introduces:

1. Wildlife movement prediction
2. Human route movement
3. Minimum predicted separation
4. Time-to-encounter
5. Proximity classification
6. Confidence classification
7. Critical encounter detection
8. Confidence-aware recommendations
9. Explicit UNKNOWN state
10. Safe failure when data is unavailable

IMPORTANT:
This is a simulation prototype.
It is NOT a real-world wildlife safety system.
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
    """Calculate distance between two points."""

    return hypot(
        a.x - b.x,
        a.y - b.y
    )


def interpolate(a, b, fraction):
    """Calculate a point between A and B."""

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
        """
        Return estimated human position
        at a particular minute.
        """

        if not self.waypoints:
            return None

        # Before route starts.
        if minute <= self.waypoints[0][0]:
            return self.waypoints[0][1]

        # Find the active route segment.
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

        # After route ends.
        return self.waypoints[-1][1]


# ======================================================
# WILD SENTINEL ENGINE
# ======================================================

class WildSentinelV062:

    def __init__(self):

        # ----------------------------------------------
        # Wildlife state
        # ----------------------------------------------

        self.last_position = None

        self.velocity = Point(
            0.0,
            0.0
        )

        self.last_observation_time = None

        # ----------------------------------------------
        # Prediction model
        # ----------------------------------------------

        self.base_uncertainty = 5.0

        self.uncertainty_growth = 1.75

        self.max_uncertainty = 35.0

        # ----------------------------------------------
        # Safety threshold
        # ----------------------------------------------

        self.minimum_confidence = 0.35

    # ==================================================
    # OBSERVE WILDLIFE
    # ==================================================

    def observe(
        self,
        minute,
        x,
        y
    ):
        """
        Update wildlife position and movement vector.

        This function should ONLY be called when
        a sensor actually observes the animal.
        """

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
    # PREDICT WILDLIFE POSITION
    # ==================================================

    def predict(
        self,
        minute
    ):
        """
        Predict wildlife position.

        Returns:

            predicted_position
            uncertainty
            confidence
        """

        # No observation has ever occurred.

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

        return (
            predicted,
            uncertainty,
            confidence
        )

    # ==================================================
    # PROXIMITY
    # ==================================================

    def classify_proximity(
        self,
        separation
    ):

        if separation is None:
            return "UNKNOWN"

        if separation <= 1.0:
            return "CRITICAL"

        if separation <= 3.0:
            return "VERY CLOSE"

        if separation <= 7.0:
            return "CLOSE"

        if separation <= 15.0:
            return "NEAR"

        return "DISTANT"

    # ==================================================
    # CONFIDENCE
    # ==================================================

    def classify_confidence(
        self,
        confidence
    ):

        percentage = confidence * 100

        if percentage >= 75:
            return "HIGH"

        if percentage >= 50:
            return "MEDIUM"

        if percentage >= 35:
            return "LOW"

        return "VERY LOW"

    # ==================================================
    # ENCOUNTER ANALYSIS
    # ==================================================

    def analyse_route(
        self,
        route,
        current_minute,
        horizon=15
    ):
        """
        Examine future human/wildlife positions.

        The model looks one minute at a time over
        the next 'horizon' minutes.

        It identifies the closest predicted approach.
        """

        samples = []

        for offset in range(
            0,
            horizon + 1
        ):

            future_minute = (
                current_minute
                + offset
            )

            wildlife, uncertainty, confidence = \
                self.predict(
                    future_minute
                )

            human = route.position_at(
                future_minute
            )

            # No wildlife prediction.
            if wildlife is None:
                continue

            # No human route position.
            if human is None:
                continue

            separation = distance(
                wildlife,
                human
            )

            samples.append({

                "minute":
                    future_minute,

                "wildlife":
                    wildlife,

                "human":
                    human,

                "separation":
                    separation,

                "uncertainty":
                    uncertainty,

                "confidence":
                    confidence
            })

        # ------------------------------------------------
        # SAFE FAILURE
        # ------------------------------------------------

        if not samples:

            return {

                "route":
                    route.name,

                "minimum_separation":
                    None,

                "time_to_encounter":
                    None,

                "proximity":
                    "UNKNOWN",

                "confidence":
                    0.0,

                "confidence_class":
                    "VERY LOW",

                "encounter":
                    False,

                "critical":
                    False,

                "state":
                    "UNKNOWN",

                "samples":
                    []
            }

        # ------------------------------------------------
        # Find closest predicted approach.
        # ------------------------------------------------

        closest = min(

            samples,

            key=lambda item:
                item["separation"]
        )

        minimum_separation = \
            closest["separation"]

        confidence = \
            closest["confidence"]

        # ------------------------------------------------
        # Encounter thresholds
        # ------------------------------------------------

        # <= 3 units:
        # Potentially direct encounter.

        critical = (
            minimum_separation <= 3.0
        )

        # <= 7 units:
        # Significant wildlife exposure.

        encounter = (
            minimum_separation <= 7.0
        )

        proximity = \
            self.classify_proximity(
                minimum_separation
            )

        confidence_class = \
            self.classify_confidence(
                confidence
            )

        # ------------------------------------------------
        # STATE
        # ------------------------------------------------

        if critical:

            if confidence >= \
                    self.minimum_confidence:

                state = \
                    "CRITICAL ENCOUNTER"

            else:

                state = \
                    "POTENTIAL CRITICAL"

        elif encounter:

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

            "minimum_separation":
                minimum_separation,

            "time_to_encounter":
                closest["minute"]
                if encounter
                else None,

            "proximity":
                proximity,

            "confidence":
                confidence,

            "confidence_class":
                confidence_class,

            "encounter":
                encounter,

            "critical":
                critical,

            "state":
                state,

            "samples":
                samples
        }

    # ==================================================
    # ROUTE RECOMMENDATION
    # ==================================================

    def recommend(
        self,
        assessments
    ):
        """
        Conservative route selection.

        Never select:

            UNKNOWN
            CRITICAL ENCOUNTER
            POTENTIAL CRITICAL
            HIGH EXPOSURE
            POTENTIAL EXPOSURE
        """

        usable = [

            assessment

            for assessment in assessments

            if assessment["state"]
            not in (

                "UNKNOWN",

                "CRITICAL ENCOUNTER",

                "POTENTIAL CRITICAL",

                "HIGH EXPOSURE",

                "POTENTIAL EXPOSURE"
            )
        ]

        # Nothing usable.

        if not usable:

            return (
                "WAIT / DO NOT ENTER"
            )

        # Remove low-confidence choices.

        confident = [

            assessment

            for assessment in usable

            if assessment["confidence"]
            >= self.minimum_confidence
        ]

        if not confident:

            return (
                "WAIT / DO NOT ENTER"
            )

        # Choose route with greatest
        # minimum separation.

        best = max(

            confident,

            key=lambda assessment:
                assessment[
                    "minimum_separation"
                ]
        )

        return (
            "ROUTE "
            + best["route"]
        )


# ======================================================
# DISPLAY
# ======================================================

def print_result(
    engine,
    minute,
    actual,
    sensor_visible,
    routes
):

    predicted, uncertainty, confidence = \
        engine.predict(
            minute
        )

    print()
    print("-" * 68)

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

    assessments = []

    # --------------------------------------------------
    # Evaluate every route.
    # --------------------------------------------------

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
            f"      Proximity: "
            f"{assessment['proximity']}"
        )

        print(
            f"      Confidence: "
            f"{assessment['confidence'] * 100:.1f}% "
            f"({assessment['confidence_class']})"
        )

        encounter_time = \
            assessment[
                "time_to_encounter"
            ]

        if encounter_time is not None:

            delta = (
                encounter_time
                - minute
            )

            print(
                f"      Encounter window: "
                f"~{encounter_time} min "
                f"(in ~{delta} min)"
            )

    # --------------------------------------------------
    # Warnings
    # --------------------------------------------------

    dangerous = [

        assessment

        for assessment in assessments

        if assessment.get("state")
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
            "  🚨 WILDLIFE "
            "ENCOUNTER WARNING"
        )

        for assessment in dangerous:

            print(
                f"  ROUTE "
                f"{assessment['route']}: "
                f"{assessment['state']}"
            )

            if assessment[
                "time_to_encounter"
            ] is not None:

                print(
                    f"      Estimated time: "
                    f"{assessment['time_to_encounter']} min"
                )

                print(
                    f"      Minimum separation: "
                    f"{assessment['minimum_separation']:.1f}"
                )

    # --------------------------------------------------
    # Recommendation
    # --------------------------------------------------

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
# DEMONSTRATION
# ======================================================

def run_demo():

    print("""
========================================================
             WILD SENTINEL V0.6.2
          ENCOUNTER INTELLIGENCE ENGINE
========================================================

SIMULATION

Leopard:
    Moves diagonally across landscape.

Sensor:
    Visible at 10 and 15 minutes.
    Blind from 20 to 35 minutes.
    Visible again at 40 minutes.

Wild Sentinel must:

    ✓ Predict wildlife movement
    ✓ Predict human movement
    ✓ Compare future positions
    ✓ Find minimum separation
    ✓ Identify encounter windows
    ✓ Classify proximity
    ✓ Track prediction confidence
    ✓ Avoid dangerous routes
    ✓ Fail safely when confidence is low

========================================================
""")

    engine = WildSentinelV062()

    # ==================================================
    # ACTUAL LEOPARD TRACK
    # ==================================================

    actual_track = {

        0:
            Point(15, 85),

        5:
            Point(22.2, 77.8),

        10:
            Point(29.5, 70.5),

        15:
            Point(36.7, 63.3),

        20:
            Point(44.0, 56.0),

        25:
            Point(51.2, 48.8),

        30:
            Point(58.5, 41.5),

        35:
            Point(65.7, 34.3),

        40:
            Point(73.0, 27.0),

        45:
            Point(80.2, 19.8)
    }

    # ==================================================
    # SENSOR VISIBILITY
    # ==================================================

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

    # ==================================================
    # HUMAN ROUTE A
    # ==================================================

    route_a = HumanRoute(

        "A",

        [

            (
                0,
                Point(5, 95)
            ),

            (
                15,
                Point(15, 85)
            ),

            (
                30,
                Point(20, 65)
            ),

            (
                45,
                Point(20, 40)
            )
        ]
    )

    # ==================================================
    # HUMAN ROUTE B
    #
    # Deliberately crosses the wildlife corridor.
    # ==================================================

    route_b = HumanRoute(

        "B",

        [

            (
                0,
                Point(5, 95)
            ),

            (
                15,
                Point(30, 70)
            ),

            (
                25,
                Point(50, 50)
            ),

            (
                35,
                Point(70, 30)
            ),

            (
                45,
                Point(90, 10)
            )
        ]
    )

    # ==================================================
    # HUMAN ROUTE C
    # ==================================================

    route_c = HumanRoute(

        "C",

        [

            (
                0,
                Point(5, 95)
            ),

            (
                15,
                Point(5, 60)
            ),

            (
                30,
                Point(5, 30)
            ),

            (
                45,
                Point(5, 10)
            )
        ]
    )

    routes = [

        route_a,

        route_b,

        route_c
    ]

    # ==================================================
    # RUN SIMULATION
    # ==================================================

    for minute, actual \
            in actual_track.items():

        visible = \
            sensor_visible[minute]

        # IMPORTANT:
        #
        # Only provide the engine with wildlife
        # observations when the sensor is visible.

        if visible:

            engine.observe(

                minute,

                actual.x,

                actual.y
            )

        print_result(

            engine,

            minute,

            actual,

            visible,

            routes
        )

    print("""
========================================================
                 V0.6.2 TEST COMPLETE
========================================================

IMPORTANT RESULT:

V0.6.2 now separates:

    PROXIMITY
    TIMING
    CONFIDENCE
    ENCOUNTER STATE

The next challenge is V0.7:

    The leopard will deliberately change direction
    while the sensors are blind.

Wild Sentinel must detect:

    "My prediction is becoming unreliable."

========================================================
""")


# ======================================================
# ENTRY POINT
# ======================================================

if __name__ == "__main__":

    run_demo()