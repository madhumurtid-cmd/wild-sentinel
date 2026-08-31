"""
========================================================
             WILD SENTINEL V0.8
          INDIRECT EVIDENCE ENGINE
========================================================

Purpose
-------

V0.8 tests whether Wild Sentinel can recognise that a
wildlife movement model may be becoming unreliable
WITHOUT direct visual confirmation.

This is a simulation.

It does NOT produce real-world wildlife probabilities.

Core principles
---------------

1. Direct observation is strongest evidence.
2. Indirect evidence can increase suspicion.
3. Multiple independent weak signals can combine.
4. Indirect evidence must NOT be treated as proof.
5. Confidence must decay during sensor blindness.
6. Route recommendations must fail safely.
7. A behaviour-change suspicion can exist before
   direct confirmation.

Evidence streams
----------------

- Movement anomaly
- Sensor disturbance
- Prey/activity anomaly
- Environmental context
- Human movement

========================================================
"""


import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ========================================================
# CONFIGURATION
# ========================================================

BLIND_START = 20
BLIND_END = 35

MAX_UNCERTAINTY = 35.0

DIRECT_CONFIDENCE = 85.7

EVIDENCE_THRESHOLD = 35.0
STRONG_EVIDENCE_THRESHOLD = 60.0
CRITICAL_EVIDENCE_THRESHOLD = 80.0


# ========================================================
# BASIC GEOMETRY
# ========================================================

Point = Tuple[float, float]


def distance(a: Point, b: Point) -> float:
    return math.sqrt(
        (a[0] - b[0]) ** 2 +
        (a[1] - b[1]) ** 2
    )


def interpolate(a: Point, b: Point, fraction: float) -> Point:
    return (
        a[0] + (b[0] - a[0]) * fraction,
        a[1] + (b[1] - a[1]) * fraction
    )


def velocity(a: Point, b: Point, dt: float) -> Point:
    if dt <= 0:
        return (0.0, 0.0)

    return (
        (b[0] - a[0]) / dt,
        (b[1] - a[1]) / dt
    )


def predict_position(
    position: Point,
    movement_vector: Point,
    elapsed: float
) -> Point:

    return (
        position[0] + movement_vector[0] * elapsed,
        position[1] + movement_vector[1] * elapsed
    )


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


# ========================================================
# ROUTES
# ========================================================

ROUTES: Dict[str, List[Point]] = {

    "A": [
        (10, 10),
        (25, 25),
        (40, 40),
        (55, 55),
        (70, 70),
        (85, 85),
    ],

    "B": [
        (10, 90),
        (25, 75),
        (40, 60),
        (55, 45),
        (70, 30),
        (85, 15),
    ],

    "C": [
        (10, 50),
        (25, 50),
        (40, 50),
        (55, 50),
        (70, 50),
        (85, 50),
    ],
}


# ========================================================
# HUMAN MOVEMENT
# ========================================================

def human_position(route: str, minute: float) -> Point:

    points = ROUTES[route]

    fraction = clamp(minute / 60.0, 0.0, 1.0)

    index_float = fraction * (len(points) - 1)

    index = int(index_float)

    if index >= len(points) - 1:
        return points[-1]

    local_fraction = index_float - index

    return interpolate(
        points[index],
        points[index + 1],
        local_fraction
    )


# ========================================================
# SIMULATED LEOPARD MOVEMENT
# ========================================================

def actual_leopard_position(minute: float) -> Point:

    # Phase 1:
    # Straight diagonal movement.
    if minute <= 20:

        start = (15.0, 85.0)
        end = (44.0, 56.0)

        fraction = minute / 20.0

        return interpolate(start, end, fraction)

    # Phase 2:
    # Leopard changes direction during blindness.
    #
    # It moves toward the lower-right initially,
    # then turns and moves toward the upper-right.

    if minute <= 40:

        start = (44.0, 56.0)
        end = (77.5, 62.5)

        fraction = (minute - 20.0) / 20.0

        return interpolate(start, end, fraction)

    # Phase 3
    # Continue after sensor recovery.

    start = (77.5, 62.5)
    end = (85.0, 55.0)

    fraction = clamp((minute - 40.0) / 5.0, 0.0, 1.0)

    return interpolate(start, end, fraction)


# ========================================================
# SENSOR MODEL
# ========================================================

def sensor_visible(minute: int) -> bool:

    return minute in (10, 15, 40, 45)


# ========================================================
# UNCERTAINTY MODEL
# ========================================================

def uncertainty_at(minute: int) -> float:

    if sensor_visible(minute):
        return 5.0

    if minute < 10:
        return 35.0

    elapsed = minute - 15

    return clamp(
        5.0 + elapsed * 1.75,
        5.0,
        MAX_UNCERTAINTY
    )


def confidence_from_uncertainty(
    uncertainty: float
) -> float:

    if uncertainty >= MAX_UNCERTAINTY:
        return 0.0

    return clamp(
        100.0 -
        (uncertainty / MAX_UNCERTAINTY) * 100.0,
        0.0,
        100.0
    )


# ========================================================
# MOVEMENT MODEL
# ========================================================

@dataclass
class MovementModel:

    position: Optional[Point] = None
    vector: Optional[Point] = None
    timestamp: Optional[int] = None

    valid: bool = False

    def update(
        self,
        position: Point,
        timestamp: int
    ):

        if self.position is not None and self.timestamp is not None:

            dt = timestamp - self.timestamp

            if dt > 0:
                self.vector = velocity(
                    self.position,
                    position,
                    dt
                )

        self.position = position
        self.timestamp = timestamp
        self.valid = self.vector is not None

    def predict(self, timestamp: int) -> Optional[Point]:

        if not self.valid:
            return None

        if self.position is None:
            return None

        if self.timestamp is None:
            return None

        elapsed = timestamp - self.timestamp

        return predict_position(
            self.position,
            self.vector,
            elapsed
        )

    def rebuild(
        self,
        position: Point,
        timestamp: int
    ):

        self.position = position
        self.timestamp = timestamp
        self.valid = False


# ========================================================
# INDIRECT EVIDENCE
# ========================================================

@dataclass
class Evidence:

    movement_anomaly: float = 0.0
    sensor_disturbance: float = 0.0
    prey_anomaly: float = 0.0
    environmental_context: float = 0.0
    human_movement: float = 0.0

    @property
    def total(self) -> float:

        weighted = (

            self.movement_anomaly * 0.30 +

            self.sensor_disturbance * 0.20 +

            self.prey_anomaly * 0.20 +

            self.environmental_context * 0.10 +

            self.human_movement * 0.20
        )

        return clamp(weighted, 0.0, 100.0)


# ========================================================
# INDIRECT EVIDENCE SCENARIO
# ========================================================

def generate_indirect_evidence(
    minute: int
) -> Evidence:

    evidence = Evidence()

    # ----------------------------------------------------
    # 20 minutes
    # Sensor blindness begins.
    # ----------------------------------------------------

    if minute >= 22:

        evidence.sensor_disturbance = 25.0

    # ----------------------------------------------------
    # 25 minutes
    # Prey/activity anomaly.
    # ----------------------------------------------------

    if minute >= 25:

        evidence.prey_anomaly = 55.0

    # ----------------------------------------------------
    # 28 minutes
    # Environmental/activity signal strengthens.
    # ----------------------------------------------------

    if minute >= 28:

        evidence.environmental_context = 60.0

    # ----------------------------------------------------
    # 30 minutes
    # Human movement enters area where the old model
    # predicted wildlife movement.
    # ----------------------------------------------------

    if minute >= 30:

        evidence.human_movement = 70.0

    # ----------------------------------------------------
    # 32 minutes
    # Multiple sensor disturbances.
    # ----------------------------------------------------

    if minute >= 32:

        evidence.sensor_disturbance = 70.0

    # ----------------------------------------------------
    # At 35 minutes, movement anomaly becomes stronger.
    # Still indirect — not direct proof.
    # ----------------------------------------------------

    if minute >= 35:

        evidence.movement_anomaly = 65.0

    return evidence


# ========================================================
# EVIDENCE CLASSIFICATION
# ========================================================

def evidence_state(score: float) -> str:

    if score >= CRITICAL_EVIDENCE_THRESHOLD:

        return "HIGH INDIRECT EVIDENCE"

    if score >= STRONG_EVIDENCE_THRESHOLD:

        return "BEHAVIOUR CHANGE SUSPECTED"

    if score >= EVIDENCE_THRESHOLD:

        return "INDIRECT EVIDENCE INCREASING"

    return "NO SIGNIFICANT INDIRECT EVIDENCE"


# ========================================================
# PREDICTION VALIDATION
# ========================================================

@dataclass
class ValidationResult:

    error: Optional[float]

    divergence: str

    model_state: str


def validate_prediction(
    predicted: Optional[Point],
    actual: Point
) -> ValidationResult:

    if predicted is None:

        return ValidationResult(
            error=None,
            divergence="NO FORECAST",
            model_state="NO MODEL"
        )

    error = distance(predicted, actual)

    if error < 2.0:

        return ValidationResult(
            error=error,
            divergence="NONE",
            model_state="TRACKING"
        )

    if error < 10.0:

        return ValidationResult(
            error=error,
            divergence="PREDICTION DRIFT",
            model_state="TRACKING"
        )

    if error < 25.0:

        return ValidationResult(
            error=error,
            divergence="SIGNIFICANT DIVERGENCE",
            model_state="MODEL AT RISK"
        )

    return ValidationResult(
        error=error,
        divergence="MODEL FAILURE",
        model_state="MODEL FAILURE"
    )


# ========================================================
# ROUTE ANALYSIS
# ========================================================

def route_minimum_separation(
    route: str,
    wildlife_position: Point
) -> float:

    points = ROUTES[route]

    minimum = float("inf")

    for point in points:

        d = distance(
            point,
            wildlife_position
        )

        minimum = min(minimum, d)

    return minimum


def proximity_state(separation: float) -> str:

    if separation < 2.0:
        return "CRITICAL"

    if separation < 5.0:
        return "VERY CLOSE"

    if separation < 10.0:
        return "CLOSE"

    if separation < 20.0:
        return "NEAR"

    return "DISTANT"


def route_risk(
    separation: float,
    confidence: float
) -> Tuple[str, float]:

    if confidence < 15.0:

        return "UNKNOWN", 0.0

    if separation < 2.0:

        risk = 95.0

        if confidence < 50:
            risk *= confidence / 50.0

        return "CRITICAL ENCOUNTER", risk

    if separation < 5.0:

        risk = 80.0 * (confidence / 100.0)

        return "POTENTIAL EXPOSURE", risk

    if separation < 10.0:

        risk = 55.0 * (confidence / 100.0)

        return "CAUTION", risk

    return "NO ENCOUNTER", 5.0


# ========================================================
# SAFETY DECISION
# ========================================================

def choose_route(
    assessments: Dict[str, Dict],
    evidence_score: float
) -> str:

    # Strong indirect evidence means we become more
    # conservative even if no direct visual exists.

    if evidence_score >= STRONG_EVIDENCE_THRESHOLD:

        safe_routes = [
            route
            for route, assessment in assessments.items()
            if assessment["state"] == "NO ENCOUNTER"
            and assessment["confidence"] >= 60.0
        ]

        if safe_routes:

            return min(
                safe_routes,
                key=lambda r: assessments[r]["risk"]
            )

        return "WAIT / DO NOT ENTER"

    safe_routes = [
        route
        for route, assessment in assessments.items()
        if assessment["state"] == "NO ENCOUNTER"
        and assessment["confidence"] >= 50.0
    ]

    if not safe_routes:

        return "WAIT / DO NOT ENTER"

    return min(
        safe_routes,
        key=lambda r: assessments[r]["risk"]
    )


# ========================================================
# PRINT HELPERS
# ========================================================

def print_separator():
    print("-" * 68)


def confidence_label(confidence: float) -> str:

    if confidence >= 70:
        return "HIGH"

    if confidence >= 40:
        return "MEDIUM"

    if confidence >= 15:
        return "LOW"

    return "VERY LOW"


def print_evidence(evidence: Evidence):

    print()
    print("  🔎 INDIRECT EVIDENCE")

    print(
        f"      Movement anomaly:       "
        f"{evidence.movement_anomaly:5.1f}"
    )

    print(
        f"      Sensor disturbance:     "
        f"{evidence.sensor_disturbance:5.1f}"
    )

    print(
        f"      Prey/activity anomaly:  "
        f"{evidence.prey_anomaly:5.1f}"
    )

    print(
        f"      Environmental context:  "
        f"{evidence.environmental_context:5.1f}"
    )

    print(
        f"      Human movement:         "
        f"{evidence.human_movement:5.1f}"
    )

    print(
        f"      --------------------------------"
    )

    print(
        f"      Evidence fusion score:  "
        f"{evidence.total:5.1f}"
    )

    print(
        f"      Evidence state: "
        f"{evidence_state(evidence.total)}"
    )


# ========================================================
# MAIN DEMONSTRATION
# ========================================================

def run_demo():

    print()
    print("=" * 56)
    print("             WILD SENTINEL V0.8")
    print("          INDIRECT EVIDENCE ENGINE")
    print("=" * 56)

    print()
    print("ADVERSARIAL TEST")
    print()
    print("Leopard initially follows a diagonal trajectory.")
    print()
    print("At approximately 20 minutes it changes direction")
    print("while the direct sensor is blind.")
    print()
    print("The engine does NOT know the turn occurred.")
    print()
    print("Indirect evidence begins appearing during blindness.")
    print()
    print("Direct sensor returns at 40 minutes.")
    print()
    print("V0.8 must determine whether indirect evidence")
    print("is sufficient to raise a pre-confirmation warning.")
    print()
    print("=" * 56)

    model = MovementModel()

    previous_actual: Optional[Point] = None
    previous_time: Optional[int] = None

    for minute in range(0, 46, 5):

        print()
        print_separator()

        actual = actual_leopard_position(minute)

        visible = sensor_visible(minute)

        uncertainty = uncertainty_at(minute)

        confidence = confidence_from_uncertainty(
            uncertainty
        )

        # ------------------------------------------------
        # Forecast BEFORE updating the model.
        #
        # This is important.
        #
        # The forecast represents what Wild Sentinel
        # believed before receiving the current evidence.
        # ------------------------------------------------

        predicted = model.predict(minute)

        # ------------------------------------------------
        # Direct observation
        # ------------------------------------------------

        if visible:

            model_validation = validate_prediction(
                predicted,
                actual
            )

            model.update(
                actual,
                minute
            )

        else:

            model_validation = None

        # ------------------------------------------------
        # Display
        # ------------------------------------------------

        print(f"{minute:02d} min")

        print(
            f"  Actual leopard: "
            f"({actual[0]:5.1f}, {actual[1]:5.1f})"
        )

        print(
            f"  Sensor: "
            f"{'VISIBLE' if visible else 'BLIND'}"
        )

        if predicted is None:

            print(
                "  Predicted wildlife: UNKNOWN"
            )

        else:

            print(
                f"  Predicted wildlife: "
                f"({predicted[0]:5.1f}, "
                f"{predicted[1]:5.1f})"
            )

        print(
            f"  Uncertainty: "
            f"{uncertainty:5.1f}"
        )

        print(
            f"  Prediction confidence: "
            f"{confidence:5.1f}%"
        )

        # ------------------------------------------------
        # Validation
        # ------------------------------------------------

        if visible:

            print()

            print("  🔎 MODEL VALIDATION")

            if model_validation.error is None:

                print(
                    "      Prediction error: "
                    "NO PRIOR FORECAST"
                )

            else:

                print(
                    f"      Prediction error: "
                    f"{model_validation.error:5.1f}"
                )

            print(
                f"      Divergence: "
                f"{model_validation.divergence}"
            )

            print(
                f"      Model state: "
                f"{model_validation.model_state}"
            )

        # ------------------------------------------------
        # Indirect evidence
        # ------------------------------------------------

        evidence = generate_indirect_evidence(
            minute
        )

        if minute >= 20:

            print_evidence(evidence)

        # ------------------------------------------------
        # Route analysis
        # ------------------------------------------------

        assessments = {}

        # If we have no prediction, route analysis is
        # intentionally UNKNOWN.

        for route in ROUTES:

            if predicted is None:

                assessments[route] = {
                    "state": "UNKNOWN",
                    "risk": 0.0,
                    "separation": None,
                    "confidence": 0.0
                }

                continue

            separation = route_minimum_separation(
                route,
                predicted
            )

            state, risk = route_risk(
                separation,
                confidence
            )

            assessments[route] = {
                "state": state,
                "risk": risk,
                "separation": separation,
                "confidence": confidence
            }

        print()

        for route, assessment in assessments.items():

            print(
                f"  ROUTE {route}"
            )

            print(
                f"      State: "
                f"{assessment['state']}"
            )

            if assessment["separation"] is None:

                print(
                    "      Minimum separation: UNKNOWN"
                )

            else:

                print(
                    f"      Minimum separation: "
                    f"{assessment['separation']:5.1f}"
                )

                print(
                    f"      Proximity: "
                    f"{proximity_state(assessment['separation'])}"
                )

            print(
                f"      Confidence: "
                f"{assessment['confidence']:5.1f}% "
                f"({confidence_label(assessment['confidence'])})"
            )

        # ------------------------------------------------
        # Indirect warning
        # ------------------------------------------------

        if evidence.total >= EVIDENCE_THRESHOLD:

            print()

            print(
                "  ⚠️ INDIRECT BEHAVIOUR WARNING"
            )

            print(
                f"  Evidence score: "
                f"{evidence.total:.1f}"
            )

            print(
                f"  State: "
                f"{evidence_state(evidence.total)}"
            )

            print(
                "  Direct wildlife confirmation "
                "is NOT available."
            )

            print(
                "  Old trajectory should NOT be "
                "treated as ground truth."
            )

        # ------------------------------------------------
        # Safety decision
        # ------------------------------------------------

        recommendation = choose_route(
            assessments,
            evidence.total
        )

        if recommendation == "WAIT / DO NOT ENTER":

            print()

            print(
                "  ⚠️ SAFETY DECISION"
            )

            print(
                "  Wild Sentinel cannot confidently "
                "identify a sufficiently safe route."
            )

            print(
                "  >>> RECOMMENDATION: "
                "WAIT / DO NOT ENTER"
            )

        else:

            print()

            print(
                f"  >>> RECOMMENDATION: "
                f"ROUTE {recommendation}"
            )

        # ------------------------------------------------
        # Save actual history
        # ------------------------------------------------

        previous_actual = actual
        previous_time = minute

    # ====================================================
    # TEST SUMMARY
    # ====================================================

    print()
    print()
    print("=" * 56)
    print("                 V0.8 TEST COMPLETE")
    print("=" * 56)

    print()
    print("V0.8 HAS TESTED:")

    print()
    print("    [✓] Direct wildlife tracking")
    print()
    print("    [✓] Sensor blindness")
    print()
    print("    [✓] Prediction confidence decay")
    print()
    print("    [✓] Movement anomaly evidence")
    print()
    print("    [✓] Sensor disturbance evidence")
    print()
    print("    [✓] Prey/activity anomaly")
    print()
    print("    [✓] Environmental context")
    print()
    print("    [✓] Human movement")
    print()
    print("    [✓] Evidence fusion")
    print()
    print("    [✓] Behaviour-change suspicion")
    print()
    print("    [✓] Conservative route selection")
    print()
    print("    [✓] Fail-safe behaviour")
    print()

    print("=" * 56)

    print()
    print("KEY PRINCIPLE")
    print()
    print("Wild Sentinel does NOT claim:")
    print()
    print('    "The leopard is definitely here."')
    print()
    print("Instead it can say:")
    print()
    print('    "Multiple indirect signals are')
    print('     inconsistent with the current model."')
    print()
    print('    "Behaviour change is suspected."')
    print()
    print('    "Do not rely on the stale trajectory."')
    print()

    print("=" * 56)

    print()
    print("IMPORTANT:")
    print()
    print("This remains a simulation.")
    print()
    print("The evidence scores are NOT real-world")
    print("wildlife probabilities.")
    print()
    print("Real deployment would require validated")
    print("sensor data, ecological data, field testing,")
    print("false-positive/false-negative analysis and")
    print("appropriate safety review.")

    print("=" * 56)


# ========================================================
# ENTRY POINT
# ========================================================

if __name__ == "__main__":
    run_demo()