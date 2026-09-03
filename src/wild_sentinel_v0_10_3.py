"""
WILD SENTINEL V0.10.3
END-TO-END SENSOR-BLIND SCENARIO ENGINE

V0.10.3 builds the first end-to-end scenario layer above V0.10.2.

ARCHITECTURE:

    V0.9.9.4
        Geometry + TTC
            ↓
    V0.10.1
        Temporal Encounter State
            ↓
    V0.10.2
        Safety Arbitration
            ↓
    V0.10.3
        Scenario / Observation / Blind-Period Prediction

CORE V0.10.3 PRINCIPLES:

    1. GROUND TRUTH IS NEVER AN ENGINE INPUT DURING SENSOR BLINDNESS.
    2. DURING BLINDNESS, ONLY LAST OBSERVATION + MOTION + ELAPSED TIME
       MAY DRIVE THE PREDICTION.
    3. UNCERTAINTY GROWS WHILE THE ANIMAL IS UNOBSERVED.
    4. BLIND IS NOT SAFE.
    5. PREDICTION IS NOT OBSERVATION.
    6. A LATER OBSERVATION MAY VALIDATE OR REFUTE THE BLIND-PERIOD
       PREDICTION.
    7. FINAL OBSERVED CONFLICT MUST PRODUCE DO_NOT_ENTER.
    8. PREDICTION ERROR IS REPORTED ONLY WHEN AN OBSERVATION BECOMES
       AVAILABLE; hidden ground truth is not used to calculate it.

Reference scenario:

    Route A: y = 50

    Observed:
        t=0   (50,20)
        t=5   (50,25)
        t=10  (50,30)

    SENSOR BLIND:
        t=15  predicted from last observation
        t=20  predicted only
        t=25  predicted only

    Observed again:
        t=30  (50,49)

The engine must predict continued approach during the blind period,
retain an uncleared safety state, and detect the final in-window conflict.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from enum import Enum


Point = Tuple[float, float]

BASE_DIR = Path(__file__).resolve().parent


class SafetyDecision(Enum):
    PROCEED = "PROCEED"
    CAUTION = "CAUTION"
    DO_NOT_ENTER = "DO_NOT_ENTER"
    SAFETY_OVERRIDE = "SAFETY_OVERRIDE"


# ======================================================================
# OBSERVATION / PREDICTION MODELS
# ======================================================================

@dataclass(frozen=True)
class Observation:
    time_min: float
    position: Point
    visible: bool


@dataclass(frozen=True)
class Prediction:
    time_min: float
    position: Point
    uncertainty_radius: float
    source_time_min: float
    source_position: Point
    blind: bool


@dataclass(frozen=True)
class ScenarioStep:
    time_min: float
    observed_position: Optional[Point]
    predicted_position: Point
    uncertainty_radius: float
    visible: bool
    blind: bool
    temporal_state: str
    decision: str
    safety_cleared: bool
    prediction_error: Optional[float]
    input_source: str


# ======================================================================
# SENSOR-BLIND PREDICTOR
# ======================================================================

class BlindPeriodPredictor:
    """Predict from observations only; never consume hidden truth."""

    VERSION = "0.10.3"

    def __init__(self, uncertainty_growth_per_minute: float = 0.75):
        self.uncertainty_growth_per_minute = uncertainty_growth_per_minute
        self.observations: List[Observation] = []

    def observe(self, time_min: float, position: Point) -> None:
        self.observations.append(
            Observation(time_min=time_min, position=position, visible=True)
        )
        self.observations.sort(key=lambda x: x.time_min)

    def _velocity(self) -> Point:
        if len(self.observations) < 2:
            return (0.0, 0.0)

        a = self.observations[-2]
        b = self.observations[-1]
        dt = b.time_min - a.time_min
        if dt <= 0:
            raise ValueError("Observation times must increase.")

        return (
            (b.position[0] - a.position[0]) / dt,
            (b.position[1] - a.position[1]) / dt,
        )

    def predict(self, time_min: float) -> Prediction:
        if not self.observations:
            raise ValueError("Cannot predict without at least one observation.")

        last = self.observations[-1]
        dt = time_min - last.time_min
        if dt < 0:
            raise ValueError("Prediction time cannot precede last observation.")

        vx, vy = self._velocity()
        predicted = (
            last.position[0] + vx * dt,
            last.position[1] + vy * dt,
        )

        # Uncertainty is zero at the observation instant and grows while blind.
        uncertainty = self.uncertainty_growth_per_minute * dt

        return Prediction(
            time_min=time_min,
            position=predicted,
            uncertainty_radius=uncertainty,
            source_time_min=last.time_min,
            source_position=last.position,
            blind=dt > 0,
        )


# ======================================================================
# SCENARIO ENGINE
# ======================================================================

class WildSentinel103:
    """End-to-end observation/blind-period safety scenario engine."""

    VERSION = "0.10.3"
    ROUTE_Y = 50.0
    CONFLICT_RADIUS = 5.0

    def __init__(self):
        self.predictor = BlindPeriodPredictor()
        self.steps: List[ScenarioStep] = []
        self._last_prediction: Optional[Prediction] = None

    @staticmethod
    def distance_to_route(position: Point, route_y: float = 50.0) -> float:
        return abs(position[1] - route_y)

    def _classify(self, position: Point, uncertainty: float, visible: bool) -> str:
        distance = self.distance_to_route(position)

        # Conservative semantics: uncertainty touching the route is a conflict
        # candidate, even if the centre of the prediction has not reached it.
        if distance <= self.CONFLICT_RADIUS + uncertainty:
            if visible:
                return "IN_WINDOW_CONFLICT"
            return "FUTURE_CONFLICT"

        if not visible:
            return "BLIND"

        return "OBSERVED"

    def _decision_for_state(self, state: str, visible: bool) -> Tuple[str, bool]:
        # V0.10.3 deliberately preserves the V0.10.2 safety principle that
        # blind/predicted states never produce a safety clearance.
        if state == "IN_WINDOW_CONFLICT":
            return SafetyDecision.DO_NOT_ENTER.value, False
        if state in ("FUTURE_CONFLICT", "BLIND"):
            return SafetyDecision.CAUTION.value, False
        if state == "OBSERVED":
            return SafetyDecision.CAUTION.value, False
        return SafetyDecision.SAFETY_OVERRIDE.value, False

    def process(self, time_min: float, position: Optional[Point]) -> ScenarioStep:
        """
        Process one scenario time point.

        IMPORTANT: position=None means the sensor is blind. No hidden or
        ground-truth position may be supplied in that case.
        """
        visible = position is not None

        if visible:
            self.predictor.observe(time_min, position)  # observation only
            prediction = self.predictor.predict(time_min)
            prediction_error = None
            if self._last_prediction is not None and self._last_prediction.blind:
                prediction_error = math.dist(
                    self._last_prediction.position,
                    position,
                )
            predicted_position = prediction.position
            uncertainty = prediction.uncertainty_radius
            input_source = "OBSERVATION"
        else:
            prediction = self.predictor.predict(time_min)
            prediction_error = None
            predicted_position = prediction.position
            uncertainty = prediction.uncertainty_radius
            input_source = "LAST_OBSERVATION_PLUS_MOTION"

        self._last_prediction = prediction

        state = self._classify(predicted_position, uncertainty, visible)
        decision, safety_cleared = self._decision_for_state(state, visible)

        step = ScenarioStep(
            time_min=time_min,
            observed_position=position,
            predicted_position=predicted_position,
            uncertainty_radius=uncertainty,
            visible=visible,
            blind=not visible,
            temporal_state=state,
            decision=decision,
            safety_cleared=safety_cleared,
            prediction_error=prediction_error,
            input_source=input_source,
        )
        self.steps.append(step)
        return step


# ======================================================================
# REFERENCE SCENARIO
# ======================================================================


def run_reference_scenario() -> List[ScenarioStep]:
    """
    Reference scenario.

    Truth is deliberately kept outside the engine input path. During t=15,
    t=20 and t=25 the engine receives None, not the hidden truth positions.
    """
    engine = WildSentinel103()

    observations: Dict[float, Optional[Point]] = {
        0: (50.0, 20.0),
        5: (50.0, 25.0),
        10: (50.0, 30.0),
        15: None,
        20: None,
        25: None,
        30: (50.0, 49.0),
    }

    return [
        engine.process(t, observations[t])
        for t in sorted(observations)
    ]


# ======================================================================
# ADVERSARIAL TEST SUITE
# ======================================================================


def check(name: str, condition: bool, detail: str = "") -> bool:
    if condition:
        print(f"[PASS] {name}")
        return True
    print(f"[FAIL] {name}" + (f" :: {detail}" if detail else ""))
    return False


def run_v0103_tests() -> bool:
    passed = 0
    failed = 0

    print("=" * 78)
    print("                 WILD SENTINEL V0.10.3")
    print("        END-TO-END SENSOR-BLIND SCENARIO ENGINE")
    print("=" * 78)

    steps = run_reference_scenario()

    # 1. Initial observations are accepted.
    ok = steps[0].visible and steps[1].visible and steps[2].visible
    if check("Observed approach is accepted", ok):
        passed += 1
    else:
        failed += 1

    # 2. Blind period contains no observed position.
    blind_steps = [s for s in steps if s.blind]
    ok = all(s.observed_position is None for s in blind_steps)
    if check("Blind period contains no ground-truth observation", ok):
        passed += 1
    else:
        failed += 1

    # 3. Blind predictions continue the observed trajectory.
    blind_y = [s.predicted_position[1] for s in blind_steps]
    ok = blind_y == [35.0, 40.0, 45.0]
    if check("Blind period predicts continued approach", ok, f"predicted_y={blind_y}"):
        passed += 1
    else:
        failed += 1

    # 4. Uncertainty grows during blindness.
    blind_uncertainty = [s.uncertainty_radius for s in blind_steps]
    ok = all(
        blind_uncertainty[i] < blind_uncertainty[i + 1]
        for i in range(len(blind_uncertainty) - 1)
    )
    if check(
        "Uncertainty grows during sensor blindness",
        ok,
        f"uncertainty={blind_uncertainty}",
    ):
        passed += 1
    else:
        failed += 1

    # 5. Blind state never clears safety and never says PROCEED.
    ok = all(
        not s.safety_cleared and s.decision != SafetyDecision.PROCEED.value
        for s in blind_steps
    )
    if check("Blind period never produces safety clearance", ok):
        passed += 1
    else:
        failed += 1

    # 6. Final observation detects the route conflict.
    final = steps[-1]
    ok = (
        final.visible
        and final.observed_position == (50.0, 49.0)
        and final.temporal_state == "IN_WINDOW_CONFLICT"
    )
    if check("Final observation detects in-window conflict", ok):
        passed += 1
    else:
        failed += 1

    # 7. Final decision is DO NOT ENTER.
    ok = final.decision == SafetyDecision.DO_NOT_ENTER.value and not final.safety_cleared
    if check("Final conflict produces DO_NOT_ENTER", ok):
        passed += 1
    else:
        failed += 1

    # 8. Prediction error is calculated only when observation returns.
    ok = final.prediction_error is not None and abs(final.prediction_error - 4.0) < 1e-9
    if check(
        "Prediction error is reported on re-observation",
        ok,
        f"prediction_error={final.prediction_error}",
    ):
        passed += 1
    else:
        failed += 1

    # 9. Ground-truth isolation: a second run with the same observations
    # must produce the same blind predictions. Hidden truth is irrelevant.
    steps_again = run_reference_scenario()
    blind_again = [s.predicted_position for s in steps_again if s.blind]
    blind_original = [s.predicted_position for s in steps if s.blind]
    ok = blind_again == blind_original
    if check("Blind predictions are isolated from hidden ground truth", ok):
        passed += 1
    else:
        failed += 1

    # 10. No blind step may claim an observed conflict merely because the
    # hidden truth is approaching. At t=15/20/25 the state is prediction/blind.
    ok = all(
        s.temporal_state in ("BLIND", "FUTURE_CONFLICT")
        for s in blind_steps
    )
    if check("Blind states remain predictive, not falsely observed", ok):
        passed += 1
    else:
        failed += 1

    print("-" * 78)
    print(f"  TESTS PASSED: {passed}")
    print(f"  TESTS FAILED: {failed}")
    print("-" * 78)

    if failed == 0:
        print("  >>> V0.10.3 SENSOR-BLIND SAFETY TESTS PASSED")
    else:
        print("  >>> V0.10.3 REQUIRES FURTHER INVESTIGATION")

    print("=" * 78)
    return failed == 0


# ======================================================================
# DEMO
# ======================================================================


def run_demo() -> None:
    steps = run_reference_scenario()

    print("\n" + "=" * 78)
    print("                 WILD SENTINEL V0.10.3 DEMO")
    print("=" * 78)
    print("Route A: y=50 | Sensor blind: t=15 to t=25")
    print()

    for s in steps:
        observed = "—" if s.observed_position is None else str(s.observed_position)
        error = "—" if s.prediction_error is None else f"{s.prediction_error:.2f}"
        print(
            f"t={s.time_min:>2.0f}m | "
            f"visible={str(s.visible):<5} | "
            f"observed={observed:<14} | "
            f"predicted=({s.predicted_position[0]:.1f},{s.predicted_position[1]:.1f}) | "
            f"uncertainty={s.uncertainty_radius:>4.1f} | "
            f"state={s.temporal_state:<18} | "
            f"decision={s.decision:<15} | "
            f"error={error}"
        )

    print("=" * 78)


if __name__ == "__main__":
    run_demo()
    print()
    if not run_v0103_tests():
        raise SystemExit(1)
