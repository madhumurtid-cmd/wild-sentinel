
"""
WILD SENTINEL V0.10.2
TEMPORAL SAFETY ARBITRATION ENGINE

V0.10.2 adds a safety-decision layer above V0.10.1.

ARCHITECTURE:

    V0.9.9.4
        Geometry + TTC
            ↓
    V0.10.1
        Temporal Encounter State
            ↓
    V0.10.2
        Safety Arbitration

CORE SAFETY PRINCIPLES:

    UNKNOWN IS NOT SAFE.
    BLIND IS NOT SAFE.
    FUTURE CONFLICT IS NOT CLEARED.
    IN-WINDOW CONFLICT MUST NOT BE CLEARED.
    MOVING AWAY IS LOWER RISK, NOT AUTOMATICALLY SAFE.

V0.10.1 remains unchanged.
"""


from __future__ import annotations

import sys


import importlib.util
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple


Point = Tuple[float, float]


BASE_DIR = Path(__file__).resolve().parent

TEMPORAL_PATH = (
    BASE_DIR / "wild_sentinel_v0_10_1.py"
)


# ======================================================================
# LOAD V0.10.1
# ======================================================================

BASELINE_PATH = (
    Path(__file__).resolve().parent
    / "wild_sentinel_v0_10_1.py"
)


def load_temporal_engine():


    spec = importlib.util.spec_from_file_location(
        "wild_sentinel_v0_10_1",
        TEMPORAL_PATH,
    )

    if spec is None or spec.loader is None:
        raise ImportError(
            "Unable to load V0.10.1 temporal engine."
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[spec.name] = module

    spec.loader.exec_module(module)

    return module

temporal_module = load_temporal_engine()

WildSentinel101 = (
    temporal_module.WildSentinel101
)

TemporalState = (
    temporal_module.TemporalState
)

TemporalEncounterAssessment = (
    temporal_module.TemporalEncounterAssessment
)


# ======================================================================
# SAFETY DECISION
# ======================================================================

class SafetyDecision(Enum):

    PROCEED = "PROCEED"

    CAUTION = "CAUTION"

    DO_NOT_ENTER = "DO_NOT_ENTER"

    SAFETY_OVERRIDE = "SAFETY_OVERRIDE"


# ======================================================================
# ARBITRATION RESULT
# ======================================================================

@dataclass(frozen=True)
class SafetyAssessment:

    decision: SafetyDecision

    temporal_state: TemporalState

    ttc: Optional[float]

    safety_cleared: bool

    reason: str

    observation_visible: bool

    closing: bool


# ======================================================================
# SAFETY ARBITRATOR
# ======================================================================

class SafetyArbitrator:

    VERSION = "0.10.2"

    def __init__(self):

        self.temporal = WildSentinel101()

    # ------------------------------------------------------------------
    # ARBITRATE
    # ------------------------------------------------------------------

    def arbitrate(
        self,
        assessment: TemporalEncounterAssessment,
    ) -> SafetyAssessment:
        """
        Convert a temporal encounter assessment into
        an explicit safety decision.

        This function deliberately does NOT invent probability.

        It applies conservative safety semantics.
        """

        state = assessment.state

        # --------------------------------------------------------------
        # 1. IN-WINDOW CONFLICT
        # --------------------------------------------------------------

        if state == TemporalState.IN_WINDOW_CONFLICT:

            return SafetyAssessment(
                decision=(
                    SafetyDecision.DO_NOT_ENTER
                ),
                temporal_state=state,
                ttc=assessment.ttc,
                safety_cleared=False,
                reason=(
                    "An encounter exists within "
                    "the current observation "
                    "horizon. Route is not safe "
                    "to enter."
                ),
                observation_visible=(
                    assessment.observation_visible
                ),
                closing=assessment.closing,
            )

        # --------------------------------------------------------------
        # 2. FUTURE CONFLICT
        # --------------------------------------------------------------

        if state == TemporalState.FUTURE_CONFLICT:

            return SafetyAssessment(
                decision=(
                    SafetyDecision.CAUTION
                ),
                temporal_state=state,
                ttc=assessment.ttc,
                safety_cleared=False,
                reason=(
                    "A closing trajectory indicates "
                    "a possible future conflict, but "
                    "the conflict is outside the "
                    "current observation horizon. "
                    "The route cannot be cleared."
                ),
                observation_visible=(
                    assessment.observation_visible
                ),
                closing=assessment.closing,
            )

        # --------------------------------------------------------------
        # 3. BLIND
        # --------------------------------------------------------------

        if state == TemporalState.BLIND:

            return SafetyAssessment(
                decision=(
                    SafetyDecision.CAUTION
                ),
                temporal_state=state,
                ttc=assessment.ttc,
                safety_cleared=False,
                reason=(
                    "Sensor visibility is unavailable. "
                    "Absence of observation cannot "
                    "be interpreted as absence of "
                    "wildlife."
                ),
                observation_visible=False,
                closing=assessment.closing,
            )

        # --------------------------------------------------------------
        # 4. UNKNOWN
        # --------------------------------------------------------------

        if state == TemporalState.UNKNOWN:

            return SafetyAssessment(
                decision=(
                    SafetyDecision.CAUTION
                ),
                temporal_state=state,
                ttc=assessment.ttc,
                safety_cleared=False,
                reason=(
                    "Temporal evidence is insufficient "
                    "to establish safety. Route remains "
                    "not cleared."
                ),
                observation_visible=(
                    assessment.observation_visible
                ),
                closing=assessment.closing,
            )

        # --------------------------------------------------------------
        # 5. CLOSING
        # --------------------------------------------------------------

        if state == TemporalState.CLOSING:

            return SafetyAssessment(
                decision=(
                    SafetyDecision.CAUTION
                ),
                temporal_state=state,
                ttc=assessment.ttc,
                safety_cleared=False,
                reason=(
                    "Wildlife trajectory is closing "
                    "toward the route. Safety cannot "
                    "be established."
                ),
                observation_visible=(
                    assessment.observation_visible
                ),
                closing=True,
            )

        # --------------------------------------------------------------
        # 6. MOVING AWAY
        #
        # Important:
        #
        # Moving away lowers immediate concern but
        # does NOT independently establish safety.
        # --------------------------------------------------------------

        if state == TemporalState.MOVING_AWAY:

            return SafetyAssessment(
                decision=(
                    SafetyDecision.CAUTION
                ),
                temporal_state=state,
                ttc=None,
                safety_cleared=False,
                reason=(
                    "Observed trajectory is moving "
                    "away from the route. Immediate "
                    "encounter risk is reduced, but "
                    "the route is not automatically "
                    "cleared."
                ),
                observation_visible=True,
                closing=False,
            )

        # --------------------------------------------------------------
        # 7. OBSERVED
        #
        # Observation alone does not prove safety.
        # --------------------------------------------------------------

        if state == TemporalState.OBSERVED:

            return SafetyAssessment(
                decision=(
                    SafetyDecision.CAUTION
                ),
                temporal_state=state,
                ttc=assessment.ttc,
                safety_cleared=False,
                reason=(
                    "Wildlife has been observed, but "
                    "observation alone does not "
                    "establish route safety."
                ),
                observation_visible=(
                    assessment.observation_visible
                ),
                closing=assessment.closing,
            )

        # --------------------------------------------------------------
        # 8. DEFENSIVE FALLBACK
        # --------------------------------------------------------------

        return SafetyAssessment(
            decision=(
                SafetyDecision.SAFETY_OVERRIDE
            ),
            temporal_state=state,
            ttc=assessment.ttc,
            safety_cleared=False,
            reason=(
                "Unrecognised temporal state. "
                "Safety cannot be established."
            ),
            observation_visible=(
                assessment.observation_visible
            ),
            closing=assessment.closing,
        )


# ======================================================================
# TEST HELPERS
# ======================================================================

def check(
    name: str,
    condition: bool,
):
    if condition:
        print(f"PASS  {name}")
        return 1

    print(f"FAIL  {name}")
    return 0


# ======================================================================
# ADVERSARIAL TEST SUITE
# ======================================================================

def run_v0102_tests():

    temporal = WildSentinel101()
    arbitrator = SafetyArbitrator()

    passed = 0
    failed = 0

    # --------------------------------------------------------------
    # TEST 01
    # In-window conflict must be DO NOT ENTER.
    # --------------------------------------------------------------
    
    assessment = temporal.assess(
    trajectory_start=(50.0, 20.0),
    trajectory_end=(50.0, 51.0),
    route="A",
    uncertainty=2.0,
    time_step_minutes=5.0,
    visible=True,
    )

    result = arbitrator.arbitrate(
        assessment
    )

    ok = (
        result.temporal_state
        == TemporalState.IN_WINDOW_CONFLICT
        and result.decision
        == SafetyDecision.DO_NOT_ENTER
        and not result.safety_cleared
    )

    if check(
        "In-window conflict cannot be cleared",
        ok,
    ):
        passed += 1
    else:
        failed += 1

    # --------------------------------------------------------------
    # TEST 02
    # Future conflict must not become PROCEED.
    # --------------------------------------------------------------

    assessment = temporal.assess(
        trajectory_start=(50.0, 20.0),
        trajectory_end=(50.0, 45.0),
        route="A",
        uncertainty=2.0,
        time_step_minutes=5.0,
        visible=True,
    )

    result = arbitrator.arbitrate(
        assessment
    )

    ok = (
        result.temporal_state
        == TemporalState.FUTURE_CONFLICT
        and result.decision
        == SafetyDecision.CAUTION
        and not result.safety_cleared
    )

    if check(
        "Future conflict remains uncleared",
        ok,
    ):
        passed += 1
    else:
        failed += 1

    # --------------------------------------------------------------
    # TEST 03
    # Blind period must not become SAFE.
    # --------------------------------------------------------------

    assessment = temporal.assess(
        trajectory_start=(50.0, 20.0),
        trajectory_end=(50.0, 15.0),
        route="A",
        uncertainty=2.0,
        time_step_minutes=5.0,
        visible=False,
    )

    result = arbitrator.arbitrate(
        assessment
    )

    ok = (
        result.decision
        != SafetyDecision.PROCEED
        and not result.safety_cleared
    )

    if check(
        "Blind period cannot clear safety",
        ok,
    ):
        passed += 1
    else:
        failed += 1

    # --------------------------------------------------------------
    # TEST 04
    # Moving away lowers risk but does not clear.
    # --------------------------------------------------------------

    assessment = temporal.assess(
        trajectory_start=(50.0, 20.0),
        trajectory_end=(50.0, 10.0),
        route="A",
        uncertainty=2.0,
        time_step_minutes=5.0,
        visible=True,
    )

    result = arbitrator.arbitrate(
        assessment
    )

    ok = (
        result.temporal_state
        == TemporalState.MOVING_AWAY
        and result.decision
        == SafetyDecision.CAUTION
        and not result.safety_cleared
    )

    if check(
        "Moving away is not automatic clearance",
        ok,
    ):
        passed += 1
    else:
        failed += 1

    # --------------------------------------------------------------
    # TEST 05
    # Unknown must remain uncleared.
    # --------------------------------------------------------------

    unknown = TemporalEncounterAssessment(
        state=TemporalState.UNKNOWN,
        ttc=None,
        intersects=False,
        observation_horizon=5.0,
        distance_start=20.0,
        distance_end=20.0,
        closing=False,
        observation_visible=True,
        safety_cleared=False,
        reason="Synthetic unknown state.",
    )

    result = arbitrator.arbitrate(
        unknown
    )

    ok = (
        result.decision
        == SafetyDecision.CAUTION
        and not result.safety_cleared
    )

    if check(
        "Unknown is not safe",
        ok,
    ):
        passed += 1
    else:
        failed += 1

    # --------------------------------------------------------------
    # TEST 06
    # Closing state must be caution.
    # --------------------------------------------------------------

    closing = TemporalEncounterAssessment(
        state=TemporalState.CLOSING,
        ttc=None,
        intersects=False,
        observation_horizon=5.0,
        distance_start=20.0,
        distance_end=15.0,
        closing=True,
        observation_visible=True,
        safety_cleared=False,
        reason="Synthetic closing state.",
    )

    result = arbitrator.arbitrate(
        closing
    )

    ok = (
        result.decision
        == SafetyDecision.CAUTION
        and not result.safety_cleared
    )

    if check(
        "Closing trajectory requires caution",
        ok,
    ):
        passed += 1
    else:
        failed += 1

    # --------------------------------------------------------------
    # TEST 07
    # Contradictory clearance attempt must fail.
    # --------------------------------------------------------------

    dangerous = TemporalEncounterAssessment(
        state=TemporalState.IN_WINDOW_CONFLICT,
        ttc=0.5,
        intersects=True,
        observation_horizon=5.0,
        distance_start=2.0,
        distance_end=1.0,
        closing=True,
        observation_visible=True,
        safety_cleared=False,
        reason="Synthetic dangerous state.",
    )

    result = arbitrator.arbitrate(
        dangerous
    )

    ok = (
        result.decision
        == SafetyDecision.DO_NOT_ENTER
        and not result.safety_cleared
    )

    if check(
        "Safety boundary cannot be overridden",
        ok,
    ):
        passed += 1
    else:
        failed += 1

    # --------------------------------------------------------------
    # TEST 08
    # Blind + future conflict remains caution.
    # --------------------------------------------------------------

    assessment = temporal.assess(
        trajectory_start=(50.0, 20.0),
        trajectory_end=(50.0, 45.0),
        route="A",
        uncertainty=2.0,
        time_step_minutes=5.0,
        visible=False,
    )

    result = arbitrator.arbitrate(
        assessment
    )

    ok = (
        result.temporal_state
        == TemporalState.FUTURE_CONFLICT
        and result.decision
        == SafetyDecision.CAUTION
        and not result.safety_cleared
    )

    if check(
        "Blind future conflict remains uncleared",
        ok,
    ):
        passed += 1
    else:
        failed += 1

    # --------------------------------------------------------------
    # TEST 09
    # Invalid horizon must still be rejected by V0.10.1.
    # --------------------------------------------------------------

    rejected = False

    try:

        temporal.assess(
            trajectory_start=(50.0, 20.0),
            trajectory_end=(50.0, 15.0),
            route="A",
            uncertainty=2.0,
            time_step_minutes=0.0,
            visible=True,
        )

    except ValueError:

        rejected = True

    if check(
        "Invalid observation horizon rejected",
        rejected,
    ):
        passed += 1
    else:
        failed += 1

    # --------------------------------------------------------------
    # TEST 10
    # No V0.10.2 result may claim safety clearance
    # for the conservative states.
    # --------------------------------------------------------------

    states = (
        TemporalState.FUTURE_CONFLICT,
        TemporalState.BLIND,
        TemporalState.UNKNOWN,
        TemporalState.CLOSING,
        TemporalState.MOVING_AWAY,
    )

    all_uncleared = True

    for state in states:

        synthetic = TemporalEncounterAssessment(
            state=state,
            ttc=None,
            intersects=False,
            observation_horizon=5.0,
            distance_start=20.0,
            distance_end=15.0,
            closing=(
                state == TemporalState.CLOSING
            ),
            observation_visible=(
                state != TemporalState.BLIND
            ),
            safety_cleared=False,
            reason="Synthetic safety invariant test.",
        )

        result = arbitrator.arbitrate(
            synthetic
        )

        if result.safety_cleared:
            all_uncleared = False

    if check(
        "Conservative temporal states never claim clearance",
        all_uncleared,
    ):
        passed += 1
    else:
        failed += 1

    # --------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "WILD SENTINEL V0.10.2"
    )
    print(
        "TEMPORAL SAFETY ARBITRATION ENGINE"
    )
    print("=" * 70)

    print(
        f"Tests passed: {passed}"
    )

    print(
        f"Tests failed: {failed}"
    )

    if failed:

        raise AssertionError(
            f"{failed} V0.10.2 test(s) failed."
        )

    print(
        "V0.10.2 TEST STATUS: PASS"
    )


# ======================================================================
# MAIN
# ======================================================================

if __name__ == "__main__":

    run_v0102_tests()