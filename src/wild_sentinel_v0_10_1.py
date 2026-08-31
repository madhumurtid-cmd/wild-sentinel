"""
WILD SENTINEL V0.10.1
TEMPORAL ENCOUNTER STATE ENGINE

V0.10.1 adds a temporal interpretation layer above the
frozen V0.9.9.4 safety engine.

CORE PRINCIPLE:

    UNKNOWN IS NOT SAFE.

The V0.9.9.4 engine deliberately reports TTC as
(None, False) when a conflict lies beyond the current
observation horizon.

V0.10.1 preserves that behaviour but distinguishes:

    NO OBSERVATION
    CLOSING
    FUTURE CONFLICT
    IN-WINDOW CONFLICT
    MOVING AWAY
    UNKNOWN

It does NOT invent an encounter probability.

V0.9.9.4 remains unchanged.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple


Point = Tuple[float, float]


# ======================================================================
# LOAD FROZEN V0.9.9.4 ENGINE
# ======================================================================

BASELINE_PATH = (
    Path(__file__).resolve().parent
    / "wild_sentinel_v0_9.9.4_clean.py"
)


def load_baseline_engine():
    """
    Load the frozen V0.9.9.4 implementation without modifying it.
    """

    spec = importlib.util.spec_from_file_location(
        "wild_sentinel_v0_9_9_4_clean",
        BASELINE_PATH,
    )

    if spec is None or spec.loader is None:
        raise ImportError(
            f"Unable to load baseline engine: {BASELINE_PATH}"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module.WildSentinel0994


WildSentinel0994 = load_baseline_engine()


# ======================================================================
# TEMPORAL STATE
# ======================================================================


class TemporalState(Enum):

    OBSERVED = "OBSERVED"

    BLIND = "BLIND"

    CLOSING = "CLOSING"

    FUTURE_CONFLICT = "FUTURE_CONFLICT"

    IN_WINDOW_CONFLICT = "IN_WINDOW_CONFLICT"

    MOVING_AWAY = "MOVING_AWAY"

    UNKNOWN = "UNKNOWN"


# ======================================================================
# TEMPORAL ASSESSMENT
# ======================================================================


@dataclass(frozen=True)
class TemporalEncounterAssessment:

    state: TemporalState

    ttc: Optional[float]

    intersects: bool

    observation_horizon: float

    distance_start: float

    distance_end: float

    closing: bool

    observation_visible: bool

    safety_cleared: bool

    reason: str


# ======================================================================
# V0.10.1 ENGINE
# ======================================================================


class WildSentinel101:

    VERSION = "0.10.1"

    def __init__(self):

        self.base = WildSentinel0994()

    # ------------------------------------------------------------------
    # TEMPORAL ASSESSMENT
    # ------------------------------------------------------------------

    def assess(
        self,
        trajectory_start: Point,
	trajectory_end: Point,
        route: str,
        uncertainty: float,
        time_step_minutes: float = 5.0,
        visible: bool = True,
    ) -> TemporalEncounterAssessment:
        """
        Interpret the V0.9.9.4 TTC result temporally.

        IMPORTANT:

        V0.9.9.4 owns the geometric and TTC semantics.

        V0.10.1 only interprets the result in the context
        of observation visibility and trajectory direction.
        """

        if time_step_minutes <= 0:
            raise ValueError(
                "time_step_minutes must be > 0"
            )

        if uncertainty < 0:
            raise ValueError(
                "uncertainty must be >= 0"
            )

        geometry = self.base.route_geometry[route].points

        distance_start = (
            self.base.route_distance(
                trajectory_start,
                route,
            )
        )

        distance_end = (
            self.base.route_distance(
                trajectory_end,
                route,
            )
        )

        closing = (
            distance_end
            < distance_start
        )

        # --------------------------------------------------------------
        # ASK THE FROZEN V0.9.9.4 ENGINE
        # --------------------------------------------------------------

        ttc, intersects = (
            self.base.time_to_conflict(
                trajectory_start,
                trajectory_end,
                route,
                uncertainty,
                time_step_minutes,
            )
        )

        # --------------------------------------------------------------
        # 1. CURRENTLY INSIDE ENVELOPE
        # --------------------------------------------------------------

        if distance_start <= uncertainty:

            return TemporalEncounterAssessment(
                state=TemporalState.IN_WINDOW_CONFLICT,
                ttc=0.0,
                intersects=True,
                observation_horizon=time_step_minutes,
                distance_start=distance_start,
                distance_end=distance_end,
                closing=closing,
                observation_visible=visible,
                safety_cleared=False,
                reason=(
                    "Animal is already inside the "
                    "route uncertainty envelope."
                ),
            )

        # --------------------------------------------------------------
        # 2. MOVING AWAY
        # --------------------------------------------------------------

        if not closing:

            if visible:

                state = TemporalState.MOVING_AWAY
                reason = (
                    "Observed trajectory is moving "
                    "away from the route."
                )

            else:

                state = TemporalState.BLIND
                reason = (
                    "Sensor blind period prevents "
                    "confirmation of continued movement."
                )

            return TemporalEncounterAssessment(
                state=state,
                ttc=None,
                intersects=False,
                observation_horizon=time_step_minutes,
                distance_start=distance_start,
                distance_end=distance_end,
                closing=False,
                observation_visible=visible,
                safety_cleared=False,
                reason=reason,
            )

        # --------------------------------------------------------------
        # 3. VALID IN-WINDOW TTC
        # --------------------------------------------------------------

        if intersects and ttc is not None:

            return TemporalEncounterAssessment(
                state=TemporalState.IN_WINDOW_CONFLICT,
                ttc=ttc,
                intersects=True,
                observation_horizon=time_step_minutes,
                distance_start=distance_start,
                distance_end=distance_end,
                closing=True,
                observation_visible=visible,
                safety_cleared=False,
                reason=(
                    "Closing trajectory enters the "
                    "uncertainty envelope within "
                    "the current observation horizon."
                ),
            )

        # --------------------------------------------------------------
        # 4. CLOSING BUT TTC UNKNOWN
        #
        # This is the important V0.10.1 case.
        #
        # V0.9.9.4 deliberately returns:
        #
        #       (None, False)
        #
        # when the conflict is beyond the current
        # observation horizon.
        #
        # We must NOT convert that into SAFE.
        # --------------------------------------------------------------

        if closing and ttc is None:

            if visible:

                return TemporalEncounterAssessment(
                    state=TemporalState.FUTURE_CONFLICT,
                    ttc=None,
                    intersects=False,
                    observation_horizon=time_step_minutes,
                    distance_start=distance_start,
                    distance_end=distance_end,
                    closing=True,
                    observation_visible=True,
                    safety_cleared=False,
                    reason=(
                        "Trajectory is closing, but "
                        "conflict is not within the "
                        "current observation horizon."
                    ),
                )

            return TemporalEncounterAssessment(
                state=TemporalState.FUTURE_CONFLICT,
                ttc=None,
                intersects=False,
                observation_horizon=time_step_minutes,
                distance_start=distance_start,
                distance_end=distance_end,
                closing=True,
                observation_visible=False,
                safety_cleared=False,
                reason=(
                    "Sensor blind period prevents "
                    "direct observation. The last "
                    "known trajectory remains closing "
                    "and a future conflict cannot be "
                    "cleared."
                ),
            )

        # --------------------------------------------------------------
        # 5. FALLBACK UNKNOWN
        # --------------------------------------------------------------

        return TemporalEncounterAssessment(
            state=TemporalState.UNKNOWN,
            ttc=None,
            intersects=False,
            observation_horizon=time_step_minutes,
            distance_start=distance_start,
            distance_end=distance_end,
            closing=closing,
            observation_visible=visible,
            safety_cleared=False,
            reason=(
                "Insufficient temporal evidence to "
                "establish an encounter state."
            ),
        )


# ======================================================================
# ADVERSARIAL TESTS
# ======================================================================


def run_v0101_tests():

    engine = WildSentinel101()

    passed = 0
    failed = 0

    def check(name, condition):

        nonlocal passed, failed

        if condition:
            print(f"PASS  {name}")
            passed += 1
        else:
            print(f"FAIL  {name}")
            failed += 1

    # --------------------------------------------------------------
    # TEST 1
    # Moving away must never become a conflict.
    # --------------------------------------------------------------

    result = engine.assess(
        trajectory_start=(50.0, 20.0),
        trajectory_end=(50.0, 10.0),
        route="A",
        uncertainty=2.0,
        time_step_minutes=5.0,
        visible=True,
    )

    check(
        "Moving-away trajectory",
        result.state == TemporalState.MOVING_AWAY
        and result.safety_cleared is False,
    )

    # --------------------------------------------------------------
    # TEST 2
    # Closing trajectory with future conflict.
    # --------------------------------------------------------------

    result = engine.assess(
        trajectory_start=(50.0, 20.0),
        trajectory_end=(50.0, 45.0),
        route="A",
        uncertainty=2.0,
        time_step_minutes=5.0,
        visible=True,
    )

    check(
        "Closing future conflict",
        result.state == TemporalState.FUTURE_CONFLICT
        and result.ttc is None
        and result.safety_cleared is False,
    )

    # --------------------------------------------------------------
    # TEST 3
    # Already inside envelope.
    # --------------------------------------------------------------

    result = engine.assess(
        trajectory_start=(50.0, 51.0),
        trajectory_end=(50.0, 52.0),
        route="A",
        uncertainty=2.0,
        time_step_minutes=5.0,
        visible=True,
    )

    check(
        "Already inside envelope",
        result.state == TemporalState.IN_WINDOW_CONFLICT
        and result.ttc == 0.0
        and result.safety_cleared is False,
    )

    # --------------------------------------------------------------
    # TEST 4
    # Blind + closing must remain uncleared.
    # --------------------------------------------------------------

    result = engine.assess(
        trajectory_start=(50.0, 20.0),
        trajectory_end=(50.0, 45.0),
        route="A",
        uncertainty=2.0,
        time_step_minutes=5.0,
        visible=False,
    )

    check(
        "Blind closing trajectory",
        result.state == TemporalState.FUTURE_CONFLICT
        and result.observation_visible is False
        and result.safety_cleared is False,
    )

    # --------------------------------------------------------------
    # TEST 5
    # Invalid time step rejected.
    # --------------------------------------------------------------

    try:

        engine.assess(
            trajectory_start=(50.0, 20.0),
            trajectory_end=(50.0, 15.0),
            route="A",
            uncertainty=2.0,
            time_step_minutes=0.0,
        )

        invalid_time_rejected = False

    except ValueError:

        invalid_time_rejected = True

    check(
        "Zero time-step rejection",
        invalid_time_rejected,
    )

    # --------------------------------------------------------------
    # TEST 6
    # Closing trajectory enters the envelope within
    # the current observation horizon.
    # --------------------------------------------------------------

    result = engine.assess(
        trajectory_start=(50.0, 20.0),
        trajectory_end=(50.0, 49.0),
        route="A",
        uncertainty=2.0,
        time_step_minutes=5.0,
        visible=True,
    )

    check(
        "In-window conflict",
        result.state == TemporalState.IN_WINDOW_CONFLICT
        and result.ttc is not None
        and result.ttc <= 5.0
        and result.intersects is True
        and result.safety_cleared is False,
    )

    # --------------------------------------------------------------
    # TEST 7
    # Moving away must never become FUTURE_CONFLICT.
    # --------------------------------------------------------------

    result = engine.assess(
        trajectory_start=(50.0, 40.0),
        trajectory_end=(50.0, 20.0),
        route="A",
        uncertainty=2.0,
        time_step_minutes=5.0,
        visible=True,
    )

    check(
        "Moving away is not future conflict",
        result.state == TemporalState.MOVING_AWAY
        and result.state != TemporalState.FUTURE_CONFLICT,
    )

    # --------------------------------------------------------------
    # TEST 8
    # Blind observation must never manufacture safety.
    # --------------------------------------------------------------

    result = engine.assess(
        trajectory_start=(50.0, 40.0),
        trajectory_end=(50.0, 20.0),
        route="A",
        uncertainty=2.0,
        time_step_minutes=5.0,
        visible=False,
    )

    check(
        "Blind period does not clear safety",
        result.safety_cleared is False
        and result.observation_visible is False,
    )

        # --------------------------------------------------------------
    # TEST 9
    # Extending the observation horizon must not manufacture
    # an in-window conflict when the observed trajectory itself
    # never enters the uncertainty envelope.
    # --------------------------------------------------------------

    short_horizon = engine.assess(
        trajectory_start=(50.0, 20.0),
        trajectory_end=(50.0, 45.0),
        route="A",
        uncertainty=2.0,
        time_step_minutes=5.0,
        visible=True,
    )

    long_horizon = engine.assess(
        trajectory_start=(50.0, 20.0),
        trajectory_end=(50.0, 45.0),
        route="A",
        uncertainty=2.0,
        time_step_minutes=30.0,
        visible=True,
    )

    check(
        "Longer horizon does not manufacture conflict",
        short_horizon.state == TemporalState.FUTURE_CONFLICT
        and long_horizon.state == TemporalState.FUTURE_CONFLICT
        and short_horizon.safety_cleared is False
        and long_horizon.safety_cleared is False,
    )

    # --------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------

    print()
    print("=" * 70)
    print("WILD SENTINEL V0.10.1")
    print("TEMPORAL ENCOUNTER STATE ENGINE")
    print("=" * 70)
    print(
        f"Tests passed: {passed}"
    )
    print(
        f"Tests failed: {failed}"
    )

    if failed:

        raise AssertionError(
            f"{failed} V0.10.1 test(s) failed."
        )

    print("V0.10.1 TEST STATUS: PASS")


if __name__ == "__main__":

    run_v0101_tests()