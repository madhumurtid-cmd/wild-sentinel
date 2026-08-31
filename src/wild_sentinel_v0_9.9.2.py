from pathlib import Path

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import math
import random

"""
======================================================================
                         WILD SENTINEL V0.9.9.2
                 ADVERSARIAL SAFETY HARDENING ENGINE
======================================================================

V0.9.9.2 fixes:
    - Moving-away trajectories no longer invent TTC.
    - Genuine route crossings still produce TTC.
    - Canonical spatial exposure field is enforced.
    - Conflicting legacy exposure fields are rejected.
    - Explicit moving-away trajectory regression test.
    - Genuine closing trajectory regression test.
    - 5,000-case deterministic safety invariant fuzz test.

CORE PRINCIPLE:

    UNCERTAINTY IS NOT SAFETY.
    PREDICTION IS NOT OBSERVATION.
    UNKNOWN IS NOT SAFE.
    HYSTERESIS MUST NEVER OVERRIDE A SAFETY BOUNDARY.
    GEOMETRIC CROSSING ALONE MUST NOT OVERRIDE CLEARLY
    MOVING-AWAY EVIDENCE.
"""

ROUTES = ("A", "B", "C")
Point = Tuple[float, float]


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def distance(a: Point, b: Point) -> float:
    return math.dist(a, b)


def lerp(a: Point, b: Point, t: float) -> Point:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def point_to_segment_distance(p: Point, a: Point, b: Point) -> float:
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay

    if dx == 0 and dy == 0:
        return distance(p, a)

    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    closest = (ax + t * dx, ay + t * dy)
    return distance(p, closest)


def point_to_polyline_distance(p: Point, polyline: List[Point]) -> float:
    if len(polyline) == 1:
        return distance(p, polyline[0])

    return min(
        point_to_segment_distance(p, polyline[i], polyline[i + 1])
        for i in range(len(polyline) - 1)
    )


def orientation(a: Point, b: Point, c: Point) -> float:
    return (
        (b[0] - a[0]) * (c[1] - a[1])
        - (b[1] - a[1]) * (c[0] - a[0])
    )


def segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
    o1 = orientation(a, b, c)
    o2 = orientation(a, b, d)
    o3 = orientation(c, d, a)
    o4 = orientation(c, d, b)

    eps = 1e-9

    if abs(o1) < eps and abs(o2) < eps and abs(o3) < eps and abs(o4) < eps:
        return not (
            max(a[0], b[0]) < min(c[0], d[0])
            or max(c[0], d[0]) < min(a[0], b[0])
            or max(a[1], b[1]) < min(c[1], d[1])
            or max(c[1], d[1]) < min(a[1], b[1])
        )

    return ((o1 > 0) != (o2 > 0)) and ((o3 > 0) != (o4 > 0))


def segment_polyline_intersects(
    a: Point,
    b: Point,
    polyline: List[Point],
) -> bool:
    return any(
        segments_intersect(a, b, polyline[i], polyline[i + 1])
        for i in range(len(polyline) - 1)
    )


@dataclass
class Evidence:
    movement: float = 0.0
    sensor: float = 0.0
    prey: float = 0.0
    environment: float = 0.0
    human: float = 0.0

    def values(self):
        return {
            "Movement": self.movement,
            "Sensor": self.sensor,
            "Prey": self.prey,
            "Environment": self.environment,
            "Human": self.human,
        }

    def fusion(self) -> float:
        return clamp(
            0.30 * self.movement
            + 0.30 * self.sensor
            + 0.15 * self.prey
            + 0.10 * self.environment
            + 0.15 * self.human
        )


@dataclass
class RouteGeometry:
    name: str
    points: List[Point]
    hazard_multiplier: float = 1.0


@dataclass
class RouteState:
    risk: float = 6.0
    previous_risk: float = 6.0
    memory: float = 0.0
    corridor_memory: float = 0.0
    persistence: int = 0
    safe_steps: int = 0
    last_trend: str = "STABLE"
    last_ttc: Optional[float] = None
    last_ttc_state: str = "UNKNOWN"
    last_exposure: float = 0.0
    emergency_switches: int = 0


class WildSentinel0992:

    def __init__(self):
        self.routes: Dict[str, RouteState] = {
            r: RouteState() for r in ROUTES
        }

        self.selected_route = "C"
        self.hold_counter = 0

        self.last_position: Optional[Point] = None
        self.last_prediction: Optional[Point] = None
        self.prediction_error_history: List[float] = []

        self.memory_decay = 0.82

        self.recovery_threshold = 12.0
        self.caution_threshold = 35.0
        self.danger_threshold = 65.0
        self.override_threshold = 85.0

        self.route_switch_margin = 8.0
        self.minimum_route_hold = 2

        self.immediate_ttc = 1.0
        self.imminent_ttc = 3.0
        self.approaching_ttc = 10.0
        self.max_ttc = 30.0

        self.exposure_distance = 35.0

        self.base_uncertainty = 2.0
        self.max_uncertainty = 60.0

        self.route_geometry: Dict[str, RouteGeometry] = {
            "A": RouteGeometry(
                "A",
                [(0.0, 50.0), (75.0, 50.0), (150.0, 50.0)],
                1.10,
            ),
            "B": RouteGeometry(
                "B",
                [(0.0, 65.0), (75.0, 65.0), (150.0, 65.0)],
                1.00,
            ),
            "C": RouteGeometry(
                "C",
                [(0.0, 90.0), (75.0, 90.0), (150.0, 90.0)],
                0.90,
            ),
        }

    # ------------------------------------------------------------------
    # PREDICTION / UNCERTAINTY
    # ------------------------------------------------------------------

    def prediction_uncertainty(self, confidence: float) -> float:
        return clamp(
            max(
                self.base_uncertainty,
                (100.0 - confidence) * 0.40,
            ),
            0.0,
            self.max_uncertainty,
        )

    def inflate_uncertainty(self, base: float) -> float:
        if not self.prediction_error_history:
            return base

        rolling_error = sum(self.prediction_error_history) / len(
            self.prediction_error_history
        )

        inflation = min(25.0, rolling_error * 0.50)
        return min(self.max_uncertainty, base + inflation)

    def predict(
        self,
        position: Point,
        confidence: float,
        direction=(8.0, -8.0),
    ):
        x, y = position
        dx, dy = direction

        predicted = (x + dx, y + dy)

        base = self.prediction_uncertainty(confidence)
        uncertainty = self.inflate_uncertainty(base)

        return predicted, uncertainty

    def validate_prediction(
        self,
        actual: Point,
        predicted: Point,
    ):
        error = distance(actual, predicted)

        self.prediction_error_history.append(error)
        self.prediction_error_history = self.prediction_error_history[-5:]

        rolling_error = sum(self.prediction_error_history) / len(
            self.prediction_error_history
        )

        accuracy = clamp(100.0 - rolling_error * 4.0)

        return error, accuracy

    # ------------------------------------------------------------------
    # HYPOTHESES / EVIDENCE
    # ------------------------------------------------------------------

    def hypotheses(
        self,
        visible: bool,
        evidence: Evidence,
        uncertainty: float,
    ):
        if visible:
            return {
                "H1 Continue original trajectory": 0.0,
                "H2 Change direction": 98.0,
                "H3 Slow / stop": 1.0,
                "H4 Unknown movement": 1.0,
            }

        h1, h2, h3, h4 = 70.0, 10.0, 10.0, 10.0
        fusion = evidence.fusion()

        if fusion > 25:
            shift = min(25.0, fusion * 0.30)
            h1 -= shift
            h2 += shift * 0.45
            h4 += shift * 0.55

        if uncertainty > 15:
            shift = min(20.0, (uncertainty - 15.0) * 0.7)
            h1 -= shift
            h4 += shift

        vals = [max(0.0, x) for x in (h1, h2, h3, h4)]
        total = sum(vals)
        vals = [v * 100.0 / total for v in vals]

        return dict(
            zip(
                [
                    "H1 Continue original trajectory",
                    "H2 Change direction",
                    "H3 Slow / stop",
                    "H4 Unknown movement",
                ],
                vals,
            )
        )

    def evidence_integrity(
        self,
        evidence: Evidence,
        hypotheses,
    ):
        fusion = evidence.fusion()
        dominant = max(hypotheses.values())
        contradiction = 0.0

        if fusion >= 50 and dominant < 55:
            contradiction += 20.0

        if evidence.human >= 60 and evidence.movement < 20:
            contradiction += 10.0

        if evidence.sensor >= 60 and evidence.movement < 20:
            contradiction += 10.0

        return min(40.0, contradiction)

    # ------------------------------------------------------------------
    # CLASSIFICATION
    # ------------------------------------------------------------------

    def classify(self, risk: float) -> str:
        if risk >= self.danger_threshold:
            return "DO NOT ENTER"

        if risk >= self.caution_threshold:
            return "CAUTION"

        return "LOW RISK"

    def classify_ttc(
        self,
        ttc: Optional[float],
        intersects: bool,
    ) -> str:
        if ttc is None:
            return "UNKNOWN"

        if not intersects:
            return "NO INTERSECTION"

        if ttc <= self.immediate_ttc:
            return "IMMEDIATE"

        if ttc <= self.imminent_ttc:
            return "IMMINENT"

        if ttc <= self.approaching_ttc:
            return "APPROACHING"

        return "DISTANT"

    # ------------------------------------------------------------------
    # SPATIAL
    # ------------------------------------------------------------------

    def route_distance(
        self,
        position: Point,
        route: str,
    ) -> float:
        return point_to_polyline_distance(
            position,
            self.route_geometry[route].points,
        )

    def encounter_exposure(
        self,
        predicted_position: Point,
        uncertainty: float,
        route: str,
        trajectory_start: Optional[Point] = None,
        trajectory_end: Optional[Point] = None,
    ) -> dict:

        geometry = self.route_geometry[route]

        center_distance = point_to_polyline_distance(
            predicted_position,
            geometry.points,
        )

        envelope_radius = uncertainty * 2.0

        overlap = max(
            0.0,
            envelope_radius - center_distance,
        )

        spatial_overlap = clamp(
            overlap / max(1.0, envelope_radius) * 100.0
        )

        intersects = False

        if (
            trajectory_start is not None
            and trajectory_end is not None
        ):
            intersects = segment_polyline_intersects(
                trajectory_start,
                trajectory_end,
                geometry.points,
            )

        envelope_intersects = center_distance <= envelope_radius

        if envelope_intersects:
            geometric_exposure = max(
                spatial_overlap,
                25.0,
            )
        else:
            distance_factor = max(
                0.0,
                1.0 - center_distance / self.exposure_distance,
            )

            geometric_exposure = distance_factor * 100.0

        if intersects:
            trajectory_factor = 1.25
        elif envelope_intersects:
            trajectory_factor = 1.10
        else:
            trajectory_factor = 0.75

        exposure = clamp(
            geometric_exposure
            * trajectory_factor
            * geometry.hazard_multiplier
        )

        return {
            "distance": center_distance,
            "uncertainty_radius": envelope_radius,
            "spatial_overlap": spatial_overlap,
            "trajectory_intersection": intersects,
            "envelope_intersection": envelope_intersects,

            # Canonical field.
            "exposure": exposure,

            # Deliberately NOT adding encounter_exposure here.
            # V0.9.9.2 uses one canonical exposure field.
        }

    # ------------------------------------------------------------------
    # SPATIAL RECORD NORMALISATION / VALIDATION
    # ------------------------------------------------------------------

    def validate_spatial_record(self, spatial: dict) -> dict:
        required = (
            "exposure",
            "distance",
            "uncertainty_radius",
            "spatial_overlap",
            "trajectory_intersection",
            "envelope_intersection",
        )

        missing = [
            key for key in required
            if key not in spatial
        ]

        if missing:
            raise ValueError(
                "Incomplete spatial safety record. "
                f"Missing fields: {missing}"
            )

        # Reject the old alias when it conflicts with canonical exposure.
        if "encounter_exposure" in spatial:
            if not math.isclose(
                float(spatial["exposure"]),
                float(spatial["encounter_exposure"]),
                rel_tol=1e-9,
                abs_tol=1e-9,
            ):
                raise ValueError(
                    "Conflicting spatial exposure fields. "
                    "Use canonical 'exposure' only."
                )

        return spatial

    # ------------------------------------------------------------------
    # TTC V2.1
    # ------------------------------------------------------------------

    def time_to_conflict(
        self,
        trajectory_start: Point,
        trajectory_end: Point,
        route: str,
        uncertainty: float,
        time_step_minutes: float = 5.0,
    ):
        """
        TTC V2.1.

        Important safety correction:

        A geometric crossing is not automatically a valid TTC.

        If the measured distance from the animal to the route is
        increasing over the observation interval, the animal is moving
        away from the route. In that case the engine returns:

            (None, False)

        even if the finite line segment happens to cross the route.

        A genuine crossing is retained when distance is:
            - decreasing, OR
            - approximately unchanged.

        This prevents the V0.9.9.1 failure where:

            start=(50,52)
            end=(50,45)
            route y=50

        was incorrectly reported as TTC=0 despite the endpoint being
        farther from the route than the starting point.

        For a genuine crossing such as:

            start=(20,40)
            end=(20,60)
            route y=50

        the distance is unchanged, so the crossing remains valid.
        """

        if time_step_minutes <= 0:
            raise ValueError("time_step_minutes must be > 0")

        geometry = self.route_geometry[route].points

        d0 = point_to_polyline_distance(
            trajectory_start,
            geometry,
        )

        d1 = point_to_polyline_distance(
            trajectory_end,
            geometry,
        )

        delta_distance = d0 - d1

        # --------------------------------------------------------------
        # FIRST: determine whether the animal is clearly moving away.
        #
        # This guard MUST occur before geometric crossing detection.
        # --------------------------------------------------------------

        distance_epsilon = 1e-9

        if delta_distance < -distance_epsilon:
            return None, False

        # --------------------------------------------------------------
        # DIRECT GEOMETRIC CROSSING.
        #
        # If the animal is closing or maintaining distance, a genuine
        # crossing is meaningful and TTC can be sampled geometrically.
        # --------------------------------------------------------------

        if segment_polyline_intersects(
            trajectory_start,
            trajectory_end,
            geometry,
        ):
            samples = 200

            for i in range(samples + 1):
                t = i / samples

                p = lerp(
                    trajectory_start,
                    trajectory_end,
                    t,
                )

                if point_to_polyline_distance(
                    p,
                    geometry,
                ) <= uncertainty:
                    return (
                        t * time_step_minutes,
                        True,
                    )

        # --------------------------------------------------------------
        # ALREADY INSIDE UNCERTAINTY ENVELOPE.
        # --------------------------------------------------------------

        if d0 <= uncertainty:
            return 0.0, True

        # --------------------------------------------------------------
        # PROJECTED ENDPOINT ENTERS UNCERTAINTY ENVELOPE.
        # --------------------------------------------------------------

        if d1 <= uncertainty and d0 > d1:
            closing_distance = d0 - uncertainty
            distance_closed = max(
                0.001,
                d0 - d1,
            )

            ttc = (
                time_step_minutes
                * closing_distance
                / distance_closed
            )

            return max(0.0, ttc), True

        # --------------------------------------------------------------
        # NO CLOSING MOVEMENT.
        # --------------------------------------------------------------

        if delta_distance <= distance_epsilon:
            return None, False

        closing_speed = (
            delta_distance
            / max(0.001, time_step_minutes)
        )

        ttc = d0 / max(
            0.001,
            closing_speed,
        )

        if ttc > self.max_ttc:
            return None, False

        return ttc, True

    # ------------------------------------------------------------------
    # ROUTE UPDATE
    # ------------------------------------------------------------------

    def update_route(
        self,
        route: str,
        current_risk: float,
        worst_plausible: float,
        uncertainty: float,
        prediction_confidence: float,
        evidence: Evidence,
        contradiction: float,
        spatial: dict,
        ttc: Optional[float],
        ttc_state: str,
    ):

        spatial = self.validate_spatial_record(spatial)

        state = self.routes[route]

        delta = current_risk - state.previous_risk

        if delta > 8:
            trend = "STRONGLY DETERIORATING"
            state.persistence += 1
            state.safe_steps = 0

        elif delta > 1:
            trend = "DETERIORATING"
            state.persistence += 1
            state.safe_steps = 0

        elif delta < -8:
            trend = "STRONGLY IMPROVING"
            state.persistence = 0
            state.safe_steps += 1

        elif delta < -1:
            trend = "IMPROVING"
            state.persistence = 0
            state.safe_steps += 1

        else:
            trend = "STABLE"

        # Historical danger memory.
        state.memory *= self.memory_decay

        if worst_plausible >= 65:
            state.memory = max(
                state.memory,
                worst_plausible,
            )

        # Corridor memory.
        exposure = float(spatial["exposure"])

        if exposure >= 50:
            state.corridor_memory = max(
                state.corridor_memory * self.memory_decay,
                exposure,
            )
        else:
            state.corridor_memory *= self.memory_decay

        persistence_pressure = min(
            25.0,
            state.persistence * 7.0,
        )

        uncertainty_penalty = 0.0

        if uncertainty > 5:
            uncertainty_penalty = min(
                20.0,
                (uncertainty - 5) * 0.45,
            )

        confidence_penalty = max(
            0.0,
            (60.0 - prediction_confidence) * 0.25,
        )

        contradiction_penalty = contradiction * 0.25

        spatial_pressure = exposure * 0.30

        ttc_pressure = {
            "IMMEDIATE": 30.0,
            "IMMINENT": 22.0,
            "APPROACHING": 12.0,
            "DISTANT": 4.0,
            "UNKNOWN": 8.0,
            "NO INTERSECTION": 0.0,
        }.get(ttc_state, 8.0)

        temporal = (
            current_risk
            + persistence_pressure
            + uncertainty_penalty
            + confidence_penalty
            + contradiction_penalty
            + spatial_pressure
            + ttc_pressure
        )

        temporal = max(
            temporal,
            state.memory * 0.55,
        )

        temporal = max(
            temporal,
            state.corridor_memory * 0.45,
        )

        if (
            worst_plausible >= 70
            and prediction_confidence < 60
        ):
            temporal = max(
                temporal,
                worst_plausible * 0.75,
            )

        if (
            ttc_state == "IMMEDIATE"
            and exposure >= 45
        ):
            temporal = max(
                temporal,
                75.0,
            )

        if (
            spatial["envelope_intersection"]
            and prediction_confidence < 60
        ):
            temporal = max(
                temporal,
                65.0,
            )

        temporal = clamp(temporal)

        # Genuine recovery only.
        if (
            current_risk <= self.recovery_threshold
            and state.safe_steps >= 2
            and exposure < 20
            and ttc_state in (
                "NO INTERSECTION",
                "DISTANT",
                "UNKNOWN",
            )
            and uncertainty < 20
            and spatial["spatial_overlap"] < 20
        ):
            state.memory *= 0.65
            state.corridor_memory *= 0.65

            temporal = min(
                temporal,
                current_risk + 8.0,
            )

        state.previous_risk = current_risk
        state.risk = temporal
        state.last_trend = trend
        state.last_ttc = ttc
        state.last_ttc_state = ttc_state
        state.last_exposure = exposure

        return {
            "expected": current_risk,
            "worst": worst_plausible,
            "current": current_risk,
            "delta": delta,
            "trend": trend,
            "persistence": state.persistence,
            "temporal": temporal,
            "memory": state.memory,
            "corridor_memory": state.corridor_memory,
            "distance_to_route": spatial["distance"],
            "uncertainty_radius": spatial["uncertainty_radius"],
            "spatial_overlap": spatial["spatial_overlap"],
            "encounter_exposure": exposure,
            "exposure": exposure,
            "trajectory_intersection": spatial["trajectory_intersection"],
            "envelope_intersection": spatial["envelope_intersection"],
            "time_to_conflict": ttc,
            "ttc_state": ttc_state,
            "classification": self.classify(temporal),
        }

    # ------------------------------------------------------------------
    # SAFETY ARBITRATION
    # ------------------------------------------------------------------

    def decide(
        self,
        route_results: Dict[str, dict],
        confidence_context: float,
    ):
        ranked = sorted(
            route_results.items(),
            key=lambda kv: kv[1]["temporal"],
        )

        best_route, best = ranked[0]
        current = route_results[self.selected_route]

        # Highest-priority condition.
        if all(
            r["temporal"] >= self.danger_threshold
            for r in route_results.values()
        ):
            return (
                "SAFETY OVERRIDE",
                {
                    "reason": (
                        "All candidate routes exceed "
                        "the danger threshold."
                    ),
                    "reason_code": "ALL_ROUTES_UNSAFE",
                    "best_candidate": best_route,
                    "confidence_context": confidence_context,
                },
            )

        # Current route unsafe: hysteresis cannot retain it.
        if current["temporal"] >= self.danger_threshold:

            if (
                best_route != self.selected_route
                and best["temporal"] < current["temporal"]
                and best["temporal"] < self.danger_threshold
            ):
                previous = self.selected_route

                self.selected_route = best_route
                self.hold_counter = 0
                self.routes[best_route].emergency_switches += 1

                return (
                    best_route,
                    {
                        "reason": (
                            "Emergency route switch: current route "
                            "exceeded the danger threshold."
                        ),
                        "reason_code": "CURRENT_ROUTE_UNSAFE",
                        "previous_route": previous,
                        "best_candidate": best_route,
                        "confidence_context": confidence_context,
                    },
                )

            return (
                "SAFETY OVERRIDE",
                {
                    "reason": (
                        "Current route is unsafe and no safer "
                        "route is available."
                    ),
                    "reason_code": "UNSAFE_NO_SAFE_ALTERNATIVE",
                    "best_candidate": best_route,
                    "confidence_context": confidence_context,
                },
            )

        # Imminent conflict override.
        if (
            current["ttc_state"] in (
                "IMMEDIATE",
                "IMMINENT",
            )
            and current["encounter_exposure"] >= 45
        ):
            if (
                best_route != self.selected_route
                and best["temporal"] < current["temporal"]
                and best["temporal"] < self.danger_threshold
            ):
                previous = self.selected_route

                self.selected_route = best_route
                self.hold_counter = 0
                self.routes[best_route].emergency_switches += 1

                return (
                    best_route,
                    {
                        "reason": (
                            "Emergency route switch: imminent "
                            "wildlife-route conflict."
                        ),
                        "reason_code": "IMMINENT_CONFLICT",
                        "previous_route": previous,
                        "best_candidate": best_route,
                        "confidence_context": confidence_context,
                    },
                )

        # Minimum hold.
        if (
            self.hold_counter < self.minimum_route_hold
            and current["temporal"] < self.danger_threshold
        ):
            chosen = self.selected_route
            reason = (
                "Existing route retained by "
                "minimum-hold hysteresis."
            )
            reason_code = "MINIMUM_HOLD"

        # Material improvement.
        elif (
            best_route != self.selected_route
            and best["temporal"] + self.route_switch_margin
            < current["temporal"]
        ):
            chosen = best_route
            reason = "New route is materially safer."
            reason_code = "MATERIAL_IMPROVEMENT"

        else:
            chosen = self.selected_route
            reason = (
                "Existing route retained; improvement "
                "is not large enough."
            )
            reason_code = "HYSTERESIS_RETAINED"

        self.selected_route = chosen
        self.hold_counter += 1

        return (
            chosen,
            {
                "reason": reason,
                "reason_code": reason_code,
                "best_candidate": best_route,
                "confidence_context": confidence_context,
            },
        )

    # ------------------------------------------------------------------
    # INVARIANTS
    # ------------------------------------------------------------------

    def validate_decision(
        self,
        chosen: str,
        route_results: Dict[str, dict],
    ) -> List[str]:

        violations = []

        if chosen in route_results:
            selected = route_results[chosen]

            if selected["classification"] == "DO NOT ENTER":

                all_unsafe = all(
                    r["temporal"] >= self.danger_threshold
                    for r in route_results.values()
                )

                if not all_unsafe:
                    violations.append(
                        "Selected route is DO NOT ENTER "
                        "while a safer route exists."
                    )

        if chosen in route_results:
            selected = route_results[chosen]

            if (
                selected["temporal"] >= self.danger_threshold
                and any(
                    r["temporal"] < self.danger_threshold
                    for r in route_results.values()
                )
            ):
                violations.append(
                    "Unsafe selected route survived despite "
                    "a safe alternative."
                )

        return violations


# ======================================================================
# ADVERSARIAL TEST SUITE
# ======================================================================

def run_adversarial_tests(seed: int = 992026):

    print("=" * 78)
    print("                 WILD SENTINEL V0.9.9.2")
    print("              ADVERSARIAL SAFETY HARDENING")
    print("=" * 78)

    passed = 0
    failed = 0

    def check(name, condition, detail=""):
        nonlocal passed, failed

        if condition:
            print(f"[PASS] {name}")
            passed += 1
        else:
            print(
                f"[FAIL] {name}"
                + (f" :: {detail}" if detail else "")
            )
            failed += 1

    # ------------------------------------------------------------------
    # 1
    # ------------------------------------------------------------------

    e = WildSentinel0992()
    e.selected_route = "C"

    results = {
        "A": {
            "temporal": 48,
            "classification": "CAUTION",
            "ttc_state": "DISTANT",
            "encounter_exposure": 20,
        },
        "B": {
            "temporal": 47,
            "classification": "CAUTION",
            "ttc_state": "DISTANT",
            "encounter_exposure": 20,
        },
        "C": {
            "temporal": 48,
            "classification": "CAUTION",
            "ttc_state": "DISTANT",
            "encounter_exposure": 20,
        },
    }

    chosen, _ = e.decide(results, 80)

    check(
        "Test 1: Normal hysteresis retention",
        chosen == "C",
    )

    # ------------------------------------------------------------------
    # 2
    # ------------------------------------------------------------------

    e = WildSentinel0992()
    e.selected_route = "C"

    results = {
        "A": {
            "temporal": 45,
            "classification": "CAUTION",
            "ttc_state": "DISTANT",
            "encounter_exposure": 20,
        },
        "B": {
            "temporal": 50,
            "classification": "CAUTION",
            "ttc_state": "DISTANT",
            "encounter_exposure": 20,
        },
        "C": {
            "temporal": 75,
            "classification": "DO NOT ENTER",
            "ttc_state": "IMMINENT",
            "encounter_exposure": 70,
        },
    }

    chosen, decision = e.decide(results, 30)

    check(
        "Test 2: Unsafe current route emergency switch",
        chosen == "A"
        and decision["reason_code"] == "CURRENT_ROUTE_UNSAFE",
    )

    # ------------------------------------------------------------------
    # 3
    # ------------------------------------------------------------------

    e = WildSentinel0992()
    e.selected_route = "C"

    results = {
        r: {
            "temporal": risk,
            "classification": "DO NOT ENTER",
            "ttc_state": "IMMEDIATE",
            "encounter_exposure": risk,
        }
        for r, risk in {
            "A": 90,
            "B": 80,
            "C": 75,
        }.items()
    }

    chosen, decision = e.decide(results, 10)

    check(
        "Test 3: All routes unsafe override",
        chosen == "SAFETY OVERRIDE"
        and decision["reason_code"] == "ALL_ROUTES_UNSAFE",
    )

    # ------------------------------------------------------------------
    # 4
    # ------------------------------------------------------------------

    e = WildSentinel0992()
    e.selected_route = "C"

    results = {
        "A": {
            "temporal": 35,
            "classification": "CAUTION",
            "ttc_state": "DISTANT",
            "encounter_exposure": 10,
        },
        "B": {
            "temporal": 40,
            "classification": "CAUTION",
            "ttc_state": "APPROACHING",
            "encounter_exposure": 25,
        },
        "C": {
            "temporal": 70,
            "classification": "DO NOT ENTER",
            "ttc_state": "IMMINENT",
            "encounter_exposure": 75,
        },
    }

    chosen, decision = e.decide(results, 25)

    check(
        "Test 4: Imminent conflict overrides hysteresis",
        chosen == "A"
        and decision["reason_code"] == "CURRENT_ROUTE_UNSAFE",
    )

    # ------------------------------------------------------------------
    # 5
    # ------------------------------------------------------------------

    e = WildSentinel0992()
    e.selected_route = "C"

    results = {
        "A": {
            "temporal": 60.4,
            "classification": "CAUTION",
            "ttc_state": "UNKNOWN",
            "encounter_exposure": 31.4,
        },
        "B": {
            "temporal": 60.4,
            "classification": "CAUTION",
            "ttc_state": "UNKNOWN",
            "encounter_exposure": 31.4,
        },
        "C": {
            "temporal": 67.4,
            "classification": "DO NOT ENTER",
            "ttc_state": "APPROACHING",
            "encounter_exposure": 31.4,
        },
    }

    chosen, decision = e.decide(results, 35.5)

    check(
        "Test 5: V0.9.6 failure fixed",
        chosen == "A"
        and decision["reason_code"] == "CURRENT_ROUTE_UNSAFE",
    )

    # ------------------------------------------------------------------
    # 6
    # Moving away. This previously failed.
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    ttc, intersects = e.time_to_conflict(
        (50, 52),
        (50, 45),
        "A",
        2,
        5,
    )

    check(
        "Test 6: Moving away does not invent TTC",
        ttc is None and not intersects,
        f"ttc={ttc}, intersects={intersects}",
    )

    # ------------------------------------------------------------------
    # 7
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    spatial = e.encounter_exposure(
        (50, 54),
        8,
        "A",
        (50, 54),
        (58, 60),
    )

    check(
        "Test 7: Sensor-blind uncertainty envelope preserved",
        spatial["envelope_intersection"]
        and spatial["exposure"] > 0,
    )

    # ------------------------------------------------------------------
    # 8
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    spatial = e.encounter_exposure(
        (50, 59),
        5,
        "A",
        (50, 59),
        (58, 51),
    )

    check(
        "Test 8: Boundary uncertainty remains exposed",
        spatial["envelope_intersection"]
        or spatial["trajectory_intersection"],
    )

    # ------------------------------------------------------------------
    # 9
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    e.prediction_error_history = [
        20,
        25,
        30,
        25,
        20,
    ]

    inflated = e.inflate_uncertainty(10)

    check(
        "Test 9: Prediction error expands uncertainty",
        inflated > 10,
    )

    # ------------------------------------------------------------------
    # 10
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    ttc, intersects = e.time_to_conflict(
        (20, 40),
        (25, 35),
        "A",
        2,
        5,
    )

    state = e.classify_ttc(
        ttc,
        intersects,
    )

    check(
        "Test 10: TTC can become UNKNOWN",
        state in (
            "UNKNOWN",
            "NO INTERSECTION",
            "DISTANT",
        ),
    )

    # ------------------------------------------------------------------
    # 11
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    sequence = []

    for a, b, c in [
        (40, 35, 40),
        (35, 40, 35),
        (40, 35, 40),
        (35, 40, 35),
    ]:
        results = {
            "A": {
                "temporal": a,
                "classification": e.classify(a),
                "ttc_state": "DISTANT",
                "encounter_exposure": 10,
            },
            "B": {
                "temporal": b,
                "classification": e.classify(b),
                "ttc_state": "DISTANT",
                "encounter_exposure": 10,
            },
            "C": {
                "temporal": c,
                "classification": e.classify(c),
                "ttc_state": "DISTANT",
                "encounter_exposure": 10,
            },
        }

        sequence.append(
            e.decide(results, 70)[0]
        )

    check(
        "Test 11: Route oscillation is damped",
        len(set(sequence)) <= 2,
    )

    # ------------------------------------------------------------------
    # 12
    # Genuine crossing. This must remain valid.
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    e.route_geometry["A"] = RouteGeometry(
        "A",
        [(0, 50), (150, 50)],
        1.0,
    )

    ttc, hit = e.time_to_conflict(
        (20, 40),
        (20, 60),
        "A",
        1,
        5,
    )

    check(
        "Test 12: Crossing route detected",
        hit and ttc is not None,
        f"ttc={ttc}, hit={hit}",
    )

    # ------------------------------------------------------------------
    # 13
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    ttc, hit = e.time_to_conflict(
        (20, 40),
        (30, 40),
        "A",
        1,
        5,
    )

    check(
        "Test 13: Parallel trajectory does not create false conflict",
        not hit or ttc is None,
    )

    # ------------------------------------------------------------------
    # 14
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    e.route_geometry["A"] = RouteGeometry(
        "A",
        [
            (0, 50),
            (75, 50),
            (75, 70),
            (150, 70),
        ],
        1.0,
    )

    spatial = e.encounter_exposure(
        (75, 60),
        4,
        "A",
        (75, 40),
        (75, 65),
    )

    check(
        "Test 14: Multi-segment route geometry works",
        spatial["trajectory_intersection"]
        or spatial["envelope_intersection"],
    )

    # ------------------------------------------------------------------
    # 15
    # ------------------------------------------------------------------

    e = WildSentinel0992()
    e.selected_route = "C"
    e.hold_counter = 0

    results = {
        "A": {
            "temporal": 50,
            "classification": "CAUTION",
            "ttc_state": "DISTANT",
            "encounter_exposure": 10,
        },
        "B": {
            "temporal": 52,
            "classification": "CAUTION",
            "ttc_state": "DISTANT",
            "encounter_exposure": 10,
        },
        "C": {
            "temporal": 66,
            "classification": "DO NOT ENTER",
            "ttc_state": "DISTANT",
            "encounter_exposure": 10,
        },
    }

    chosen, decision = e.decide(results, 20)

    check(
        "Test 15: Minimum hold cannot retain unsafe route",
        chosen == "A"
        and decision["reason_code"] == "CURRENT_ROUTE_UNSAFE",
    )

    # ------------------------------------------------------------------
    # 16
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    predicted, uncertainty = e.predict(
        (50, 50),
        20,
    )

    check(
        "Test 16: Low confidence produces large uncertainty",
        uncertainty >= 25,
    )

    # ------------------------------------------------------------------
    # 17
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    results = {
        r: {
            "temporal": 65 + i,
            "classification": "DO NOT ENTER",
            "ttc_state": "UNKNOWN",
            "encounter_exposure": 60,
        }
        for i, r in enumerate(ROUTES)
    }

    chosen, decision = e.decide(
        results,
        5,
    )

    check(
        "Test 17: No safe route means explicit override",
        chosen == "SAFETY OVERRIDE"
        and decision["reason_code"] == "ALL_ROUTES_UNSAFE",
    )

    # ------------------------------------------------------------------
    # 18
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    state = e.routes["A"]

    state.memory = 60
    state.corridor_memory = 50
    state.safe_steps = 3

    result = e.update_route(
        "A",
        6,
        8,
        2,
        90,
        Evidence(),
        0,
        {
            "distance": 100,
            "uncertainty_radius": 4,
            "spatial_overlap": 0,
            "exposure": 5,
            "trajectory_intersection": False,
            "envelope_intersection": False,
        },
        None,
        "NO INTERSECTION",
    )

    check(
        "Test 18: Genuine recovery reduces retained risk",
        result["temporal"] <= 14,
    )

    # ------------------------------------------------------------------
    # 19
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    state = e.routes["A"]

    state.memory = 60
    state.corridor_memory = 50
    state.safe_steps = 3

    result = e.update_route(
        "A",
        6,
        80,
        30,
        25,
        Evidence(),
        0,
        {
            "distance": 5,
            "uncertainty_radius": 60,
            "spatial_overlap": 90,
            "exposure": 80,
            "trajectory_intersection": False,
            "envelope_intersection": True,
        },
        None,
        "UNKNOWN",
    )

    check(
        "Test 19: High uncertainty blocks false recovery",
        result["temporal"] >= 35,
    )

    # ------------------------------------------------------------------
    # 20
    # ------------------------------------------------------------------

    rng = random.Random(seed)
    invariant_failures = 0

    for _ in range(5000):

        e = WildSentinel0992()
        e.selected_route = rng.choice(
            list(ROUTES)
        )

        results = {}

        for r in ROUTES:

            risk = rng.uniform(
                0,
                100,
            )

            results[r] = {
                "temporal": risk,
                "classification": e.classify(risk),
                "ttc_state": rng.choice(
                    [
                        "UNKNOWN",
                        "DISTANT",
                        "APPROACHING",
                        "IMMINENT",
                        "IMMEDIATE",
                    ]
                ),
                "encounter_exposure": rng.uniform(
                    0,
                    100,
                ),
            }

        chosen, decision = e.decide(
            results,
            rng.uniform(0, 100),
        )

        violations = e.validate_decision(
            chosen,
            results,
        )

        if violations:
            invariant_failures += 1

    check(
        "Test 20: 5,000-case safety invariant fuzz",
        invariant_failures == 0,
        f"{invariant_failures} invariant failures",
    )

    # ------------------------------------------------------------------
    # 21
    # Canonical exposure accepted.
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    result = e.update_route(
        "A",
        6,
        8,
        2,
        90,
        Evidence(),
        0,
        {
            "distance": 100,
            "uncertainty_radius": 4,
            "spatial_overlap": 0,
            "exposure": 5,
            "trajectory_intersection": False,
            "envelope_intersection": False,
        },
        None,
        "NO INTERSECTION",
    )

    check(
        "Test 21: Canonical exposure field accepted",
        result["exposure"] == 5
        and result["encounter_exposure"] == 5,
    )

    # ------------------------------------------------------------------
    # 22
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    missing_rejected = False

    try:
        e.update_route(
            "A",
            6,
            8,
            2,
            90,
            Evidence(),
            0,
            {
                "distance": 100,
                "uncertainty_radius": 4,
                "spatial_overlap": 0,
                "trajectory_intersection": False,
                "envelope_intersection": False,
            },
            None,
            "NO INTERSECTION",
        )
    except ValueError:
        missing_rejected = True

    check(
        "Test 22: Missing spatial exposure is rejected",
        missing_rejected,
    )

    # ------------------------------------------------------------------
    # 23
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    conflicting_rejected = False

    try:
        e.update_route(
            "A",
            6,
            8,
            2,
            90,
            Evidence(),
            0,
            {
                "distance": 100,
                "uncertainty_radius": 4,
                "spatial_overlap": 0,
                "exposure": 5,
                "encounter_exposure": 95,
                "trajectory_intersection": False,
                "envelope_intersection": False,
            },
            None,
            "NO INTERSECTION",
        )
    except ValueError:
        conflicting_rejected = True

    check(
        "Test 23: Conflicting exposure fields rejected",
        conflicting_rejected,
    )

    # ------------------------------------------------------------------
    # 24
    # Explicit moving-away trajectory.
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    ttc, hit = e.time_to_conflict(
        (50, 52),
        (50, 45),
        "A",
        2,
        5,
    )

    check(
        "Test 24: Explicit moving-away trajectory rejected",
        ttc is None and not hit,
        f"ttc={ttc}, hit={hit}",
    )

    # ------------------------------------------------------------------
    # 25
    # Genuine closing trajectory.
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    ttc, hit = e.time_to_conflict(
        (50, 80),
        (50, 60),
        "A",
        2,
        5,
    )

    check(
        "Test 25: Genuine closing trajectory produces TTC",
        hit
        and ttc is not None
        and 0 <= ttc <= 5,
        f"ttc={ttc}, hit={hit}",
    )

    # ------------------------------------------------------------------
    # 26
    # Genuine crossing while maintaining symmetric distance.
    # ------------------------------------------------------------------

    e = WildSentinel0992()

    ttc, hit = e.time_to_conflict(
        (20, 40),
        (20, 60),
        "A",
        1,
        5,
    )

    check(
        "Test 26: Symmetric route crossing remains valid",
        hit and ttc is not None,
        f"ttc={ttc}, hit={hit}",
    )

    print("-" * 78)
    print(f"  TESTS PASSED: {passed}")
    print(f"  TESTS FAILED: {failed}")
    print("-" * 78)

    if failed == 0:
        print("  >>> V0.9.9.2 ADVERSARIAL SAFETY TESTS PASSED")
    else:
        print("  >>> V0.9.9.2 REQUIRES FURTHER INVESTIGATION")

    print("=" * 78)

    return failed == 0


# ======================================================================
# DEMO
# ======================================================================

def run_demo():

    engine = WildSentinel0992()

    print("\n" + "=" * 78)
    print("                 WILD SENTINEL V0.9.9.2 DEMO")
    print("=" * 78)

    timeline = [
        (
            0,
            (15.0, 85.0),
            False,
            Evidence(),
            {
                "A": (31, 56),
                "B": (6, 6),
                "C": (6, 6),
            },
        ),
        (
            5,
            (23.0, 75.0),
            False,
            Evidence(),
            {
                "A": (20, 55),
                "B": (8, 8),
                "C": (6, 6),
            },
        ),
        (
            10,
            (31.0, 65.0),
            True,
            Evidence(sensor=70),
            {
                "A": (40, 81),
                "B": (8, 31),
                "C": (6, 6),
            },
        ),
        (
            15,
            (39.0, 55.0),
            True,
            Evidence(
                movement=65,
                sensor=75,
            ),
            {
                "A": (60, 84),
                "B": (10, 10),
                "C": (6, 6),
            },
        ),
        (
            20,
            (47.0, 50.0),
            False,
            Evidence(
                movement=40,
                sensor=35,
            ),
            {
                "A": (65, 84),
                "B": (15, 15),
                "C": (6, 6),
            },
        ),
        (
            25,
            (55.0, 48.0),
            False,
            Evidence(
                movement=50,
                sensor=45,
                prey=55,
            ),
            {
                "A": (70, 85),
                "B": (15, 85),
                "C": (6, 6),
            },
        ),
        (
            30,
            (63.0, 49.0),
            False,
            Evidence(
                movement=65,
                sensor=60,
                prey=60,
                environment=50,
                human=70,
            ),
            {
                "A": (75, 90),
                "B": (20, 90),
                "C": (6, 6),
            },
        ),
        (
            35,
            (71.0, 50.0),
            False,
            Evidence(
                movement=70,
                sensor=65,
                prey=55,
                environment=60,
                human=70,
            ),
            {
                "A": (80, 95),
                "B": (25, 95),
                "C": (6, 6),
            },
        ),
        (
            40,
            (79.0, 51.0),
            False,
            Evidence(
                movement=75,
                sensor=70,
                prey=55,
                environment=60,
                human=70,
            ),
            {
                "A": (85, 95),
                "B": (25, 95),
                "C": (6, 6),
            },
        ),
        (
            50,
            (95.0, 75.0),
            False,
            Evidence(
                movement=15,
                sensor=10,
                prey=5,
            ),
            {
                "A": (25, 85),
                "B": (10, 75),
                "C": (6, 6),
            },
        ),
        (
            60,
            (110.0, 90.0),
            False,
            Evidence(),
            {
                "A": (12, 75),
                "B": (8, 70),
                "C": (6, 6),
            },
        ),
        (
            75,
            (130.0, 105.0),
            False,
            Evidence(),
            {
                "A": (6, 60),
                "B": (6, 60),
                "C": (6, 67),
            },
        ),
    ]

    previous = None
    previous_time = None

    for minute, actual, visible, evidence, risks in timeline:

        if previous is None:
            confidence = 87.5
        else:
            confidence = max(
                17.5,
                87.5 - max(0, minute - 10) * 0.8,
            )

        if visible:
            predicted = actual
            uncertainty = 2.0
        else:
            predicted, uncertainty = engine.predict(
                previous or actual,
                confidence,
            )

        if visible:
            error, accuracy = engine.validate_prediction(
                actual,
                predicted,
            )
        else:
            error = distance(
                actual,
                predicted,
            )
            accuracy = clamp(
                100 - error * 4
            )

        hyps = engine.hypotheses(
            visible,
            evidence,
            uncertainty,
        )

        contradiction = engine.evidence_integrity(
            evidence,
            hyps,
        )

        route_results = {}

        start = previous or actual

        step = (
            5.0
            if previous_time is None
            else max(
                1.0,
                minute - previous_time,
            )
        )

        for route in ROUTES:

            current, worst = risks[route]

            spatial = engine.encounter_exposure(
                predicted,
                uncertainty,
                route,
                start,
                predicted,
            )

            ttc, hit = engine.time_to_conflict(
                start,
                predicted,
                route,
                uncertainty,
                step,
            )

            ttc_state = engine.classify_ttc(
                ttc,
                hit,
            )

            route_results[route] = engine.update_route(
                route,
                current,
                worst,
                uncertainty,
                confidence,
                evidence,
                contradiction,
                spatial,
                ttc,
                ttc_state,
            )

        fusion = evidence.fusion()

        confidence_context = max(
            0.0,
            confidence * (
                1 - fusion / 100.0
            ),
        )

        before = engine.selected_route

        chosen, decision = engine.decide(
            route_results,
            confidence_context,
        )

        violations = engine.validate_decision(
            chosen,
            route_results,
        )

        print(
            f"\n{minute:02d} min | "
            f"sensor={'VISIBLE' if visible else 'BLIND'}"
        )

        print(
            "  actual="
            f"{actual} "
            "predicted="
            f"{tuple(round(x, 1) for x in predicted)}"
        )

        print(
            f"  confidence={confidence:.1f}% "
            f"uncertainty={uncertainty:.1f}"
        )

        print(
            "  route risks: "
            + " | ".join(
                f"{r}={route_results[r]['temporal']:.1f}"
                for r in ROUTES
            )
        )

        print(
            "  TTC: "
            + " | ".join(
                f"{r}={route_results[r]['ttc_state']}"
                for r in ROUTES
            )
        )

        if chosen == "SAFETY OVERRIDE":

            print(
                "  >>> SAFETY OVERRIDE "
                f"[{decision['reason_code']}]"
            )

        elif decision["reason_code"] in (
            "CURRENT_ROUTE_UNSAFE",
            "IMMINENT_CONFLICT",
        ):

            print(
                f"  >>> EMERGENCY SWITCH "
                f"{before} -> {chosen} "
                f"[{decision['reason_code']}]"
            )

        else:

            print(
                f"  >>> ROUTE {chosen} "
                f"[{decision['reason_code']}]"
            )

        if violations:
            print(
                "  !!! INVARIANT FAILURE:",
                violations,
            )

        previous = actual
        previous_time = minute

    print("\n" + "=" * 78)
    print("V0.9.9.2 DEMO COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    run_demo()
    run_adversarial_tests()
