r"""
WILD SENTINEL V0.10.6

MULTI-ROUTE SCENARIO ENGINE

V0.10.6 adds route-level orchestration above the frozen
V0.10.4 / V0.10.5 safety engines.

Architecture:

V0.9.9.4  Geometry / TTC
    ↓
V0.10.1   Temporal State
    ↓
V0.10.2   Safety Arbitration
    ↓
V0.10.3   Sensor-Blind Scenario Engine
    ↓
V0.10.4   Adversarial Validation
    ↓
V0.10.5   Behaviour Divergence
    ↓
V0.10.6   MULTI-ROUTE SCENARIO ENGINE

CORE PRINCIPLES
---------------

1. Each route is evaluated independently.
2. A route must never become safe merely because another route is safe.
3. Sensor blindness does not clear safety.
4. UNKNOWN is not SAFE.
5. No-re-observation is not a safety clearance.
6. Existing safety decisions remain authoritative.
7. V0.10.6 is an orchestration layer only.
8. V0.10.4 and V0.10.5 remain frozen.

Route topology:

                       HOUSE
             / | \
            A  B  C
             \ | /
             SCHOOL
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, List, Any


# ---------------------------------------------------------------------------
# DYNAMIC LOADING
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent


def _load_module(filename: str, module_name: str):
    path = BASE_DIR / filename

    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
    )

    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load {filename}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


V0104 = _load_module(
    "wild_sentinel_v0_10_4.py",
    "wild_sentinel_v0_10_4_for_v0106",
)


# ---------------------------------------------------------------------------
# ROUTE DATA MODELS
# ---------------------------------------------------------------------------

@dataclass
class RouteScenario:
    """
    One independent route scenario.

    observations:
        Mapping of time in minutes to observed wildlife position.

        None means that no wildlife observation is available at
        that point in the timeline.
    """

    route_id: str
    observations: Dict[float, Optional[Any]]


@dataclass
class RouteAssessment:
    """
    Complete result for one route.

    Current state is reported separately from safety history.
    A later observation must not erase an earlier safety-critical event.
    """

    route_id: str
    steps: List[Any]
    final_step: Any

    @property
    def decision(self) -> str:
        return self.final_step.decision

    @property
    def temporal_state(self) -> str:
        return self.final_step.temporal_state

    @property
    def safety_cleared(self) -> bool:
        return bool(self.final_step.safety_cleared)

    @property
    def blind(self) -> bool:
        return bool(self.final_step.blind)

    @property
    def uncertainty_radius(self) -> float:
        return float(self.final_step.uncertainty_radius)

    @property
    def ever_do_not_enter(self) -> bool:
        return any(
            step.decision == "DO_NOT_ENTER"
            for step in self.steps
        )

    @property
    def ever_future_conflict(self) -> bool:
        return any(
            step.temporal_state == "FUTURE_CONFLICT"
            for step in self.steps
        )

    @property
    def ever_in_window_conflict(self) -> bool:
        return any(
            step.temporal_state == "IN_WINDOW_CONFLICT"
            for step in self.steps
        )

    @property
    def ever_blind(self) -> bool:
        return any(
            step.blind
            for step in self.steps
        )

    @property
    def maximum_uncertainty(self) -> float:
        return max(
            float(step.uncertainty_radius)
            for step in self.steps
        )

    @property
    def prediction_errors(self) -> List[float]:
        return [
            float(step.prediction_error)
            for step in self.steps
            if step.prediction_error is not None
        ]

@dataclass
class MultiRouteAssessment:
    """
    Complete assessment of all routes.

    No ranking is performed.
    """

    routes: Dict[str, RouteAssessment]

    @property
    def route_count(self) -> int:
        return len(self.routes)

    def get(self, route_id: str) -> RouteAssessment:
        return self.routes[route_id]


# ---------------------------------------------------------------------------
# MULTI-ROUTE ENGINE
# ---------------------------------------------------------------------------

class WildSentinel106:
    """
    V0.10.6 Multi-Route Scenario Engine.

    This class orchestrates independent route evaluations.

    It deliberately does NOT alter the underlying V0.10.4 engine.
    """

    VERSION = "0.10.6"

    def __init__(self):
        self.baseline = V0104

    def evaluate_route(
        self,
        scenario: RouteScenario,
    ) -> RouteAssessment:
        """
        Evaluate one route independently.
        """

        steps = self.baseline.run_scenario(
            scenario.observations
        )

        if not steps:
            raise ValueError(
                f"Route {scenario.route_id} produced no scenario steps"
            )

        return RouteAssessment(
            route_id=scenario.route_id,
            steps=steps,
            final_step=steps[-1],
        )

    def evaluate_routes(
        self,
        scenarios: List[RouteScenario],
    ) -> MultiRouteAssessment:
        """
        Evaluate all routes independently.

        No route is allowed to influence another route's result.
        """

        results: Dict[str, RouteAssessment] = {}

        for scenario in scenarios:
            if scenario.route_id in results:
                raise ValueError(
                    f"Duplicate route ID: {scenario.route_id}"
                )

            results[scenario.route_id] = self.evaluate_route(
                scenario
            )

        return MultiRouteAssessment(
            routes=results
        )


# ---------------------------------------------------------------------------
# REPORTING
# ---------------------------------------------------------------------------

def print_route_assessment(
    assessment: RouteAssessment,
) -> None:

    print(
        f"\nROUTE {assessment.route_id}"
    )
    print("-" * 60)

    for step in assessment.steps:
        print(
            f"t={step.time_min:>5.1f}  "
            f"visible={str(step.visible):<5}  "
            f"blind={str(step.blind):<5}  "
            f"state={step.temporal_state:<22}  "
            f"decision={step.decision:<15}  "
            f"uncertainty={step.uncertainty_radius:>6.2f}  "
            f"source={step.input_source}"
        )

    print()
    print("CURRENT STATUS")
    print(
        f"CURRENT DECISION : {assessment.decision}"
    )
    print(
        f"CURRENT STATE    : {assessment.temporal_state}"
    )
    print(
        f"SAFETY CLEARED   : {assessment.safety_cleared}"
    )
    print(
        f"CURRENT BLIND    : {assessment.blind}"
    )
    print(
        f"CURRENT UNCERTAINTY : "
        f"{assessment.uncertainty_radius:.2f}"
    )

    print()
    print("SAFETY HISTORY")
    print(
        f"EVER DO_NOT_ENTER      : "
        f"{assessment.ever_do_not_enter}"
    )
    print(
        f"EVER FUTURE_CONFLICT   : "
        f"{assessment.ever_future_conflict}"
    )
    print(
        f"EVER IN_WINDOW_CONFLICT: "
        f"{assessment.ever_in_window_conflict}"
    )
    print(
        f"EVER BLIND             : "
        f"{assessment.ever_blind}"
    )
    print(
        f"MAX UNCERTAINTY        : "
        f"{assessment.maximum_uncertainty:.2f}"
    )

    if assessment.prediction_errors:
        print(
            f"PREDICTION ERRORS     : "
            f"{assessment.prediction_errors}"
        )


def print_multi_route_report(
    assessment: MultiRouteAssessment,
) -> None:

    print()
    print("=" * 72)
    print("WILD SENTINEL V0.10.6")
    print("MULTI-ROUTE SAFETY REPORT")
    print("=" * 72)

    for route_id in sorted(assessment.routes):
        print_route_assessment(
            assessment.routes[route_id]
        )

    print()
    print("=" * 72)
    print("ROUTE SUMMARY")
    print("=" * 72)

    for route_id in sorted(assessment.routes):
        route = assessment.routes[route_id]

        print(
            f"ROUTE {route_id}: "
            f"{route.decision} | "
            f"{route.temporal_state} | "
            f"SAFETY_CLEARED={route.safety_cleared}"
        )

    print()
    print(
        "IMPORTANT: V0.10.6 does not rank routes "
        "or manufacture a SAFE route."
    )


# ---------------------------------------------------------------------------
# TEST SCENARIOS
# ---------------------------------------------------------------------------

def _build_test_routes() -> List[RouteScenario]:
    """
    Three deliberately different routes.

    Route A:
        Wildlife approaches during sensor blindness.

    Route B:
        Wildlife is observed moving away after blindness.

    Route C:
        No wildlife is observed during the route timeline.

    These scenarios are designed to test orchestration rather
    than create artificial safety guarantees.
    """

    route_a = RouteScenario(
        route_id="A",
        observations={
            0.0: (50.0, 20.0),
            5.0: (50.0, 25.0),
            10.0: (50.0, 30.0),
            15.0: None,
            20.0: None,
            25.0: (50.0, 42.0),
        },
    )

    route_b = RouteScenario(
        route_id="B",
        observations={
            0.0: (30.0, 60.0),
            5.0: (30.0, 55.0),
            10.0: (30.0, 50.0),
            15.0: None,
            20.0: None,
            25.0: (30.0, 35.0),
        },
    )

    route_c = RouteScenario(
    route_id="C",
    observations={
        0.0: (80.0, 80.0),
        5.0: None,
        10.0: None,
        15.0: None,
        20.0: None,
        25.0: None,
    },
)

    return [
        route_a,
        route_b,
        route_c,
    ]


# ---------------------------------------------------------------------------
# TESTS
# ---------------------------------------------------------------------------

def run_v0106_tests() -> bool:

    print()
    print("WILD SENTINEL V0.10.6 TEST SUITE")
    print("=" * 60)

    engine = WildSentinel106()

    passed = 0
    failed = 0

    # Test 1
    try:
        routes = _build_test_routes()
        result = engine.evaluate_routes(routes)

        assert result.route_count == 3

        print("[PASS] Three independent routes evaluated")
        passed += 1

    except Exception as exc:
        print(
            f"[FAIL] Three independent routes evaluated: {exc}"
        )
        failed += 1

    # Test 2
    try:
        assert set(result.routes.keys()) == {"A", "B", "C"}

        print("[PASS] Route identities preserved")
        passed += 1

    except Exception as exc:
        print(
            f"[FAIL] Route identities preserved: {exc}"
        )
        failed += 1

    # Test 3
    try:
        assert all(
            len(route.steps) > 0
            for route in result.routes.values()
        )

        print("[PASS] Every route produced scenario steps")
        passed += 1

    except Exception as exc:
        print(
            f"[FAIL] Every route produced scenario steps: {exc}"
        )
        failed += 1

    # Test 4
    try:
        assert (
            result.routes["A"].steps
            is not result.routes["B"].steps
        )

        assert (
            result.routes["B"].steps
            is not result.routes["C"].steps
        )

        print("[PASS] Route results remain independent")
        passed += 1

    except Exception as exc:
        print(
            f"[FAIL] Route results remain independent: {exc}"
        )
        failed += 1

    # Test 5
    try:
        assert all(
            hasattr(step, "decision")
            for route in result.routes.values()
            for step in route.steps
        )

        print("[PASS] Safety decisions preserved")
        passed += 1

    except Exception as exc:
        print(
            f"[FAIL] Safety decisions preserved: {exc}"
        )
        failed += 1

    # Test 6
    try:
        assert all(
            hasattr(step, "uncertainty_radius")
            for route in result.routes.values()
            for step in route.steps
        )

        print("[PASS] Uncertainty preserved for every route")
        passed += 1

    except Exception as exc:
        print(
            f"[FAIL] Uncertainty preserved for every route: {exc}"
        )
        failed += 1

    # Test 7
    try:
        assert all(
            hasattr(step, "input_source")
            for route in result.routes.values()
            for step in route.steps
        )

        print("[PASS] Engine input source preserved")
        passed += 1

    except Exception as exc:
        print(
            f"[FAIL] Engine input source preserved: {exc}"
        )
        failed += 1

    # Test 8
    try:
        assert not hasattr(
            result,
            "recommended_route"
        )

        print(
            "[PASS] No global route ranking/recommendation created"
        )
        passed += 1

    except Exception as exc:
        print(
            f"[FAIL] No global route ranking/recommendation created: {exc}"
        )
        failed += 1

    # Test 9
    try:
        assert (
            result.routes["A"].decision
            is not None
        )

        assert (
            result.routes["B"].decision
            is not None
        )

        assert (
            result.routes["C"].decision
            is not None
        )

        print(
            "[PASS] Every route retains an explicit safety decision"
        )
        passed += 1

    except Exception as exc:
        print(
            f"[FAIL] Every route retains an explicit safety decision: {exc}"
        )
        failed += 1

    # Test 10
    try:
        assert result.routes["B"].ever_do_not_enter is True

        print(
            "[PASS] Safety-critical route history is preserved"
        )
        passed += 1

    except Exception as exc:
        print(
            f"[FAIL] Safety-critical route history is preserved: {exc}"
        )
        failed += 1

    # Test 11
    try:
        assert result.routes["A"].ever_future_conflict is True

        print(
            "[PASS] Future conflict history is preserved"
        )
        passed += 1

    except Exception as exc:
        print(
            f"[FAIL] Future conflict history is preserved: {exc}"
        )
        failed += 1

    # Test 12
    try:
        assert result.routes["C"].maximum_uncertainty == 18.75

        print(
            "[PASS] Maximum uncertainty is preserved"
        )
        passed += 1

    except Exception as exc:
        print(
            f"[FAIL] Maximum uncertainty is preserved: {exc}"
        )
        failed += 1

# Test 13
    try:
        assert engine.VERSION == "0.10.6"

        print("[PASS] V0.10.6 engine version confirmed")
        passed += 1

    except Exception as exc:
        print(
            f"[FAIL] V0.10.6 engine version confirmed: {exc}"
        )
        failed += 1

    print()
    print(f"TESTS PASSED: {passed}")
    print(f"TESTS FAILED: {failed}")

    if failed == 0:
        print(
            ">>> V0.10.6 MULTI-ROUTE TESTS PASSED"
        )
        return True

    print(
        ">>> V0.10.6 MULTI-ROUTE TESTS FAILED"
    )

    return False


# ---------------------------------------------------------------------------
# DEMO
# ---------------------------------------------------------------------------

def run_demo() -> None:

    engine = WildSentinel106()

    result = engine.evaluate_routes(
        _build_test_routes()
    )

    print_multi_route_report(result)


if __name__ == "__main__":
    run_demo()
