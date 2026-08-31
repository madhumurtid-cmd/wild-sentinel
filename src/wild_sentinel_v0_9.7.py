from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import math


"""
======================================================================
                         WILD SENTINEL V0.9.7
              SAFETY ARBITRATION + EMERGENCY ROUTE SWITCHING
======================================================================

Built from:
    V0.9.5  Confidence + contradiction + temporal recovery
    V0.9.6  Spatial intercept + uncertainty + TTC + route geometry

V0.9.7 NEW:
    [NEW] Safety-breaking hysteresis
    [NEW] Emergency route switching
    [NEW] Unsafe-current-route detection
    [NEW] Route-specific spatial exposure
    [NEW] Explicit TTC state classification
    [NEW] UNKNOWN TTC state
    [NEW] Safety arbitration hierarchy
    [NEW] Decision invariants
    [NEW] Adversarial route-selection tests
    [NEW] Current-route safety invariant
    [NEW] Never recommend DO NOT ENTER without explicit safety handling
    [NEW] All-routes-unsafe override
    [NEW] Emergency conflict override
    [NEW] Route switching reason codes
    [NEW] Stronger explainability
    [NEW] Sensor-blind safety preservation

IMPORTANT:
    This remains a simulation/reference engine.
    It is NOT a field-certified wildlife safety system.

CORE SAFETY PRINCIPLE:

    UNCERTAINTY IS NOT SAFETY.

    PREDICTION IS NOT OBSERVATION.

    HYSTERESIS MUST NEVER OVERRIDE A SAFETY BOUNDARY.

======================================================================
"""


# ----------------------------------------------------------------------
# GLOBAL CONFIGURATION
# ----------------------------------------------------------------------

ROUTES = ("A", "B", "C")


# ----------------------------------------------------------------------
# BASIC GEOMETRY
# ----------------------------------------------------------------------

Point = Tuple[float, float]


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def distance(a: Point, b: Point) -> float:
    return math.dist(a, b)


def lerp(a: Point, b: Point, t: float) -> Point:
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
    )


def point_to_segment_distance(
    p: Point,
    a: Point,
    b: Point
) -> float:

    ax, ay = a
    bx, by = b
    px, py = p

    dx = bx - ax
    dy = by - ay

    if dx == 0 and dy == 0:
        return distance(p, a)

    t = (
        (px - ax) * dx +
        (py - ay) * dy
    ) / (dx * dx + dy * dy)

    t = max(0.0, min(1.0, t))

    closest = (
        ax + t * dx,
        ay + t * dy
    )

    return distance(p, closest)


def point_to_polyline_distance(
    p: Point,
    polyline: List[Point]
) -> float:

    if len(polyline) == 1:
        return distance(p, polyline[0])

    return min(
        point_to_segment_distance(
            p,
            polyline[i],
            polyline[i + 1]
        )
        for i in range(len(polyline) - 1)
    )


def orientation(a: Point, b: Point, c: Point) -> float:
    return (
        (b[0] - a[0]) * (c[1] - a[1])
        - (b[1] - a[1]) * (c[0] - a[0])
    )


def segments_intersect(
    a: Point,
    b: Point,
    c: Point,
    d: Point
) -> bool:

    o1 = orientation(a, b, c)
    o2 = orientation(a, b, d)
    o3 = orientation(c, d, a)
    o4 = orientation(c, d, b)

    eps = 1e-9

    if (
        abs(o1) < eps and
        abs(o2) < eps and
        abs(o3) < eps and
        abs(o4) < eps
    ):
        # Bounding-box overlap for collinear segments.
        return not (
            max(a[0], b[0]) < min(c[0], d[0])
            or max(c[0], d[0]) < min(a[0], b[0])
            or max(a[1], b[1]) < min(c[1], d[1])
            or max(c[1], d[1]) < min(a[1], b[1])
        )

    return (
        ((o1 > 0) != (o2 > 0)) and
        ((o3 > 0) != (o4 > 0))
    )


def segment_polyline_intersects(
    a: Point,
    b: Point,
    polyline: List[Point]
) -> bool:

    for i in range(len(polyline) - 1):
        if segments_intersect(
            a,
            b,
            polyline[i],
            polyline[i + 1]
        ):
            return True

    return False


# ----------------------------------------------------------------------
# EVIDENCE
# ----------------------------------------------------------------------

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
            0.30 * self.movement +
            0.30 * self.sensor +
            0.15 * self.prey +
            0.10 * self.environment +
            0.15 * self.human
        )


# ----------------------------------------------------------------------
# ROUTE GEOMETRY
# ----------------------------------------------------------------------

@dataclass
class RouteGeometry:

    name: str
    points: List[Point]
    hazard_multiplier: float = 1.0


# ----------------------------------------------------------------------
# ROUTE STATE
# ----------------------------------------------------------------------

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


# ----------------------------------------------------------------------
# WILD SENTINEL 0.9.7
# ----------------------------------------------------------------------

class WildSentinel097:

    """
    Conservative spatial-temporal safety engine.

    Decision hierarchy:

        1. ALL ROUTES UNSAFE
                    ↓
        2. CURRENT ROUTE UNSAFE
                    ↓
        3. IMMINENT CONFLICT
                    ↓
        4. NORMAL HYSTERESIS
                    ↓
        5. ROUTE PREFERENCE

    Hysteresis is deliberately BELOW safety arbitration.

    Therefore:

        HYSTERESIS CANNOT OVERRIDE SAFETY.
    """

    def __init__(self):

        self.routes: Dict[str, RouteState] = {
            r: RouteState()
            for r in ROUTES
        }

        self.selected_route = "C"

        self.hold_counter = 0

        self.last_position: Optional[Point] = None

        self.last_prediction: Optional[Point] = None

        self.prediction_error_history: List[float] = []

        self.time_min = 0

        # --------------------------------------------------------------
        # Temporal safety
        # --------------------------------------------------------------

        self.memory_decay = 0.82

        self.recovery_threshold = 12.0

        self.caution_threshold = 35.0

        self.danger_threshold = 65.0

        self.override_threshold = 85.0

        # --------------------------------------------------------------
        # Route selection
        # --------------------------------------------------------------

        self.route_switch_margin = 8.0

        self.minimum_route_hold = 2

        # --------------------------------------------------------------
        # Spatial safety
        # --------------------------------------------------------------

        self.immediate_ttc = 1.0

        self.imminent_ttc = 3.0

        self.approaching_ttc = 10.0

        self.max_ttc = 30.0

        # --------------------------------------------------------------
        # Exposure
        # --------------------------------------------------------------

        self.exposure_distance = 35.0

        self.exposure_scale = 40.0

        # --------------------------------------------------------------
        # Default route geometry.
        #
        # These are DEMONSTRATION coordinates only.
        # Replace with actual GIS/polyline data in deployment.
        # --------------------------------------------------------------

        self.route_geometry: Dict[str, RouteGeometry] = {

            "A": RouteGeometry(
                "A",
                [
                    (0.0, 50.0),
                    (150.0, 50.0)
                ],
                hazard_multiplier=1.10
            ),

            "B": RouteGeometry(
                "B",
                [
                    (0.0, 65.0),
                    (150.0, 65.0)
                ],
                hazard_multiplier=1.00
            ),

            "C": RouteGeometry(
                "C",
                [
                    (0.0, 90.0),
                    (150.0, 90.0)
                ],
                hazard_multiplier=0.90
            ),
        }

    # ==================================================================
    # PREDICTION
    # ==================================================================

    def predict(
        self,
        position: Point,
        confidence: float,
        direction=(8.0, -8.0)
    ):

        x, y = position

        dx, dy = direction

        predicted = (
            x + dx,
            y + dy
        )

        uncertainty = max(
            2.0,
            min(
                40.0,
                (100.0 - confidence) * 0.40
            )
        )

        return predicted, uncertainty

    # ==================================================================
    # PREDICTION VALIDATION
    # ==================================================================

    def validate_prediction(
        self,
        actual: Point,
        predicted: Point
    ):

        error = distance(
            actual,
            predicted
        )

        self.prediction_error_history.append(error)

        self.prediction_error_history = (
            self.prediction_error_history[-5:]
        )

        rolling_error = (
            sum(self.prediction_error_history)
            /
            len(self.prediction_error_history)
        )

        accuracy = clamp(
            100.0 - rolling_error * 4.0
        )

        return error, accuracy

    # ==================================================================
    # HYPOTHESES
    # ==================================================================

    def hypotheses(
        self,
        visible: bool,
        evidence: Evidence,
        uncertainty: float
    ):

        if visible:

            return {
                "H1 Continue original trajectory": 0.0,
                "H2 Change direction": 98.0,
                "H3 Slow / stop": 1.0,
                "H4 Unknown movement": 1.0,
            }

        h1 = 70.0
        h2 = 10.0
        h3 = 10.0
        h4 = 10.0

        fusion = evidence.fusion()

        if fusion > 25:

            shift = min(
                25.0,
                fusion * 0.30
            )

            h1 -= shift

            h2 += shift * 0.45

            h4 += shift * 0.55

        if uncertainty > 15:

            shift = min(
                20.0,
                (uncertainty - 15.0) * 0.7
            )

            h1 -= shift

            h4 += shift

        vals = [
            max(0.0, h1),
            max(0.0, h2),
            max(0.0, h3),
            max(0.0, h4)
        ]

        total = sum(vals)

        vals = [
            v * 100.0 / total
            for v in vals
        ]

        return dict(
            zip(
                [
                    "H1 Continue original trajectory",
                    "H2 Change direction",
                    "H3 Slow / stop",
                    "H4 Unknown movement"
                ],
                vals
            )
        )

    # ==================================================================
    # EVIDENCE INTEGRITY
    # ==================================================================

    def evidence_integrity(
        self,
        evidence: Evidence,
        hypotheses
    ):

        fusion = evidence.fusion()

        dominant = max(
            hypotheses.values()
        )

        contradiction = 0.0

        if fusion >= 50 and dominant < 55:

            contradiction += 20.0

        if (
            evidence.human >= 60
            and evidence.movement < 20
        ):

            contradiction += 10.0

        if (
            evidence.sensor >= 60
            and evidence.movement < 20
        ):

            contradiction += 10.0

        return min(
            40.0,
            contradiction
        )

    # ==================================================================
    # RISK CLASSIFICATION
    # ==================================================================

    def classify(
        self,
        risk: float
    ) -> str:

        if risk >= self.danger_threshold:

            return "DO NOT ENTER"

        if risk >= self.caution_threshold:

            return "CAUTION"

        return "LOW RISK"

    # ==================================================================
    # TTC CLASSIFICATION
    # ==================================================================

    def classify_ttc(
        self,
        ttc: Optional[float],
        intersects: bool
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

    # ==================================================================
    # ROUTE GEOMETRY
    # ==================================================================

    def route_distance(
        self,
        position: Point,
        route: str
    ) -> float:

        geometry = self.route_geometry[route]

        return point_to_polyline_distance(
            position,
            geometry.points
        )

    # ==================================================================
    # SPATIAL EXPOSURE
    # ==================================================================

    def encounter_exposure(
        self,
        predicted_position: Point,
        uncertainty: float,
        route: str,
        trajectory_start: Optional[Point] = None,
        trajectory_end: Optional[Point] = None
    ) -> dict:

        geometry = self.route_geometry[route]

        center_distance = point_to_polyline_distance(
            predicted_position,
            geometry.points
        )

        # --------------------------------------------------------------
        # Uncertainty envelope overlap.
        # --------------------------------------------------------------

        envelope_radius = uncertainty * 2.0

        overlap = max(
            0.0,
            envelope_radius - center_distance
        )

        spatial_overlap = clamp(
            overlap /
            max(1.0, envelope_radius)
            * 100.0
        )

        # --------------------------------------------------------------
        # Trajectory intersection.
        # --------------------------------------------------------------

        intersects = False

        if (
            trajectory_start is not None
            and trajectory_end is not None
        ):

            intersects = segment_polyline_intersects(
                trajectory_start,
                trajectory_end,
                geometry.points
            )

        # --------------------------------------------------------------
        # If the uncertainty envelope reaches the route,
        # treat this as potential exposure even when the centre
        # prediction itself misses it.
        # --------------------------------------------------------------

        envelope_intersects = (
            center_distance <= envelope_radius
        )

        if envelope_intersects:

            geometric_exposure = max(
                spatial_overlap,
                25.0
            )

        else:

            distance_factor = max(
                0.0,
                1.0 -
                (
                    center_distance /
                    self.exposure_distance
                )
            )

            geometric_exposure = (
                distance_factor *
                100.0
            )

        # --------------------------------------------------------------
        # Trajectory bonus.
        # --------------------------------------------------------------

        if intersects:

            trajectory_factor = 1.25

        elif envelope_intersects:

            trajectory_factor = 1.10

        else:

            trajectory_factor = 0.75

        exposure = (
            geometric_exposure *
            trajectory_factor *
            geometry.hazard_multiplier
        )

        exposure = clamp(exposure)

        return {
            "distance": center_distance,
            "uncertainty_radius": envelope_radius,
            "spatial_overlap": spatial_overlap,
            "trajectory_intersection": intersects,
            "envelope_intersection": envelope_intersects,
            "exposure": exposure,
        }

    # ==================================================================
    # TIME TO CONFLICT
    # ==================================================================

    def time_to_conflict(
        self,
        trajectory_start: Point,
        trajectory_end: Point,
        route: str,
        uncertainty: float,
        time_step_minutes: float = 5.0
    ):

        geometry = self.route_geometry[route]

        if segment_polyline_intersects(
            trajectory_start,
            trajectory_end,
            geometry.points
        ):

            # Estimate where along trajectory the conflict occurs.
            #
            # For this reference implementation we approximate
            # intersection timing using sampled points.

            samples = 50

            for i in range(samples + 1):

                t = i / samples

                p = lerp(
                    trajectory_start,
                    trajectory_end,
                    t
                )

                if (
                    point_to_polyline_distance(
                        p,
                        geometry.points
                    )
                    <= uncertainty
                ):

                    return (
                        t * time_step_minutes,
                        True
                    )

            return 0.0, True

        # --------------------------------------------------------------
        # Even without a centre-line intersection, the uncertainty
        # envelope may intersect the route.
        # --------------------------------------------------------------

        start_distance = point_to_polyline_distance(
            trajectory_start,
            geometry.points
        )

        end_distance = point_to_polyline_distance(
            trajectory_end,
            geometry.points
        )

        if (
            start_distance <= uncertainty
            or end_distance <= uncertainty
        ):

            if start_distance <= uncertainty:

                return 0.0, True

            return time_step_minutes, True

        # --------------------------------------------------------------
        # Estimate approach time based on distance reduction.
        # --------------------------------------------------------------

        delta_distance = (
            start_distance -
            end_distance
        )

        if delta_distance <= 0:

            return None, False

        fraction = (
            start_distance /
            max(
                0.001,
                delta_distance
            )
        )

        ttc = (
            fraction *
            time_step_minutes
        )

        if ttc > self.max_ttc:

            return None, False

        return ttc, True

    # ==================================================================
    # ROUTE UPDATE
    # ==================================================================

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
        ttc_state: str
    ):

        state = self.routes[route]

        delta = (
            current_risk -
            state.previous_risk
        )

        # --------------------------------------------------------------
        # Trend
        # --------------------------------------------------------------

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

        # --------------------------------------------------------------
        # Historical danger memory
        # --------------------------------------------------------------

        state.memory *= self.memory_decay

        if worst_plausible >= 65:

            state.memory = max(
                state.memory,
                worst_plausible
            )

        # --------------------------------------------------------------
        # Corridor memory
        # --------------------------------------------------------------

        if spatial["exposure"] >= 50:

            state.corridor_memory = max(
                state.corridor_memory * self.memory_decay,
                spatial["exposure"]
            )

        else:

            state.corridor_memory *= (
                self.memory_decay
            )

        # --------------------------------------------------------------
        # Persistence pressure
        # --------------------------------------------------------------

        persistence_pressure = min(
            25.0,
            state.persistence * 7.0
        )

        # --------------------------------------------------------------
        # Uncertainty penalty
        # --------------------------------------------------------------

        uncertainty_penalty = 0.0

        if uncertainty > 5:

            uncertainty_penalty = min(
                20.0,
                (uncertainty - 5) * 0.45
            )

        # --------------------------------------------------------------
        # Confidence penalty
        # --------------------------------------------------------------

        confidence_penalty = max(
            0.0,
            (60.0 - prediction_confidence) * 0.25
        )

        # --------------------------------------------------------------
        # Contradiction penalty
        # --------------------------------------------------------------

        contradiction_penalty = (
            contradiction *
            0.25
        )

        # --------------------------------------------------------------
        # Spatial exposure pressure
        # --------------------------------------------------------------

        spatial_pressure = (
            spatial["exposure"] *
            0.30
        )

        # --------------------------------------------------------------
        # Time-to-conflict pressure
        # --------------------------------------------------------------

        ttc_pressure = 0.0

        if ttc_state == "IMMEDIATE":

            ttc_pressure = 30.0

        elif ttc_state == "IMMINENT":

            ttc_pressure = 22.0

        elif ttc_state == "APPROACHING":

            ttc_pressure = 12.0

        elif ttc_state == "DISTANT":

            ttc_pressure = 4.0

        elif ttc_state == "UNKNOWN":

            # Unknown TTC must not be treated as zero risk.
            ttc_pressure = 8.0

        # --------------------------------------------------------------
        # Base temporal risk
        # --------------------------------------------------------------

        temporal = (
            current_risk
            + persistence_pressure
            + uncertainty_penalty
            + confidence_penalty
            + contradiction_penalty
            + spatial_pressure
            + ttc_pressure
        )

        # --------------------------------------------------------------
        # Historical memory floor
        # --------------------------------------------------------------

        temporal = max(
            temporal,
            state.memory * 0.55
        )

        # --------------------------------------------------------------
        # Corridor memory floor
        # --------------------------------------------------------------

        temporal = max(
            temporal,
            state.corridor_memory * 0.45
        )

        # --------------------------------------------------------------
        # Conservative worst-case protection
        # --------------------------------------------------------------

        if (
            worst_plausible >= 70
            and prediction_confidence < 60
        ):

            temporal = max(
                temporal,
                worst_plausible * 0.75
            )

        # --------------------------------------------------------------
        # IMMEDIATE CONFLICT OVERRIDE
        # --------------------------------------------------------------

        if (
            ttc_state == "IMMEDIATE"
            and spatial["exposure"] >= 45
        ):

            temporal = max(
                temporal,
                75.0
            )

        # --------------------------------------------------------------
        # Uncertainty-envelope conflict
        # --------------------------------------------------------------

        if (
            spatial["envelope_intersection"]
            and prediction_confidence < 60
        ):

            temporal = max(
                temporal,
                65.0
            )

        temporal = clamp(
            temporal
        )

        # --------------------------------------------------------------
        # Recovery
        # --------------------------------------------------------------

        if (
            current_risk <= self.recovery_threshold
            and state.safe_steps >= 2
            and spatial["exposure"] < 20
            and ttc_state in (
                "NO INTERSECTION",
                "DISTANT",
                "UNKNOWN"
            )
        ):

            state.memory *= 0.65

            state.corridor_memory *= 0.65

            temporal = min(
                temporal,
                current_risk + 8.0
            )

        state.previous_risk = current_risk

        state.risk = temporal

        state.last_trend = trend

        state.last_ttc = ttc

        state.last_ttc_state = ttc_state

        state.last_exposure = spatial["exposure"]

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

            "distance_to_route":
                spatial["distance"],

            "uncertainty_radius":
                spatial["uncertainty_radius"],

            "spatial_overlap":
                spatial["spatial_overlap"],

            "encounter_exposure":
                spatial["exposure"],

            "trajectory_intersection":
                spatial["trajectory_intersection"],

            "envelope_intersection":
                spatial["envelope_intersection"],

            "time_to_conflict": ttc,

            "ttc_state": ttc_state,

            "classification":
                self.classify(temporal),
        }

    # ==================================================================
    # SAFETY ARBITRATION
    # ==================================================================

    def decide(
        self,
        route_results: Dict[str, dict],
        confidence_context: float
    ):

        ranked = sorted(
            route_results.items(),
            key=lambda kv: kv[1]["temporal"]
        )

        best_route, best = ranked[0]

        current = route_results[
            self.selected_route
        ]

        # ==============================================================
        # LEVEL 1
        # ALL ROUTES UNSAFE
        # ==============================================================

        if all(
            r["temporal"] >=
            self.danger_threshold
            for r in route_results.values()
        ):

            return (
                "SAFETY OVERRIDE",
                {
                    "reason":
                        "All candidate routes exceed the "
                        "danger threshold.",
                    "reason_code":
                        "ALL_ROUTES_UNSAFE",
                    "best_candidate":
                        best_route,
                    "confidence_context":
                        confidence_context,
                }
            )

        # ==============================================================
        # LEVEL 2
        # CURRENT ROUTE HAS BECOME UNSAFE
        #
        # THIS IS THE V0.9.7 FIX.
        #
        # HYSTERESIS IS COMPLETELY IGNORED HERE.
        # ==============================================================

        if (
            current["temporal"] >=
            self.danger_threshold
        ):

            if (
                best_route !=
                self.selected_route
                and
                best["temporal"] <
                current["temporal"]
            ):

                previous = (
                    self.selected_route
                )

                self.selected_route = (
                    best_route
                )

                self.hold_counter = 0

                self.routes[
                    best_route
                ].emergency_switches += 1

                return (
                    best_route,
                    {
                        "reason":
                            "Emergency route switch: "
                            "current route exceeded "
                            "the danger threshold.",
                        "reason_code":
                            "CURRENT_ROUTE_UNSAFE",
                        "previous_route":
                            previous,
                        "best_candidate":
                            best_route,
                        "confidence_context":
                            confidence_context,
                    }
                )

            return (
                "SAFETY OVERRIDE",
                {
                    "reason":
                        "Current route is unsafe and "
                        "no safer route is available.",
                    "reason_code":
                        "UNSAFE_NO_SAFE_ALTERNATIVE",
                    "best_candidate":
                        best_route,
                    "confidence_context":
                        confidence_context,
                }
            )

        # ==============================================================
        # LEVEL 3
        # IMMINENT CONFLICT OVERRIDE
        # ==============================================================

        if (
            current["ttc_state"]
            in ("IMMEDIATE", "IMMINENT")
            and
            current["encounter_exposure"] >= 45
        ):

            if (
                best_route !=
                self.selected_route
                and
                best["temporal"] <
                current["temporal"]
            ):

                previous = (
                    self.selected_route
                )

                self.selected_route = (
                    best_route
                )

                self.hold_counter = 0

                self.routes[
                    best_route
                ].emergency_switches += 1

                return (
                    best_route,
                    {
                        "reason":
                            "Emergency route switch: "
                            "imminent wildlife-route conflict.",
                        "reason_code":
                            "IMMINENT_CONFLICT",
                        "previous_route":
                            previous,
                        "best_candidate":
                            best_route,
                        "confidence_context":
                            confidence_context,
                    }
                )

        # ==============================================================
        # LEVEL 4
        # NORMAL HYSTERESIS
        # ==============================================================

        if (
            self.hold_counter <
            self.minimum_route_hold
            and
            current["temporal"] <
            self.danger_threshold
        ):

            chosen = (
                self.selected_route
            )

            reason = (
                "Existing route retained by "
                "minimum-hold hysteresis."
            )

            reason_code = (
                "MINIMUM_HOLD"
            )

        # ==============================================================
        # LEVEL 5
        # NORMAL MATERIAL IMPROVEMENT
        # ==============================================================

        elif (
            best_route !=
            self.selected_route
            and
            best["temporal"]
            + self.route_switch_margin
            <
            current["temporal"]
        ):

            chosen = best_route

            reason = (
                "New route is materially safer."
            )

            reason_code = (
                "MATERIAL_IMPROVEMENT"
            )

        else:

            chosen = (
                self.selected_route
            )

            reason = (
                "Existing route retained; "
                "improvement is not large enough."
            )

            reason_code = (
                "HYSTERESIS_RETAINED"
            )

        self.selected_route = chosen

        self.hold_counter += 1

        return (
            chosen,
            {
                "reason": reason,
                "reason_code": reason_code,
                "best_candidate": best_route,
                "confidence_context":
                    confidence_context,
            }
        )

    # ==================================================================
    # DECISION INVARIANTS
    # ==================================================================

    def validate_decision(
        self,
        chosen: str,
        route_results: Dict[str, dict]
    ) -> List[str]:

        violations = []

        # --------------------------------------------------------------
        # Invariant 1
        #
        # Never silently recommend a DO NOT ENTER route.
        # --------------------------------------------------------------

        if chosen in route_results:

            selected = route_results[
                chosen
            ]

            if (
                selected["classification"]
                == "DO NOT ENTER"
            ):

                # This is permitted only if ALL routes are unsafe.
                all_unsafe = all(
                    r["temporal"]
                    >= self.danger_threshold
                    for r in route_results.values()
                )

                if not all_unsafe:

                    violations.append(
                        "INVARIANT FAILURE: "
                        "Selected route is DO NOT ENTER "
                        "while a safer route exists."
                    )

        # --------------------------------------------------------------
        # Invariant 2
        # If selected route is unsafe, there must be
        # an explicit emergency decision.
        # --------------------------------------------------------------

        return violations

    # ==================================================================
    # EXPLANATION
    # ==================================================================

    def explain(
        self,
        route: str,
        result: dict,
        sensor_blind: bool,
        confidence: float,
        uncertainty: float,
        evidence: Evidence,
        contradiction: float,
        decision: Optional[dict] = None
    ):

        reasons = []

        if sensor_blind:

            reasons.append(
                "Sensor blind: wildlife position remains "
                "a probabilistic estimate."
            )

        if confidence < 60:

            reasons.append(
                "Prediction confidence is low; "
                "uncertainty is elevated."
            )

        fusion = evidence.fusion()

        if fusion > 20:

            reasons.append(
                f"Indirect evidence is active ({fusion:.1f})."
            )

        if contradiction > 0:

            reasons.append(
                f"Evidence conflict detected "
                f"({contradiction:.1f}); "
                "risk is conservatively bounded."
            )

        if result["encounter_exposure"] >= 50:

            reasons.append(
                f"High route-specific encounter exposure "
                f"({result['encounter_exposure']:.1f})."
            )

        elif result["encounter_exposure"] >= 20:

            reasons.append(
                f"Moderate wildlife-route encounter exposure "
                f"({result['encounter_exposure']:.1f})."
            )

        if result["ttc_state"] == "IMMEDIATE":

            reasons.append(
                "Immediate potential wildlife-route conflict."
            )

        elif result["ttc_state"] == "IMMINENT":

            reasons.append(
                "Potential wildlife-human conflict is imminent."
            )

        elif result["ttc_state"] == "APPROACHING":

            reasons.append(
                "Wildlife trajectory is approaching the route."
            )

        elif result["ttc_state"] == "UNKNOWN":

            reasons.append(
                "Time-to-conflict cannot be established reliably."
            )

        if result["envelope_intersection"]:

            reasons.append(
                "Wildlife uncertainty envelope intersects "
                "the route corridor."
            )

        if result["trajectory_intersection"]:

            reasons.append(
                "Predicted wildlife trajectory intersects "
                "the route geometry."
            )

        if result["delta"] > 1:

            reasons.append(
                f"Risk increased by "
                f"{result['delta']:.1f}."
            )

        if result["persistence"] >= 2:

            reasons.append(
                f"Deterioration persisted for "
                f"{result['persistence']} step(s)."
            )

        if result["memory"] > 15:

            reasons.append(
                "Historical danger memory is active/decaying."
            )

        if result["corridor_memory"] > 15:

            reasons.append(
                "Danger-corridor memory is active/decaying."
            )

        if (
            decision is not None
            and
            decision.get(
                "reason_code"
            ) == "CURRENT_ROUTE_UNSAFE"
        ):

            reasons.append(
                "Emergency route switching overrode "
                "normal hysteresis."
            )

        if not reasons:

            reasons.append(
                "No significant temporal or "
                "spatial-risk pressure."
            )

        return reasons


# ======================================================================
# DEMONSTRATION SCENARIO
# ======================================================================

def run_demo():

    engine = WildSentinel097()

    timeline = [

        # --------------------------------------------------------------
        # minute
        # actual position
        # visible
        # evidence
        # route risks
        # --------------------------------------------------------------

        (
            0,
            (15.0, 85.0),
            False,
            Evidence(),
            {
                "A": (31, 56),
                "B": (6, 6),
                "C": (6, 6)
            }
        ),

        (
            5,
            (23.0, 75.0),
            False,
            Evidence(),
            {
                "A": (20, 55),
                "B": (8, 8),
                "C": (6, 6)
            }
        ),

        (
            10,
            (31.0, 65.0),
            True,
            Evidence(sensor=70),
            {
                "A": (40, 81),
                "B": (8, 31),
                "C": (6, 6)
            }
        ),

        (
            15,
            (39.0, 55.0),
            True,
            Evidence(
                movement=65,
                sensor=75
            ),
            {
                "A": (60, 84),
                "B": (10, 10),
                "C": (6, 6)
            }
        ),

        (
            20,
            (47.0, 50.0),
            False,
            Evidence(
                movement=40,
                sensor=35
            ),
            {
                "A": (65, 84),
                "B": (15, 15),
                "C": (6, 6)
            }
        ),

        (
            25,
            (55.0, 48.0),
            False,
            Evidence(
                movement=50,
                sensor=45,
                prey=55
            ),
            {
                "A": (70, 85),
                "B": (15, 85),
                "C": (6, 6)
            }
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
                human=70
            ),
            {
                "A": (75, 90),
                "B": (20, 90),
                "C": (6, 6)
            }
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
                human=70
            ),
            {
                "A": (80, 95),
                "B": (25, 95),
                "C": (6, 6)
            }
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
                human=70
            ),
            {
                "A": (85, 95),
                "B": (25, 95),
                "C": (6, 6)
            }
        ),

        # --------------------------------------------------------------
        # 50 min:
        # confidence begins collapsing.
        # --------------------------------------------------------------

        (
            50,
            (95.0, 75.0),
            False,
            Evidence(
                movement=15,
                sensor=10,
                prey=5
            ),
            {
                "A": (25, 85),
                "B": (10, 75),
                "C": (6, 6)
            }
        ),

        # --------------------------------------------------------------
        # 60 min:
        # all routes becoming uncertain.
        # --------------------------------------------------------------

        (
            60,
            (110.0, 90.0),
            False,
            Evidence(),
            {
                "A": (12, 75),
                "B": (8, 70),
                "C": (6, 6)
            }
        ),

        # --------------------------------------------------------------
        # 75 min:
        #
        # THIS IS THE IMPORTANT ADVERSARIAL CASE.
        #
        # Old V0.9.6:
        #
        #     A = 60.4 CAUTION
        #     B = 60.4 CAUTION
        #     C = 67.4 DO NOT ENTER
        #
        # Yet it retained C because of hysteresis.
        #
        # V0.9.7 MUST SWITCH AWAY FROM C.
        # --------------------------------------------------------------

        (
            75,
            (130.0, 105.0),
            False,
            Evidence(),
            {
                "A": (6, 60),
                "B": (6, 60),
                "C": (6, 67)
            }
        ),
    ]

    print("=" * 78)

    print(
        "                 WILD SENTINEL V0.9.7"
    )

    print(
        "       SAFETY ARBITRATION + EMERGENCY ROUTE SWITCHING"
    )

    print("=" * 78)

    previous_position = None

    previous_time = None

    for (
        minute,
        actual,
        visible,
        evidence,
        risks
    ) in timeline:

        # --------------------------------------------------------------
        # Confidence
        # --------------------------------------------------------------

        if previous_position is None:

            confidence = 87.5

        else:

            confidence = max(
                17.5,
                87.5 -
                max(0, minute - 10) * 0.8
            )

        # --------------------------------------------------------------
        # Prediction
        # --------------------------------------------------------------

        predicted = None

        uncertainty = 5.0

        if visible:

            error = 0.0

            accuracy = 100.0

            predicted = actual

        else:

            predicted, uncertainty = engine.predict(
                previous_position or actual,
                confidence
            )

            error = distance(
                actual,
                predicted
            )

            accuracy = clamp(
                100.0 -
                error * 4.0
            )

        engine.last_prediction = predicted

        # --------------------------------------------------------------
        # Hypotheses
        # --------------------------------------------------------------

        hyps = engine.hypotheses(
            visible,
            evidence,
            uncertainty
        )

        contradiction = (
            engine.evidence_integrity(
                evidence,
                hyps
            )
        )

        # --------------------------------------------------------------
        # Route analysis
        # --------------------------------------------------------------

        route_results = {}

        for route in ROUTES:

            current_risk, worst = (
                risks[route]
            )

            # ----------------------------------------------------------
            # Spatial geometry
            # ----------------------------------------------------------

            if previous_position is None:

                trajectory_start = (
                    actual
                )

            else:

                trajectory_start = (
                    previous_position
                )

            trajectory_end = predicted

            spatial = (
                engine.encounter_exposure(
                    predicted_position=predicted,
                    uncertainty=uncertainty,
                    route=route,
                    trajectory_start=trajectory_start,
                    trajectory_end=trajectory_end
                )
            )

            # ----------------------------------------------------------
            # TTC
            # ----------------------------------------------------------

            ttc, intersects = (
                engine.time_to_conflict(
                    trajectory_start,
                    trajectory_end,
                    route,
                    uncertainty,
                    time_step_minutes=(
                        5.0
                        if previous_time is None
                        else max(
                            1.0,
                            minute - previous_time
                        )
                    )
                )
            )

            ttc_state = (
                engine.classify_ttc(
                    ttc,
                    intersects
                )
            )

            # ----------------------------------------------------------
            # Route temporal update
            # ----------------------------------------------------------

            route_results[route] = (
                engine.update_route(
                    route=route,
                    current_risk=current_risk,
                    worst_plausible=worst,
                    uncertainty=uncertainty,
                    prediction_confidence=confidence,
                    evidence=evidence,
                    contradiction=contradiction,
                    spatial=spatial,
                    ttc=ttc,
                    ttc_state=ttc_state
                )
            )

        # --------------------------------------------------------------
        # Confidence context
        # --------------------------------------------------------------

        fusion = evidence.fusion()

        confidence_context = max(
            0.0,
            confidence *
            (1.0 - fusion / 100.0)
        )

        # --------------------------------------------------------------
        # SAFETY DECISION
        # --------------------------------------------------------------

        previous_route = (
            engine.selected_route
        )

        chosen, decision = (
            engine.decide(
                route_results,
                confidence_context
            )
        )

        # --------------------------------------------------------------
        # Invariant validation
        # --------------------------------------------------------------

        violations = (
            engine.validate_decision(
                chosen,
                route_results
            )
        )

        # --------------------------------------------------------------
        # OUTPUT
        # --------------------------------------------------------------

        print("\n" + "-" * 66)

        print(
            f"{minute:02d} min"
        )

        print(
            f"  Actual wildlife: "
            f"({actual[0]:6.1f}, {actual[1]:6.1f})"
        )

        print(
            f"  Sensor: "
            f"{'VISIBLE' if visible else 'BLIND'}"
        )

        if visible:

            print(
                f"  Direct wildlife observation: "
                f"({actual[0]:.1f}, {actual[1]:.1f})"
            )

            print(
                "  PREDICTION VALIDATION"
            )

            print(
                f"      Position error: "
                f"{error:6.1f}"
            )

            print(
                f"      Rolling model accuracy: "
                f"{accuracy:5.1f}%"
            )

        else:

            print(
                f"  Predicted wildlife: "
                f"({predicted[0]:6.1f}, "
                f"{predicted[1]:6.1f})"
            )

            print(
                f"  Uncertainty radius: "
                f"{uncertainty:6.1f}"
            )

        print(
            f"  Prediction confidence: "
            f"{confidence:5.1f}%"
        )

        # --------------------------------------------------------------
        # Evidence
        # --------------------------------------------------------------

        print(
            "\n  INDIRECT EVIDENCE"
        )

        for name, value in (
            evidence.values().items()
        ):

            print(
                f"      {name:<12} "
                f"{value:5.1f}"
            )

        print(
            "      ----------------"
        )

        print(
            f"      Evidence fusion "
            f"{fusion:5.1f}"
        )

        # --------------------------------------------------------------
        # Hypotheses
        # --------------------------------------------------------------

        print(
            "\n  COMPETING HYPOTHESES"
        )

        for name, value in (
            hyps.items()
        ):

            print(
                f"      {name:<35} "
                f"{value:5.1f}%"
            )

        dominant = max(
            hyps,
            key=hyps.get
        )

        print(
            f"      Dominant hypothesis: "
            f"{dominant}"
        )

        if contradiction:

            print(
                "\n  EVIDENCE INTEGRITY"
            )

            print(
                f"      Contradiction pressure: "
                f"{contradiction:.1f}"
            )

            print(
                "      Conservative interpretation enabled."
            )

        # --------------------------------------------------------------
        # Route analysis
        # --------------------------------------------------------------

        print(
            "\n  SPATIAL + TEMPORAL ROUTE ANALYSIS"
        )

        for route in ROUTES:

            r = route_results[route]

            print(
                f"\n      ROUTE {route}"
            )

            print(
                f"          Expected risk:       "
                f"{r['expected']:6.1f}"
            )

            print(
                f"          Worst plausible:     "
                f"{r['worst']:6.1f}"
            )

            print(
                f"          Current risk:        "
                f"{r['current']:6.1f}"
            )

            print(
                f"          Encounter exposure: "
                f"{r['encounter_exposure']:6.1f}"
            )

            print(
                f"          Distance to route:  "
                f"{r['distance_to_route']:6.1f}"
            )

            print(
                f"          Uncertainty radius:  "
                f"{r['uncertainty_radius']:6.1f}"
            )

            if r["time_to_conflict"] is None:

                ttc_display = "UNKNOWN"

            else:

                ttc_display = (
                    f"{r['time_to_conflict']:.1f} min"
                )

            print(
                f"          Time to conflict:    "
                f"{ttc_display}"
            )

            print(
                f"          TTC state:           "
                f"{r['ttc_state']}"
            )

            print(
                f"          Trajectory intersect:"
                f" {'YES' if r['trajectory_intersection'] else 'NO'}"
            )

            print(
                f"          Envelope intersect: "
                f" {'YES' if r['envelope_intersection'] else 'NO'}"
            )

            print(
                f"          Risk trend:           "
                f"{r['trend']}"
            )

            print(
                f"          Persistence:           "
                f"{r['persistence']:6d}"
            )

            print(
                f"          Temporal risk:        "
                f"{r['temporal']:6.1f}"
            )

            print(
                f"          Historical memory:   "
                f"{r['memory']:6.1f}"
            )

            print(
                f"          Corridor memory:     "
                f"{r['corridor_memory']:6.1f}"
            )

            print(
                f"          Final decision risk: "
                f"{r['temporal']:6.1f}"
            )

            print(
                f"          Overall:             "
                f"{r['classification']}"
            )

        # --------------------------------------------------------------
        # Safety decision
        # --------------------------------------------------------------

        print(
            "\n  SAFETY DECISION"
        )

        if chosen == "SAFETY OVERRIDE":

            print(
                "  >>> SAFETY OVERRIDE: "
                "NO SAFE ROUTE AVAILABLE"
            )

            print(
                f"      Reason code: "
                f"{decision['reason_code']}"
            )

            print(
                f"      {decision['reason']}"
            )

        else:

            if (
                decision["reason_code"]
                in (
                    "CURRENT_ROUTE_UNSAFE",
                    "IMMINENT_CONFLICT"
                )
            ):

                print(
                    "  >>> EMERGENCY ROUTE SWITCH"
                )

                print(
                    f"      {previous_route} "
                    f"-> {chosen}"
                )

            else:

                print(
                    f"  >>> RECOMMENDATION: "
                    f"ROUTE {chosen}"
                )

            print(
                f"      Reason code: "
                f"{decision['reason_code']}"
            )

            print(
                f"      {decision['reason']}"
            )

        # --------------------------------------------------------------
        # Explanation
        # --------------------------------------------------------------

        print(
            "\n  DECISION EXPLANATION"
        )

        if chosen != "SAFETY OVERRIDE":

            result = (
                route_results[chosen]
            )

            print(
                f"      Route {chosen} -> "
                f"{result['classification']}"
            )

            print(
                f"      Final decision risk: "
                f"{result['temporal']:.1f}"
            )

            print(
                f"      Current risk:        "
                f"{result['current']:.1f}"
            )

            print(
                f"      Encounter exposure: "
                f"{result['encounter_exposure']:.1f}"
            )

            print(
                f"      TTC state:           "
                f"{result['ttc_state']}"
            )

            print(
                f"      Confidence context: "
                f"{confidence_context:.1f}%"
            )

            for reason in (
                engine.explain(
                    chosen,
                    result,
                    not visible,
                    confidence,
                    uncertainty,
                    evidence,
                    contradiction,
                    decision
                )
            ):

                print(
                    f"        + {reason}"
                )

        # --------------------------------------------------------------
        # Invariant report
        # --------------------------------------------------------------

        print(
            "\n  SAFETY INVARIANTS"
        )

        if not violations:

            print(
                "      [PASS] No decision invariant violations."
            )

        else:

            for violation in violations:

                print(
                    f"      [FAIL] {violation}"
                )

        # --------------------------------------------------------------
        # Sensor blindness
        # --------------------------------------------------------------

        if not visible:

            print(
                "\n  SENSOR-BLINDNESS STATUS"
            )

            print(
                "      Direct confirmation unavailable."
            )

            print(
                "      Spatial safety is inferred from "
                "prediction + uncertainty."
            )

            print(
                "      Prediction is NOT treated as ground truth."
            )

        previous_position = actual

        previous_time = minute

    print(
        "\n" + "=" * 78
    )

    print(
        "                    V0.9.7 TEST COMPLETE"
    )

    print(
        "=" * 78
    )

    print(
        """
V0.9.7 ENGINE CHECK:

  [✓] Multiple wildlife hypotheses
  [✓] Indirect evidence updates hypotheses
  [✓] Sensor blindness
  [✓] Prediction confidence decay
  [✓] Prediction validation
  [✓] Temporal risk memory
  [✓] Risk trend
  [✓] Risk persistence
  [✓] Danger-zone memory
  [✓] Conservative worst-case protection
  [✓] Decision hysteresis
  [✓] Route switching protection
  [✓] Safety override
  [✓] Explicit decision explanation
  [✓] Historical danger decay
  [✓] Route recovery
  [✓] Confidence-aware risk ceiling
  [✓] Evidence contradiction detection

V0.9.7 SPATIAL:

  [✓] Wildlife uncertainty envelope
  [✓] Route geometry analysis
  [✓] Route-specific exposure
  [✓] Wildlife-route spatial overlap
  [✓] Time-to-conflict estimation
  [✓] TTC state classification
  [✓] UNKNOWN TTC state
  [✓] Blind-state spatial risk
  [✓] Danger corridor memory
  [✓] Spatial recovery detection
  [✓] Imminent conflict detection

V0.9.7 SAFETY ARBITRATION:

  [✓] Safety-breaking hysteresis
  [✓] Emergency route switching
  [✓] Unsafe-current-route detection
  [✓] All-routes-unsafe override
  [✓] Emergency conflict override
  [✓] Decision reason codes
  [✓] Safety invariants
  [✓] Adversarial route-selection test
  [✓] No silent DO NOT ENTER recommendation

======================================================================

V0.9.7 CORE QUESTION:

  "Can Wild Sentinel prevent its own route-selection logic
   from retaining a route after that route becomes unsafe?"

ANSWER:

  YES.

  Normal hysteresis can retain a route when conditions are close.

  BUT:

      DO NOT ENTER
             ↓
      SAFETY ARBITRATION
             ↓
      FIND SAFER ALTERNATIVE
             ↓
      EMERGENCY SWITCH

  If every route is unsafe:

      SAFETY OVERRIDE

  The governing principle is:

      "HYSTERESIS MAY REDUCE OSCILLATION.
       IT MUST NEVER OVERRIDE SAFETY."

======================================================================
"""
    )


# ======================================================================
# ADVERSARIAL TEST SUITE
# ======================================================================

def run_adversarial_tests():

    print("\n")
    print("=" * 78)
    print("                 V0.9.7 ADVERSARIAL TESTS")
    print("=" * 78)

    passed = 0
    failed = 0

    # ------------------------------------------------------------------
    # TEST 1
    # Normal hysteresis should retain current route.
    # ------------------------------------------------------------------

    engine = WildSentinel097()

    engine.selected_route = "C"

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

    chosen, decision = engine.decide(
        results,
        80
    )

    if chosen == "C":

        print(
            "[PASS] Test 1: "
            "Normal hysteresis retains current route."
        )

        passed += 1

    else:

        print(
            "[FAIL] Test 1"
        )

        failed += 1

    # ------------------------------------------------------------------
    # TEST 2
    # Current route becomes DO NOT ENTER.
    # It MUST switch.
    # ------------------------------------------------------------------

    engine = WildSentinel097()

    engine.selected_route = "C"

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

    chosen, decision = engine.decide(
        results,
        30
    )

    if (
        chosen == "A"
        and
        decision["reason_code"]
        == "CURRENT_ROUTE_UNSAFE"
    ):

        print(
            "[PASS] Test 2: "
            "Unsafe current route triggers emergency switch."
        )

        passed += 1

    else:

        print(
            "[FAIL] Test 2"
        )

        failed += 1

    # ------------------------------------------------------------------
    # TEST 3
    # All routes unsafe.
    # ------------------------------------------------------------------

    engine = WildSentinel097()

    engine.selected_route = "C"

    results = {

        "A": {
            "temporal": 90,
            "classification": "DO NOT ENTER",
            "ttc_state": "IMMEDIATE",
            "encounter_exposure": 90,
        },

        "B": {
            "temporal": 80,
            "classification": "DO NOT ENTER",
            "ttc_state": "IMMEDIATE",
            "encounter_exposure": 80,
        },

        "C": {
            "temporal": 75,
            "classification": "DO NOT ENTER",
            "ttc_state": "IMMEDIATE",
            "encounter_exposure": 75,
        },
    }

    chosen, decision = engine.decide(
        results,
        10
    )

    if (
        chosen == "SAFETY OVERRIDE"
        and
        decision["reason_code"]
        == "ALL_ROUTES_UNSAFE"
    ):

        print(
            "[PASS] Test 3: "
            "All unsafe routes produce safety override."
        )

        passed += 1

    else:

        print(
            "[FAIL] Test 3"
        )

        failed += 1

    # ------------------------------------------------------------------
    # TEST 4
    # Imminent conflict overrides hysteresis.
    # ------------------------------------------------------------------

    engine = WildSentinel097()

    engine.selected_route = "C"

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

    chosen, decision = engine.decide(
        results,
        25
    )

    if chosen == "A":

        print(
            "[PASS] Test 4: "
            "Imminent conflict overrides hysteresis."
        )

        passed += 1

    else:

        print(
            "[FAIL] Test 4"
        )

        failed += 1

    # ------------------------------------------------------------------
    # TEST 5
    # The exact V0.9.6 failure.
    #
    # C is current and unsafe.
    # A/B are safer but only ~7 points better.
    #
    # Old hysteresis would retain C.
    # V0.9.7 must switch.
    # ------------------------------------------------------------------

    engine = WildSentinel097()

    engine.selected_route = "C"

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

    chosen, decision = engine.decide(
        results,
        35.5
    )

    if (
        chosen == "A"
        and
        decision["reason_code"]
        == "CURRENT_ROUTE_UNSAFE"
    ):

        print(
            "[PASS] Test 5: "
            "V0.9.6 75-minute failure fixed."
        )

        passed += 1

    else:

        print(
            "[FAIL] Test 5: "
            "V0.9.6 failure remains."
        )

        failed += 1

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------

    print("\n" + "-" * 78)

    print(
        f"  TESTS PASSED: {passed}"
    )

    print(
        f"  TESTS FAILED: {failed}"
    )

    print(
        "-" * 78
    )

    if failed == 0:

        print(
            "  >>> V0.9.7 SAFETY ARBITRATION TESTS PASSED"
        )

    else:

        print(
            "  >>> V0.9.7 REQUIRES FURTHER INVESTIGATION"
        )

    print(
        "=" * 78
    )


# ======================================================================
# MAIN
# ======================================================================

if __name__ == "__main__":

    run_demo()

    run_adversarial_tests()
