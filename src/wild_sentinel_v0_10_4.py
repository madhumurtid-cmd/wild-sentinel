
# Start from the uploaded, working V0.10.3 architecture and build a separate
# adversarial harness around the frozen engine.
"""
WILD SENTINEL V0.10.4
ADVERSARIAL BEHAVIOUR STRESS TEST ENGINE

V0.10.4 preserves the V0.10.3 engine and adds an adversarial
scenario harness designed to test what happens when the animal
does NOT follow the predicted trajectory.

V0.10.3 remains the frozen baseline.

CORE V0.10.4 PRINCIPLES:
    1. The V0.10.3 safety engine is not modified.
    2. Ground truth remains outside the engine during blindness.
    3. Blind periods receive None, never hidden truth.
    4. Prediction error is only calculated when an observation returns.
    5. Sensor blindness never produces safety clearance.
    6. Unexpected behaviour must not create false safety.
    7. Re-observation may validate or refute the prediction.
    8. A missing re-observation must never be interpreted as SAFE.

ADVERSARIAL SCENARIOS:
    A. Continued approach
    B. Animal stops
    C. Animal reverses direction
    D. Animal changes direction across the route
    E. Animal moves away
    F. Animal never reappears
"""

from __future__ import annotations
import sys
import importlib.util
from pathlib import Path
from typing import Optional, Tuple, List, Dict

Point = Tuple[float, float]
BASE_DIR = Path(__file__).resolve().parent
BASELINE_FILE = BASE_DIR / "wild_sentinel_v0_10_3.py"


def load_baseline():
    spec = importlib.util.spec_from_file_location(
        "wild_sentinel_v0_10_3", BASELINE_FILE
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load baseline: {BASELINE_FILE}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


baseline = load_baseline()

SafetyDecision = baseline.SafetyDecision
ScenarioStep = baseline.ScenarioStep
WildSentinel103 = baseline.WildSentinel103


# ======================================================================
# SCENARIO DEFINITIONS
# ======================================================================

def run_scenario(
    observations: Dict[float, Optional[Point]]
) -> List[ScenarioStep]:
    """
    Run a scenario through the frozen V0.10.3 engine.

    IMPORTANT:
    None means sensor blind. Hidden ground truth is deliberately not
    passed to the engine during those time points.
    """
    engine = WildSentinel103()
    return [
        engine.process(t, observations[t])
        for t in sorted(observations)
    ]


def scenario_continued_approach() -> List[ScenarioStep]:
    return run_scenario({
        0: (50.0, 20.0),
        5: (50.0, 25.0),
        10: (50.0, 30.0),
        15: None,
        20: None,
        25: None,
        30: (50.0, 49.0),
    })


def scenario_animal_stops() -> List[ScenarioStep]:
    return run_scenario({
        0: (50.0, 20.0),
        5: (50.0, 25.0),
        10: (50.0, 30.0),
        15: None,
        20: None,
        25: None,
        30: (50.0, 30.0),
    })


def scenario_animal_reverses() -> List[ScenarioStep]:
    return run_scenario({
        0: (50.0, 20.0),
        5: (50.0, 25.0),
        10: (50.0, 30.0),
        15: None,
        20: None,
        25: None,
        30: (50.0, 22.0),
    })


def scenario_changes_direction_across_route() -> List[ScenarioStep]:
    return run_scenario({
        0: (45.0, 20.0),
        5: (45.0, 25.0),
        10: (45.0, 30.0),
        15: None,
        20: None,
        25: None,
        30: (55.0, 52.0),
    })


def scenario_moves_away() -> List[ScenarioStep]:
    return run_scenario({
        0: (50.0, 40.0),
        5: (50.0, 35.0),
        10: (50.0, 30.0),
        15: None,
        20: None,
        25: None,
        30: (50.0, 20.0),
    })


def scenario_never_reappears() -> List[ScenarioStep]:
    return run_scenario({
        0: (50.0, 20.0),
        5: (50.0, 25.0),
        10: (50.0, 30.0),
        15: None,
        20: None,
        25: None,
        30: None,
        35: None,
        40: None,
    })


# ======================================================================
# TEST HELPERS
# ======================================================================

def check(name: str, condition: bool, detail: str = "") -> bool:
    if condition:
        print(f"[PASS] {name}")
        return True

    suffix = f" :: {detail}" if detail else ""
    print(f"[FAIL] {name}{suffix}")
    return False


def blind_steps(steps: List[ScenarioStep]) -> List[ScenarioStep]:
    return [s for s in steps if s.blind]


def last_step(steps: List[ScenarioStep]) -> ScenarioStep:
    return steps[-1]


def run_v0104_tests() -> bool:
    passed = 0
    failed = 0

    print("=" * 78)
    print("                 WILD SENTINEL V0.10.4")
    print("           ADVERSARIAL BEHAVIOUR STRESS TEST")
    print("=" * 78)
    print("Frozen baseline: V0.10.3")
    print()

    scenarios = {
        "A. CONTINUED APPROACH": scenario_continued_approach,
        "B. ANIMAL STOPS": scenario_animal_stops,
        "C. ANIMAL REVERSES": scenario_animal_reverses,
        "D. DIRECTION CHANGE ACROSS ROUTE": scenario_changes_direction_across_route,
        "E. ANIMAL MOVES AWAY": scenario_moves_away,
        "F. ANIMAL NEVER REAPPEARS": scenario_never_reappears,
    }

    results = {}

    # 1. Hidden truth must remain outside blind engine inputs.
    for name, runner in scenarios.items():
        steps = runner()
        blind = blind_steps(steps)
        ok = all(
            s.observed_position is None
            and s.input_source == "LAST_OBSERVATION_PLUS_MOTION"
            for s in blind
        )
        if check(f"{name}: blind inputs contain no ground truth", ok):
            passed += 1
        else:
            failed += 1
        results[name] = steps

    # 2. No blind period may ever clear safety.
    for name, steps in results.items():
        blind = blind_steps(steps)
        ok = all(
            not s.safety_cleared
            and s.decision != SafetyDecision.PROCEED.value
            for s in blind
        )
        if check(f"{name}: blindness never clears safety", ok):
            passed += 1
        else:
            failed += 1

    # 3. Continued approach reaches an observed conflict.
    steps = results["A. CONTINUED APPROACH"]
    blind = blind_steps(steps)
    final = last_step(steps)
    ok = (
        all(s.temporal_state in ("BLIND", "FUTURE_CONFLICT") for s in blind)
        and final.temporal_state == "IN_WINDOW_CONFLICT"
        and final.decision == SafetyDecision.DO_NOT_ENTER.value
        and final.prediction_error is not None
    )
    if check("A. Continued approach remains safely conservative", ok):
        passed += 1
    else:
        failed += 1

    # 4. Stopped animal refutes the motion prediction on re-observation.
    steps = results["B. ANIMAL STOPS"]
    final = last_step(steps)
    ok = (
        final.prediction_error is not None
        and final.prediction_error > 0.0
        and final.observed_position == (50.0, 30.0)
    )
    if check(
        "B. Stopped animal produces re-observation prediction error",
        ok,
        f"error={final.prediction_error}",
    ):
        passed += 1
    else:
        failed += 1

    # 5. Reversal produces measurable prediction error.
    steps = results["C. ANIMAL REVERSES"]
    final = last_step(steps)
    ok = final.prediction_error is not None and final.prediction_error > 0.0
    if check(
        "C. Reversal is exposed by prediction error",
        ok,
        f"error={final.prediction_error}",
    ):
        passed += 1
    else:
        failed += 1

    # 6. Direction change across route is not falsely observed during blind
    # time, but the actual re-observation inside the window is a conflict.
    steps = results["D. DIRECTION CHANGE ACROSS ROUTE"]
    blind = blind_steps(steps)
    final = last_step(steps)
    ok = (
        all(s.temporal_state in ("BLIND", "FUTURE_CONFLICT") for s in blind)
        and final.visible
        and final.temporal_state == "IN_WINDOW_CONFLICT"
        and final.decision == SafetyDecision.DO_NOT_ENTER.value
    )
    if check("D. Direction change across route remains conservative", ok):
        passed += 1
    else:
        failed += 1

    # 7. Moving away is recognized on re-observation.
    steps = results["E. ANIMAL MOVES AWAY"]
    final = last_step(steps)
    ok = (
        final.visible
        and final.temporal_state == "OBSERVED"
        and final.decision == SafetyDecision.CAUTION.value
        and final.prediction_error is not None
        and final.prediction_error > 0.0
    )
    if check(
        "E. Animal moving away is recognized on re-observation",
        ok,
        f"state={final.temporal_state}, error={final.prediction_error}",
    ):
        passed += 1
    else:
        failed += 1

    # 8. No reappearance never becomes a safety clearance.
    steps = results["F. ANIMAL NEVER REAPPEARS"]
    blind = blind_steps(steps)
    ok = (
        len(blind) == 6
        and all(
            s.observed_position is None
            and not s.safety_cleared
            and s.decision != SafetyDecision.PROCEED.value
            for s in blind
        )
    )
    if check("F. No reappearance never becomes a safety clearance", ok):
        passed += 1
    else:
        failed += 1

    # 9. Uncertainty continues growing during prolonged blindness.
    uncertainty = [s.uncertainty_radius for s in blind]
    ok = all(
        uncertainty[i] < uncertainty[i + 1]
        for i in range(len(uncertainty) - 1)
    )
    if check(
        "F. Uncertainty grows throughout prolonged blindness",
        ok,
        f"uncertainty={uncertainty}",
    ):
        passed += 1
    else:
        failed += 1

    # 10. V0.10.4 is explicitly testing the frozen V0.10.3 engine.
    ok = (
        WildSentinel103.VERSION == "0.10.3"
        and baseline.BlindPeriodPredictor.VERSION == "0.10.3"
    )
    if check("V0.10.4 uses the frozen V0.10.3 engine", ok):
        passed += 1
    else:
        failed += 1

    print("-" * 78)
    print(f"  TESTS PASSED: {passed}")
    print(f"  TESTS FAILED: {failed}")
    print("-" * 78)

    if failed == 0:
        print("  >>> V0.10.4 ADVERSARIAL SAFETY TESTS PASSED")
    else:
        print("  >>> V0.10.4 REQUIRES FURTHER INVESTIGATION")

    print("=" * 78)
    return failed == 0


# ======================================================================
# DEMO
# ======================================================================

def print_scenario(name: str, steps: List[ScenarioStep]) -> None:
    print()
    print("-" * 78)
    print(name)
    print("-" * 78)

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


def run_demo() -> None:
    print_scenario("A. CONTINUED APPROACH", scenario_continued_approach())
    print_scenario("B. ANIMAL STOPS", scenario_animal_stops())
    print_scenario("C. ANIMAL REVERSES", scenario_animal_reverses())
    print_scenario(
        "D. DIRECTION CHANGE ACROSS ROUTE",
        scenario_changes_direction_across_route(),
    )
    print_scenario("E. ANIMAL MOVES AWAY", scenario_moves_away())
    print_scenario("F. ANIMAL NEVER REAPPEARS", scenario_never_reappears())


if __name__ == "__main__":
    run_demo()
