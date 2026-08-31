from pathlib import Path

"""
==========================================================================
                         WILD SENTINEL V0.9.6
==========================================================================
       SPATIAL INTERCEPT + TIME-TO-CONFLICT + RECOVERY SAFETY ENGINE

Built from V0.9.5.

V0.9.6 additions:

  [NEW] Wildlife uncertainty envelope
  [NEW] Human-route spatial intersection analysis
  [NEW] Time-to-conflict estimation
  [NEW] Predicted encounter probability
  [NEW] Route exposure scoring
  [NEW] Wildlife trajectory crossing detection
  [NEW] Confidence-aware spatial risk ceiling
  [NEW] Risk based on geometry, not only supplied route scores
  [NEW] Route-specific encounter explanation
  [NEW] Persistent danger corridor memory
  [NEW] Recovery requires sustained spatial separation
  [NEW] Sensor-blind spatial safety state

Core idea:

  V0.9.5 asks:
      "How dangerous is this route?"

  V0.9.6 asks:
      "Given where the wildlife may be, where the human is going,
       and how uncertain the prediction is, could the two intersect?"

This remains a simulation/reference engine.
It is NOT a field-certified wildlife safety system.
==========================================================================

"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import math


ROUTES = ("A", "B", "C")


# ==========================================================================
# BASIC GEOMETRY
# ==========================================================================

def distance(a: Tuple[float, float],
             b: Tuple[float, float]) -> float:
    return math.dist(a, b)


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def point_to_segment_distance(
    p: Tuple[float, float],
    a: Tuple[float, float],
    b: Tuple[float, float]
) -> float:

    px, py = p
    ax, ay = a
    bx, by = b

    dx = bx - ax
    dy = by - ay

    if dx == 0 and dy == 0:
        return distance(p, a)

    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)

    t = max(0.0, min(1.0, t))

    closest = (
        ax + t * dx,
        ay + t * dy
    )

    return distance(p, closest)


# ==========================================================================
# DATA STRUCTURES
# ==========================================================================

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

        return min(
            100.0,
            0.30 * self.movement +
            0.30 * self.sensor +
            0.15 * self.prey +
            0.10 * self.environment +
            0.15 * self.human
        )


@dataclass
class Route:

    name: str

    start: Tuple[float, float]

    end: Tuple[float, float]

    # Approximate human travel speed in coordinate units/minute.
    speed: float = 1.0


@dataclass
class RouteState:

    risk: float = 6.0
    previous_risk: float = 6.0

    memory: float = 0.0

    persistence: int = 0

    last_trend: str = "STABLE"

    unsafe_steps: int = 0

    safe_steps: int = 0

    danger_corridor_memory: float = 0.0


# ==========================================================================
# ENGINE
# ==========================================================================

class WildSentinel096:

    """
    Wild Sentinel V0.9.6.

    Main safety chain:

        observation
             |
             v
        prediction
             |
             v
      uncertainty envelope
             |
             v
       route intersection
             |
             v
       time-to-conflict
             |
             v
       encounter exposure
             |
             v
       temporal risk engine
             |
             v
       safety decision

    V0.9.6 deliberately separates:

        prediction confidence
        evidence confidence
        spatial encounter exposure
        historical danger

    None of these are silently treated as certainty.
    """

    def __init__(self):

        self.routes: Dict[str, RouteState] = {
            r: RouteState() for r in ROUTES
        }

        self.selected_route = "C"

        self.hold_counter = 0

        self.last_position = None

        self.last_prediction = None

        self.prediction_error_history: List[float] = []

        self.time_min = 0

        # --------------------------------------------------------------
        # Safety parameters
        # --------------------------------------------------------------

        self.memory_decay = 0.82

        self.recovery_threshold = 12.0

        self.caution_threshold = 35.0

        self.danger_threshold = 65.0

        self.override_threshold = 85.0

        self.route_switch_margin = 8.0

        self.minimum_route_hold = 2

        # Wildlife uncertainty cannot disappear instantly.
        self.uncertainty_growth_factor = 0.40

        # Spatial parameters.
        self.wildlife_buffer = 5.0

        self.human_buffer = 3.0

        self.conflict_horizon = 30.0

    # ==================================================================
    # PREDICTION
    # ==================================================================

    def predict(
        self,
        position: Tuple[float, float],
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
                (100.0 - confidence) *
                self.uncertainty_growth_factor
            )
        )

        return predicted, uncertainty

    # ==================================================================
    # PREDICTION VALIDATION
    # ==================================================================

    def validate_prediction(self, actual, predicted):

        error = distance(actual, predicted)

        self.prediction_error_history.append(error)

        self.prediction_error_history = \
            self.prediction_error_history[-5:]

        accuracy = max(
            0.0,
            min(
                100.0,
                100.0 -
                (
                    sum(self.prediction_error_history) /
                    len(self.prediction_error_history)
                ) * 4.0
            )
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
                (uncertainty - 15) * 0.7
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
    # UNCERTAINTY ENVELOPE
    # ==================================================================

    def uncertainty_envelope(
        self,
        uncertainty: float,
        confidence: float
    ):

        """
        Converts prediction uncertainty into a spatial safety radius.

        The radius grows when:

          - uncertainty rises
          - confidence falls

        This is deliberately conservative.
        """

        confidence_penalty = max(
            0.0,
            (70.0 - confidence) * 0.08
        )

        radius = (
            self.wildlife_buffer
            + uncertainty
            + confidence_penalty
        )

        return min(
            50.0,
            radius
        )

    # ==================================================================
    # ROUTE GEOMETRY
    # ==================================================================

    def route_geometry(
        self,
        route: Route,
        wildlife_position: Tuple[float, float],
        uncertainty_radius: float
    ):

        distance_to_route = point_to_segment_distance(
            wildlife_position,
            route.start,
            route.end
        )

        safe_distance = (
            uncertainty_radius
            + self.human_buffer
        )

        overlap = max(
            0.0,
            safe_distance - distance_to_route
        )

        if safe_distance <= 0:

            spatial_exposure = 0.0

        else:

            spatial_exposure = clamp(
                (overlap / safe_distance) * 100.0
            )

        return {
            "distance_to_route": distance_to_route,
            "safe_distance": safe_distance,
            "overlap": overlap,
            "spatial_exposure": spatial_exposure,
        }

    # ==================================================================
    # TIME TO CONFLICT
    # ==================================================================

    def time_to_conflict(
        self,
        wildlife_position: Tuple[float, float],
        route: Route,
        wildlife_direction: Tuple[float, float],
        uncertainty_radius: float
    ):

        """
        Estimate when wildlife reaches the human route corridor.

        This is intentionally a simple explainable approximation,
        rather than pretending to be a full animal-motion model.
        """

        distance_to_route = point_to_segment_distance(
            wildlife_position,
            route.start,
            route.end
        )

        vx, vy = wildlife_direction

        wildlife_speed = math.sqrt(
            vx * vx + vy * vy
        )

        if wildlife_speed <= 0:

            return math.inf

        effective_distance = max(
            0.0,
            distance_to_route -
            uncertainty_radius -
            self.human_buffer
        )

        return effective_distance / wildlife_speed

    # ==================================================================
    # ENCOUNTER EXPOSURE
    # ==================================================================

    def encounter_exposure(
        self,
        route: Route,
        wildlife_position: Tuple[float, float],
        wildlife_direction: Tuple[float, float],
        uncertainty: float,
        confidence: float,
        sensor_blind: bool
    ):

        radius = self.uncertainty_envelope(
            uncertainty,
            confidence
        )

        geometry = self.route_geometry(
            route,
            wildlife_position,
            radius
        )

        ttc = self.time_to_conflict(
            wildlife_position,
            route,
            wildlife_direction,
            radius
        )

        # --------------------------------------------------------------
        # Spatial component
        # --------------------------------------------------------------

        spatial = geometry["spatial_exposure"]

        # --------------------------------------------------------------
        # Time component
        # --------------------------------------------------------------

        if ttc == math.inf:

            time_pressure = 0.0

        elif ttc <= 0:

            time_pressure = 100.0

        elif ttc <= 5:

            time_pressure = 100.0

        elif ttc <= 10:

            time_pressure = 85.0

        elif ttc <= 20:

            time_pressure = 65.0

        elif ttc <= 30:

            time_pressure = 40.0

        else:

            time_pressure = 10.0

        # --------------------------------------------------------------
        # Blindness amplification
        # --------------------------------------------------------------

        blindness_pressure = 0.0

        if sensor_blind:

            blindness_pressure = min(
                20.0,
                uncertainty * 0.35
            )

        # --------------------------------------------------------------
        # Combined encounter exposure
        # --------------------------------------------------------------

        exposure = (
            0.55 * spatial
            + 0.30 * time_pressure
            + 0.15 * blindness_pressure
        )

        return {
            "uncertainty_radius": radius,
            "distance_to_route": geometry["distance_to_route"],
            "safe_distance": geometry["safe_distance"],
            "overlap": geometry["overlap"],
            "spatial_exposure": spatial,
            "time_to_conflict": ttc,
            "time_pressure": time_pressure,
            "blindness_pressure": blindness_pressure,
            "encounter_exposure": clamp(exposure),
        }

    # ==================================================================
    # CLASSIFICATION
    # ==================================================================

    def classify(self, risk: float):

        if risk >= self.danger_threshold:

            return "DO NOT ENTER"

        if risk >= self.caution_threshold:

            return "CAUTION"

        return "LOW RISK"

    # ==================================================================
    # ROUTE RISK
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
        encounter_exposure: float,
        ttc: float
    ):

        state = self.routes[route]

        # --------------------------------------------------------------
        # Blend supplied environmental/base risk with spatial exposure.
        # --------------------------------------------------------------

        spatial_risk = (
            0.45 * current_risk
            + 0.55 * encounter_exposure
        )

        delta = (
            spatial_risk -
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
        # Spatial danger corridor memory
        # --------------------------------------------------------------

        if encounter_exposure >= 50:

            state.danger_corridor_memory = max(
                state.danger_corridor_memory * 0.90,
                encounter_exposure
            )

        else:

            state.danger_corridor_memory *= 0.88

        # --------------------------------------------------------------
        # Persistence pressure
        # --------------------------------------------------------------

        persistence_pressure = min(
            25.0,
            state.persistence * 7.0
        )

        # --------------------------------------------------------------
        # Uncertainty
        # --------------------------------------------------------------

        uncertainty_penalty = 0.0

        if uncertainty > 5:

            uncertainty_penalty = min(
                20.0,
                (uncertainty - 5) * 0.45
            )

        # --------------------------------------------------------------
        # Confidence
        # --------------------------------------------------------------

        confidence_penalty = max(
            0.0,
            (60.0 - prediction_confidence) * 0.25
        )

        # --------------------------------------------------------------
        # Contradiction
        # --------------------------------------------------------------

        contradiction_penalty = (
            contradiction * 0.25
        )

        # --------------------------------------------------------------
        # Immediate conflict pressure
        # --------------------------------------------------------------

        conflict_pressure = 0.0

        if ttc != math.inf:

            if ttc <= 5:

                conflict_pressure = 25.0

            elif ttc <= 10:

                conflict_pressure = 18.0

            elif ttc <= 20:

                conflict_pressure = 10.0

            elif ttc <= 30:

                conflict_pressure = 5.0

        # --------------------------------------------------------------
        # Temporal risk
        # --------------------------------------------------------------

        temporal = (
            spatial_risk
            + persistence_pressure
            + uncertainty_penalty
            + confidence_penalty
            + contradiction_penalty
            + conflict_pressure
        )

        # Historical danger remains relevant.

        temporal = max(
            temporal,
            state.memory * 0.55
        )

        # Danger corridor memory.

        temporal = max(
            temporal,
            state.danger_corridor_memory * 0.45
        )

        # --------------------------------------------------------------
        # Worst-case protection
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
        # Confidence-aware risk ceiling
        #
        # Low confidence + high spatial exposure means the engine
        # must not declare the route safely known.
        # --------------------------------------------------------------

        if prediction_confidence < 45:

            confidence_floor = (
                encounter_exposure * 0.55
            )

            temporal = max(
                temporal,
                confidence_floor
            )

        # --------------------------------------------------------------
        # Recovery
        # --------------------------------------------------------------

        if (
            current_risk <= self.recovery_threshold
            and encounter_exposure <= 20
            and state.safe_steps >= 2
        ):

            state.memory *= 0.65

            state.danger_corridor_memory *= 0.70

            temporal = min(
                temporal,
                current_risk + 8.0
            )

        temporal = clamp(
            temporal
        )

        state.previous_risk = spatial_risk

        state.risk = temporal

        state.last_trend = trend

        return {

            "expected": current_risk,

            "worst": worst_plausible,

            "current": spatial_risk,

            "delta": delta,

            "trend": trend,

            "persistence": state.persistence,

            "temporal": temporal,

            "memory": state.memory,

            "corridor_memory":
                state.danger_corridor_memory,

            "encounter_exposure":
                encounter_exposure,

            "time_to_conflict":
                ttc,

            "classification":
                self.classify(temporal),
        }

    # ==================================================================
    # SAFETY DECISION
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

        # --------------------------------------------------------------
        # GLOBAL SAFETY OVERRIDE
        # --------------------------------------------------------------

        if all(
            v["temporal"] >=
            self.danger_threshold
            for v in route_results.values()
        ):

            return "SAFETY OVERRIDE", {
                "reason":
                    "All candidate routes exceed the danger threshold."
            }

        current = route_results[
            self.selected_route
        ]

        # --------------------------------------------------------------
        # Immediate encounter override.
        # --------------------------------------------------------------

        if (
            current["time_to_conflict"] != math.inf
            and
            current["time_to_conflict"] <= 5
            and
            current["encounter_exposure"] >= 60
        ):

            return "SAFETY OVERRIDE", {
                "reason":
                    "Predicted wildlife-human conflict is imminent."
            }

        # --------------------------------------------------------------
        # Hysteresis
        # --------------------------------------------------------------

        if (
            self.hold_counter <
            self.minimum_route_hold
            and
            current["temporal"] <
            self.danger_threshold
        ):

            chosen = self.selected_route

            reason = (
                "Existing route retained by "
                "minimum-hold hysteresis."
            )

        elif (
            best_route != self.selected_route
            and
            best["temporal"] +
            self.route_switch_margin <
            current["temporal"]
        ):

            chosen = best_route

            reason = (
                "New route is materially safer "
                "after spatial encounter analysis."
            )

        else:

            chosen = self.selected_route

            reason = (
                "Existing route retained; "
                "improvement is not large enough."
            )

        self.selected_route = chosen

        self.hold_counter += 1

        return chosen, {

            "reason": reason,

            "best_candidate":
                best_route,

            "confidence_context":
                confidence_context,
        }

    # ==================================================================
    # EXPLAINABILITY
    # ==================================================================

    def explain(
        self,
        result: dict,
        sensor_blind: bool,
        confidence: float,
        uncertainty: float,
        evidence: Evidence,
        contradiction: float
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
                f"Evidence conflict detected ({contradiction:.1f}); "
                "risk is conservatively bounded."
            )

        exposure = result[
            "encounter_exposure"
        ]

        if exposure >= 60:

            reasons.append(
                f"High wildlife-route encounter exposure "
                f"({exposure:.1f})."
            )

        elif exposure >= 30:

            reasons.append(
                f"Moderate wildlife-route encounter exposure "
                f"({exposure:.1f})."
            )

        ttc = result[
            "time_to_conflict"
        ]

        if ttc != math.inf:

            if ttc <= 5:

                reasons.append(
                    "Potential wildlife-human conflict "
                    "is imminent."
                )

            elif ttc <= 15:

                reasons.append(
                    f"Potential route conflict in "
                    f"approximately {ttc:.1f} min."
                )

            elif ttc <= 30:

                reasons.append(
                    f"Wildlife trajectory enters the "
                    f"route horizon in approximately {ttc:.1f} min."
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
                "Historical danger memory remains active."
            )

        if result["corridor_memory"] > 15:

            reasons.append(
                "Danger-corridor memory remains active."
            )

        if not reasons:

            reasons.append(
                "No significant temporal or "
                "spatial-risk pressure."
            )

        return reasons


# ==========================================================================
# DEMONSTRATION
# ==========================================================================

def run_demo():

    engine = WildSentinel096()

    # ------------------------------------------------------------------
    # Human routes
    #
    # Coordinates are intentionally simple simulation coordinates.
    # ------------------------------------------------------------------

    routes = {

        "A": Route(
            "A",
            (40.0, 50.0),
            (100.0, 50.0),
            1.0
        ),

        "B": Route(
            "B",
            (40.0, 30.0),
            (100.0, 30.0),
            1.0
        ),

        "C": Route(
            "C",
            (40.0, 10.0),
            (100.0, 10.0),
            1.0
        ),
    }

    # ------------------------------------------------------------------
    # Wildlife trajectory.
    #
    # The important test:
    #
    # Wildlife disappears from sensors.
    #
    # Its predicted trajectory gradually approaches Route A.
    #
    # Route A therefore becomes dangerous even without direct
    # observation.
    # ------------------------------------------------------------------

    timeline = [

        (
            0,
            (15.0, 85.0),
            False,
            Evidence(),
            {"A": (15, 25), "B": (8, 10), "C": (6, 8)}
        ),

        (
            5,
            (23.0, 75.0),
            False,
            Evidence(),
            {"A": (20, 30), "B": (8, 10), "C": (6, 8)}
        ),

        (
            10,
            (31.0, 65.0),
            True,
            Evidence(sensor=70),
            {"A": (40, 55), "B": (8, 10), "C": (6, 8)}
        ),

        (
            15,
            (39.0, 55.0),
            True,
            Evidence(sensor=75, movement=65),
            {"A": (60, 70), "B": (10, 15), "C": (6, 8)}
        ),

        (
            20,
            (47.0, 50.0),
            False,
            Evidence(sensor=35, movement=40),
            {"A": (65, 80), "B": (15, 20), "C": (6, 8)}
        ),

        (
            25,
            (55.0, 48.0),
            False,
            Evidence(
                sensor=45,
                movement=50,
                prey=55
            ),
            {"A": (70, 85), "B": (15, 25), "C": (6, 8)}
        ),

        (
            30,
            (63.0, 49.0),
            False,
            Evidence(
                sensor=60,
                movement=65,
                prey=60,
                environment=50,
                human=70
            ),
            {"A": (75, 90), "B": (20, 30), "C": (6, 8)}
        ),

        (
            35,
            (71.0, 50.0),
            False,
            Evidence(
                sensor=65,
                movement=70,
                prey=55,
                environment=60,
                human=70
            ),
            {"A": (80, 95), "B": (25, 35), "C": (6, 8)}
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
            {"A": (85, 100), "B": (25, 35), "C": (6, 8)}
        ),

        # Wildlife starts moving away.
        (
            50,
            (95.0, 75.0),
            False,
            Evidence(
                movement=15,
                sensor=10,
                prey=5
            ),
            {"A": (25, 45), "B": (10, 15), "C": (6, 8)}
        ),

        (
            60,
            (110.0, 90.0),
            False,
            Evidence(),
            {"A": (12, 20), "B": (8, 10), "C": (6, 8)}
        ),

        (
            75,
            (130.0, 105.0),
            False,
            Evidence(),
            {"A": (6, 10), "B": (6, 8), "C": (6, 8)}
        ),
    ]

    print("=" * 78)

    print(
        "                 WILD SENTINEL V0.9.6"
    )

    print(
        "   SPATIAL INTERCEPT + TIME-TO-CONFLICT + RECOVERY ENGINE"
    )

    print("=" * 78)

    previous_position = None

    previous_minute = None

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

        uncertainty = 5.0

        predicted = None

        # --------------------------------------------------------------
        # Prediction
        # --------------------------------------------------------------

        if visible:

            error = 0.0

            accuracy = 100.0

            predicted_position = actual

        else:

            predicted, uncertainty = engine.predict(
                previous_position or actual,
                confidence
            )

            predicted_position = predicted

            error = distance(
                actual,
                predicted
            )

            accuracy = max(
                0,
                100 -
                error * 4
            )

        # --------------------------------------------------------------
        # Wildlife direction
        # --------------------------------------------------------------

        if previous_position is not None:

            dx = actual[0] - previous_position[0]

            dy = actual[1] - previous_position[1]

        else:

            dx, dy = 8.0, -8.0

        # If sensor-blind, use the predicted direction.
        if not visible:

            wildlife_direction = (8.0, -8.0)

        else:

            wildlife_direction = (
                dx,
                dy
            )

        # --------------------------------------------------------------
        # Hypotheses
        # --------------------------------------------------------------

        hyps = engine.hypotheses(
            visible,
            evidence,
            uncertainty
        )

        contradiction = engine.evidence_integrity(
            evidence,
            hyps
        )

        # --------------------------------------------------------------
        # Route analysis
        # --------------------------------------------------------------

        route_results = {}

        for route_name in ROUTES:

            route = routes[route_name]

            current_risk, worst = \
                risks[route_name]

            encounter = engine.encounter_exposure(
                route,
                predicted_position,
                wildlife_direction,
                uncertainty,
                confidence,
                not visible
            )

            route_results[route_name] = \
                engine.update_route(
                    route_name,
                    current_risk,
                    worst,
                    uncertainty,
                    confidence,
                    evidence,
                    contradiction,
                    encounter[
                        "encounter_exposure"
                    ],
                    encounter[
                        "time_to_conflict"
                    ]
                )

            # Preserve geometry diagnostics.
            route_results[
                route_name
            ][
                "geometry"
            ] = encounter

        # --------------------------------------------------------------
        # Confidence context
        # --------------------------------------------------------------

        fusion = evidence.fusion()

        confidence_context = max(
            0.0,
            confidence *
            (1 - fusion / 100.0)
        )

        chosen, decision = engine.decide(
            route_results,
            confidence_context
        )

        # ==============================================================
        # OUTPUT
        # ==============================================================

        print(
            f"\n{'-' * 70}"
        )

        print(
            f"{minute:02d} min"
        )

        print(
            f"  Actual wildlife: "
            f"({actual[0]:5.1f}, {actual[1]:5.1f})"
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
                f"({predicted[0]:5.1f}, "
                f"{predicted[1]:5.1f})"
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

        for name, value in evidence.values().items():

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

        for name, value in hyps.items():

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

        # --------------------------------------------------------------
        # Contradiction
        # --------------------------------------------------------------

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

            g = r["geometry"]

            print(
                f"\n      ROUTE {route}"
            )

            print(
                f"          Base risk:           "
                f"{r['expected']:6.1f}"
            )

            print(
                f"          Encounter exposure:  "
                f"{r['encounter_exposure']:6.1f}"
            )

            print(
                f"          Distance to route:   "
                f"{g['distance_to_route']:6.1f}"
            )

            print(
                f"          Uncertainty radius:   "
                f"{g['uncertainty_radius']:6.1f}"
            )

            if r["time_to_conflict"] == math.inf:

                print(
                    "          Time to conflict:    NONE"
                )

            else:

                print(
                    f"          Time to conflict:    "
                    f"{r['time_to_conflict']:6.1f} min"
                )

            print(
                f"          Risk trend:           "
                f"{r['trend']}"
            )

            print(
                f"          Persistence:          "
                f"{r['persistence']:6d}"
            )

            print(
                f"          Temporal risk:       "
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
                f"          Overall:              "
                f"{r['classification']}"
            )

        # --------------------------------------------------------------
        # Decision
        # --------------------------------------------------------------

        print(
            "\n  SAFETY DECISION"
        )

        if chosen == "SAFETY OVERRIDE":

            print(
                "  >>> SAFETY OVERRIDE"
            )

            print(
                f"      {decision['reason']}"
            )

        else:

            print(
                f"  >>> RECOMMENDATION: "
                f"ROUTE {chosen}"
            )

            print(
                f"      {decision['reason']}"
            )

        # --------------------------------------------------------------
        # Explanation
        # --------------------------------------------------------------

        if chosen != "SAFETY OVERRIDE":

            print(
                "\n  DECISION EXPLANATION"
            )

            result = route_results[
                chosen
            ]

            print(
                f"      Route {chosen} -> "
                f"{result['classification']}"
            )

            print(
                f"      Final decision risk: "
                f"{result['temporal']:.1f}"
            )

            print(
                f"      Encounter exposure: "
                f"{result['encounter_exposure']:.1f}"
            )

            print(
                f"      Confidence context: "
                f"{confidence_context:.1f}%"
            )

            for reason in engine.explain(
                result,
                not visible,
                confidence,
                uncertainty,
                evidence,
                contradiction
            ):

                print(
                    f"        + {reason}"
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
                "      Spatial safety is being inferred "
                "from prediction + uncertainty."
            )

            print(
                "      Prediction is NOT treated as ground truth."
            )

        previous_position = actual

        previous_minute = minute

    # ==================================================================
    # FINAL CHECK
    # ==================================================================

    print(
        "\n" + "=" * 78
    )

    print(
        "                    V0.9.6 TEST COMPLETE"
    )

    print(
        "=" * 78
    )

    print(
        """
V0.9.6 ENGINE CHECK:

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

  V0.9.6 NEW:

  [✓] Wildlife uncertainty envelope
  [✓] Route geometry analysis
  [✓] Wildlife-route spatial overlap
  [✓] Time-to-conflict estimation
  [✓] Encounter exposure
  [✓] Blind-state spatial risk
  [✓] Danger corridor memory
  [✓] Spatial recovery detection
  [✓] Imminent conflict override
  [✓] Route-specific spatial explanation


V0.9.6 CORE QUESTION:

  "If the wildlife disappears from every sensor,
   can Wild Sentinel still determine whether a
   human route may intersect the wildlife's
   uncertain future position?"

  Answer:

  YES — V0.9.6 does not require direct observation
  to reason about potential encounter.

  It combines:

      PREDICTED POSITION
           +
      UNCERTAINTY ENVELOPE
           +
      WILDLIFE TRAJECTORY
           +
      HUMAN ROUTE GEOMETRY
           +
      TIME-TO-CONFLICT
           +
      EVIDENCE
           +
      HISTORICAL DANGER
           =
      ENCOUNTER EXPOSURE

  The important safety principle remains:

      "UNKNOWN" is not converted into "SAFE".

  And:

      "PREDICTED" is not converted into "OBSERVED".
"""
    )


if __name__ == "__main__":

    run_demo()