"""
WILD SENTINEL V0.10.5

BEHAVIOUR DIVERGENCE INTERPRETATION ENGINE

V0.10.5 builds on the frozen V0.10.4 adversarial validation layer.

PURPOSE
-------
Interpret what happens when wildlife is re-observed after a
sensor-blind period and the observed position differs from the
previously predicted position.

SAFETY PRINCIPLES
-----------------
1. V0.10.4 remains unchanged.
2. Ground truth is never supplied during blindness.
3. Divergence is calculated only when observation returns.
4. Prediction agreement does not automatically mean SAFE.
5. Missing re-observation never becomes a safety clearance.
6. Large prediction error is explicitly exposed.
7. Actual route conflict continues to dominate safety decisions.
8. V0.10.5 is an interpretation layer, not a replacement
   for the frozen safety engine.
"""

from __future__ import annotations

import importlib.util
import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple


VERSION = "0.10.5"

Position = Tuple[float, float]


# ---------------------------------------------------------------------------
# LOAD FROZEN V0.10.4
# ---------------------------------------------------------------------------

def load_v0104():
    here = Path(__file__).resolve().parent
    path = here / "wild_sentinel_v0_10_4.py"

    spec = importlib.util.spec_from_file_location(
        "wild_sentinel_v0_10_4",
        path,
    )

    if spec is None or spec.loader is None:
        raise ImportError("Unable to load V0.10.4 baseline")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


baseline = load_v0104()


# ---------------------------------------------------------------------------
# ENUMS
# ---------------------------------------------------------------------------

class DivergenceState(Enum):
    NO_REOBSERVATION = "NO_REOBSERVATION"
    PREDICTION_CONFIRMED = "PREDICTION_CONFIRMED"
    BEHAVIOUR_DIVERGENCE = "BEHAVIOUR_DIVERGENCE"
    REOBSERVED_CLOSING = "REOBSERVED_CLOSING"
    REOBSERVED_MOVING_AWAY = "REOBSERVED_MOVING_AWAY"
    REOBSERVED_CONFLICT = "REOBSERVED_CONFLICT"


# ---------------------------------------------------------------------------
# RESULT
# ---------------------------------------------------------------------------

@dataclass
class DivergenceResult:
    time: float
    predicted_position: Optional[Position]
    observed_position: Optional[Position]
    prediction_error: Optional[float]
    state: DivergenceState
    safety_decision: str


# ---------------------------------------------------------------------------
# ENGINE
# ---------------------------------------------------------------------------

class WildSentinel105:
    """
    V0.10.5 interpretation layer.

    It consumes the outputs of the frozen V0.10.4 scenario engine
    and interprets re-observation behaviour.
    """

    VERSION = VERSION

    # Deliberately conservative threshold.
    # A small error can be treated as prediction agreement.
    # Anything materially larger becomes explicit divergence.
    DIVERGENCE_THRESHOLD = 5.0

    def __init__(self):
        self.history = []

    @staticmethod
    def distance(a: Position, b: Position) -> float:
        return math.sqrt(
            (a[0] - b[0]) ** 2 +
            (a[1] - b[1]) ** 2
        )

    @staticmethod
    def _movement_direction(
        previous: Position,
        current: Position,
    ) -> Position:
        return (
            current[0] - previous[0],
            current[1] - previous[1],
        )

    def interpret(
        self,
        time: float,
        predicted_position: Optional[Position],
        observed_position: Optional[Position],
        previous_observed_position: Optional[Position] = None,
        safety_decision: str = "CAUTION",
    ) -> DivergenceResult:

        # ---------------------------------------------------------------
        # NO RE-OBSERVATION
        # ---------------------------------------------------------------

        if observed_position is None:
            result = DivergenceResult(
                time=time,
                predicted_position=predicted_position,
                observed_position=None,
                prediction_error=None,
                state=DivergenceState.NO_REOBSERVATION,
                safety_decision=safety_decision,
            )

            self.history.append(result)
            return result

        # ---------------------------------------------------------------
        # OBSERVATION RETURNED
        # ---------------------------------------------------------------

        error = None

        if predicted_position is not None:
            error = self.distance(
                predicted_position,
                observed_position,
            )

        # ---------------------------------------------------------------
        # ACTUAL ROUTE CONFLICT TAKES PRIORITY
        #
        # We intentionally allow the underlying safety engine's
        # decision to dominate the interpretation layer.
        # ---------------------------------------------------------------

        if safety_decision == "DO_NOT_ENTER":
            state = DivergenceState.REOBSERVED_CONFLICT

        # ---------------------------------------------------------------
        # MOVEMENT INTERPRETATION
        # ---------------------------------------------------------------

        elif (
            previous_observed_position is not None
            and observed_position[1] < previous_observed_position[1]
        ):
            state = DivergenceState.REOBSERVED_MOVING_AWAY

        elif (
            error is not None
            and error <= self.DIVERGENCE_THRESHOLD
        ):
            state = DivergenceState.PREDICTION_CONFIRMED

        elif error is not None:
            state = DivergenceState.BEHAVIOUR_DIVERGENCE

        else:
            state = DivergenceState.BEHAVIOUR_DIVERGENCE

        # ---------------------------------------------------------------
        # SAFETY DECISION
        #
        # V0.10.5 does not manufacture PROCEED.
        # ---------------------------------------------------------------

        result = DivergenceResult(
            time=time,
            predicted_position=predicted_position,
            observed_position=observed_position,
            prediction_error=error,
            state=state,
            safety_decision=safety_decision,
        )

        self.history.append(result)
        return result


# ---------------------------------------------------------------------------
# TEST SCENARIOS
# ---------------------------------------------------------------------------

def test_prediction_confirmed():
    engine = WildSentinel105()

    result = engine.interpret(
        time=30,
        predicted_position=(50, 45),
        observed_position=(50, 49),
        safety_decision="DO_NOT_ENTER",
    )

    return (
        result.prediction_error == 4.0
        and result.state == DivergenceState.REOBSERVED_CONFLICT
    )


def test_stopped_animal():
    engine = WildSentinel105()

    result = engine.interpret(
        time=30,
        predicted_position=(50, 45),
        observed_position=(50, 30),
        safety_decision="CAUTION",
    )

    return (
        result.prediction_error == 15.0
        and result.state == DivergenceState.BEHAVIOUR_DIVERGENCE
    )


def test_reversal():
    engine = WildSentinel105()

    result = engine.interpret(
        time=30,
        predicted_position=(50, 45),
        observed_position=(50, 22),
        safety_decision="CAUTION",
    )

    return (
        result.prediction_error == 23.0
        and result.state == DivergenceState.BEHAVIOUR_DIVERGENCE
    )


def test_direction_change_conflict():
    engine = WildSentinel105()

    result = engine.interpret(
        time=30,
        predicted_position=(45, 45),
        observed_position=(55, 52),
        safety_decision="DO_NOT_ENTER",
    )

    return (
        result.state == DivergenceState.REOBSERVED_CONFLICT
        and result.safety_decision == "DO_NOT_ENTER"
    )


def test_moving_away():
    engine = WildSentinel105()

    result = engine.interpret(
        time=30,
        predicted_position=(50, 15),
        observed_position=(50, 20),
        previous_observed_position=(50, 30),
        safety_decision="CAUTION",
    )

    return (
        result.prediction_error == 5.0
        and result.state == DivergenceState.REOBSERVED_MOVING_AWAY
        and result.safety_decision != "PROCEED"
    )


def test_no_reappearance():
    engine = WildSentinel105()

    result = engine.interpret(
        time=40,
        predicted_position=(50, 60),
        observed_position=None,
        safety_decision="CAUTION",
    )

    return (
        result.state == DivergenceState.NO_REOBSERVATION
        and result.safety_decision != "PROCEED"
    )


def test_v0104_frozen():
    return baseline.baseline.WildSentinel103.VERSION == "0.10.3"


# ---------------------------------------------------------------------------
# TEST RUNNER
# ---------------------------------------------------------------------------

def run_v0105_tests():

    tests = [
        ("Prediction conflict remains safety-dominant",
         test_prediction_confirmed),

        ("Stopped animal produces divergence",
         test_stopped_animal),

        ("Reversal produces divergence",
         test_reversal),

        ("Direction change remains DO_NOT_ENTER",
         test_direction_change_conflict),

        ("Moving-away behaviour is recognized conservatively",
         test_moving_away),

        ("No reappearance never becomes SAFE",
         test_no_reappearance),

        ("Frozen V0.10.4/V0.10.3 baseline remains intact",
         test_v0104_frozen),
    ]

    passed = 0
    failed = 0

    print()
    print("=" * 78)
    print("        WILD SENTINEL V0.10.5 TEST SUITE")
    print("=" * 78)

    for name, test in tests:
        try:
            result = test()
        except Exception as exc:
            result = False
            print(f"[ERROR] {name}: {exc}")

        if result:
            print(f"[PASS] {name}")
            passed += 1
        else:
            print(f"[FAIL] {name}")
            failed += 1

    print("-" * 78)
    print(f"  TESTS PASSED: {passed}")
    print(f"  TESTS FAILED: {failed}")
    print("-" * 78)

    if failed == 0:
        print("  >>> V0.10.5 BEHAVIOUR DIVERGENCE TESTS PASSED")
    else:
        print("  >>> V0.10.5 TESTS FAILED")

    print()

    return failed == 0


# ---------------------------------------------------------------------------
# DEMO
# ---------------------------------------------------------------------------

def run_demo():

    engine = WildSentinel105()

    scenarios = [
        (
            "A. Continued approach",
            (50, 45),
            (50, 49),
            None,
            "DO_NOT_ENTER",
        ),
        (
            "B. Animal stops",
            (50, 45),
            (50, 30),
            None,
            "CAUTION",
        ),
        (
            "C. Animal reverses",
            (50, 45),
            (50, 22),
            None,
            "CAUTION",
        ),
        (
            "D. Direction change across route",
            (45, 45),
            (55, 52),
            None,
            "DO_NOT_ENTER",
        ),
        (
            "E. Animal moves away",
            (50, 15),
            (50, 20),
            (50, 30),
            "CAUTION",
        ),
        (
            "F. Animal never reappears",
            (50, 60),
            None,
            None,
            "CAUTION",
        ),
    ]

    print()
    print("=" * 78)
    print("        WILD SENTINEL V0.10.5")
    print("        BEHAVIOUR DIVERGENCE INTERPRETATION")
    print("=" * 78)

    for name, predicted, observed, previous, decision in scenarios:

        result = engine.interpret(
            time=30,
            predicted_position=predicted,
            observed_position=observed,
            previous_observed_position=previous,
            safety_decision=decision,
        )

        print()
        print(name)
        print("-" * 78)
        print(f"Predicted position : {predicted}")
        print(f"Observed position  : {observed}")

        if result.prediction_error is None:
            print("Prediction error   : N/A")
        else:
            print(
                f"Prediction error   : "
                f"{result.prediction_error:.2f}"
            )

        print(f"Divergence state   : {result.state.value}")
        print(f"Safety decision    : {result.safety_decision}")

    print()
    print("=" * 78)


if __name__ == "__main__":
    run_demo()