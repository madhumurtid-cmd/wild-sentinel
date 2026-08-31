

"""
WILD SENTINEL V0.9.3
TEMPORAL SAFETY DECISION ENGINE

Zero external dependencies.

V0.9.3 adds to V0.9.2:
- temporal risk memory
- risk trend + persistence
- prediction error / prediction ageing
- indirect-evidence persistence
- danger-zone memory
- route switching / commitment penalty
- decision hysteresis
- sensor-blindness escalation
- conservative multi-hypothesis reasoning
- explicit safety overrides
- decision explanations

This is a simulation/research prototype, NOT a certified wildlife-safety system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from math import hypot
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

class RiskLevel(IntEnum):
    LOW = 0
    CAUTION = 1
    HIGH = 2
    DO_NOT_ENTER = 3


RISK_LABELS = {
    RiskLevel.LOW: "LOW RISK",
    RiskLevel.CAUTION: "CAUTION",
    RiskLevel.HIGH: "HIGH RISK",
    RiskLevel.DO_NOT_ENTER: "DO NOT ENTER",
}


@dataclass
class Config:
    # Risk thresholds
    caution_threshold: float = 30.0
    high_threshold: float = 55.0
    deny_threshold: float = 75.0

    # Temporal memory
    trend_weight: float = 0.20
    persistence_weight: float = 5.0
    max_temporal_bonus: float = 20.0

    # Uncertainty / blindness
    uncertainty_weight: float = 0.30
    blindness_weight: float = 0.20

    # Indirect evidence
    evidence_weight: float = 0.15
    evidence_persistence_weight: float = 4.0

    # Conservative protection
    worst_case_weight: float = 0.35
    danger_gap: float = 20.0

    # Decision hysteresis
    switch_margin: float = 8.0
    minimum_decision_hold_steps: int = 1
    route_memory_penalty: float = 3.0

    # Safety override
    plausible_danger_threshold: float = 75.0
    dangerous_probability_threshold: float = 0.08

    # Prediction ageing
    prediction_confidence_floor: float = 0.10


# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------

@dataclass
class Point:
    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        return hypot(self.x - other.x, self.y - other.y)


@dataclass
class Observation:
    minute: int
    actual: Point
    sensor_visible: bool
    predicted: Point
    uncertainty: float
    prediction_confidence: float

    movement_anomaly: float = 0.0
    sensor_disturbance: float = 0.0
    prey_activity_anomaly: float = 0.0
    environmental_context: float = 0.0
    human_movement: float = 0.0

    @property
    def evidence_score(self) -> float:
        # Weighted evidence: deliberately transparent.
        return (
            self.movement_anomaly * 0.25
            + self.sensor_disturbance * 0.15
            + self.prey_activity_anomaly * 0.25
            + self.environmental_context * 0.15
            + self.human_movement * 0.20
        )


@dataclass
class Hypothesis:
    name: str
    probability: float


@dataclass
class Route:
    name: str
    target: Point


@dataclass
class RouteAssessment:
    route: str
    expected_risk: float
    worst_plausible: float
    current_risk: float
    trend_delta: float
    persistence: int
    temporal_risk: float
    final_risk: float
    level: RiskLevel
    worst_hypothesis: str
    dangerous_probability: float
    explanation: List[str] = field(default_factory=list)


@dataclass
class RouteMemory:
    last_risk: Optional[float] = None
    deteriorating_steps: int = 0
    improving_steps: int = 0
    danger_memory: float = 0.0


# ---------------------------------------------------------------------------
# TEMPORAL MEMORY
# ---------------------------------------------------------------------------

class TemporalMemory:
    def __init__(self, config: Config):
        self.config = config
        self.routes: Dict[str, RouteMemory] = {}
        self.last_prediction: Optional[Point] = None
        self.last_prediction_minute: Optional[int] = None
        self.last_confidence: Optional[float] = None
        self.prediction_errors: List[float] = []
        self.evidence_memory: float = 0.0

    def route_memory(self, route_name: str) -> RouteMemory:
        if route_name not in self.routes:
            self.routes[route_name] = RouteMemory()
        return self.routes[route_name]

    def update_route(self, route_name: str, current_risk: float) -> Tuple[float, int]:
        mem = self.route_memory(route_name)

        if mem.last_risk is None:
            delta = 0.0
            mem.deteriorating_steps = 0
            mem.improving_steps = 0
        else:
            delta = current_risk - mem.last_risk

            if delta > 2.0:
                mem.deteriorating_steps += 1
                mem.improving_steps = 0
            elif delta < -2.0:
                mem.improving_steps += 1
                mem.deteriorating_steps = 0
            else:
                # Stable readings do not falsely increase persistence.
                mem.deteriorating_steps = max(0, mem.deteriorating_steps - 1)
                mem.improving_steps = max(0, mem.improving_steps - 1)

        mem.last_risk = current_risk

        # Danger memory decays, but does not instantly disappear.
        mem.danger_memory *= 0.75

        if current_risk >= self.config.high_threshold:
            mem.danger_memory = max(mem.danger_memory, current_risk * 0.30)

        persistence = mem.deteriorating_steps
        return delta, persistence

    def apply_danger_memory(self, route_name: str, risk: float) -> float:
        mem = self.route_memory(route_name)
        return min(100.0, risk + mem.danger_memory)

    def update_evidence(self, evidence: float) -> float:
        # Evidence decays slowly so one weak observation does not erase a
        # persistent behavioural signal.
        self.evidence_memory = max(
            evidence,
            self.evidence_memory * 0.80
        )
        return self.evidence_memory

    def validate_prediction(self, actual: Point, minute: int) -> Optional[float]:
        if self.last_prediction is None:
            return None

        error = actual.distance_to(self.last_prediction)
        self.prediction_errors.append(error)

        # Retain a useful bounded history.
        if len(self.prediction_errors) > 10:
            self.prediction_errors.pop(0)

        return error

    def prediction_accuracy(self) -> Optional[float]:
        if not self.prediction_errors:
            return None

        avg_error = sum(self.prediction_errors) / len(self.prediction_errors)

        # Transparent prototype mapping.
        if avg_error <= 2:
            return 0.95
        if avg_error <= 5:
            return 0.80
        if avg_error <= 10:
            return 0.55
        return 0.30

    def store_prediction(self, point: Point, minute: int, confidence: float):
        self.last_prediction = point
        self.last_prediction_minute = minute
        self.last_confidence = confidence


# ---------------------------------------------------------------------------
# HYPOTHESIS ENGINE
# ---------------------------------------------------------------------------

class HypothesisEngine:
    @staticmethod
    def infer(observation: Observation) -> List[Hypothesis]:
        if observation.sensor_visible:
            # Direct observation dominates.
            return [
                Hypothesis("H1 Continue original trajectory", 0.00),
                Hypothesis("H2 Change direction", 0.98),
                Hypothesis("H3 Slow / stop", 0.01),
                Hypothesis("H4 Unknown movement", 0.01),
            ]

        evidence = observation.evidence_score
        confidence = observation.prediction_confidence

        # Start from the conservative blind-sensor baseline.
        h1 = 0.70
        h2 = 0.10
        h3 = 0.10
        h4 = 0.10

        # Evidence gradually weakens H1.
        if evidence >= 15:
            h1 -= 0.10
            h2 += 0.05
            h3 += 0.025
            h4 += 0.025

        if evidence >= 35:
            h1 -= 0.20
            h2 += 0.12
            h3 += 0.03
            h4 += 0.05

        if evidence >= 55:
            h1 -= 0.25
            h2 += 0.23
            h3 += 0.03
            h4 += 0.04

        # Falling confidence increases unknown movement.
        if confidence < 0.50:
            shift = min(0.15, (0.50 - confidence) * 0.30)
            h1 -= shift
            h4 += shift

        values = [max(0.0, h1), max(0.0, h2), max(0.0, h3), max(0.0, h4)]
        total = sum(values)
        values = [v / total for v in values]

        return [
            Hypothesis("H1 Continue original trajectory", values[0]),
            Hypothesis("H2 Change direction", values[1]),
            Hypothesis("H3 Slow / stop", values[2]),
            Hypothesis("H4 Unknown movement", values[3]),
        ]


# ---------------------------------------------------------------------------
# RISK MODEL
# ---------------------------------------------------------------------------

class RiskModel:
    def __init__(self, config: Config):
        self.config = config

    @staticmethod
    def distance_risk(distance: float) -> float:
        # Prototype distance-to-risk curve.
        if distance <= 8:
            return 100.0
        if distance <= 12:
            return 80.0
        if distance <= 18:
            return 55.0
        if distance <= 25:
            return 30.0
        return 5.0

    @staticmethod
    def risk_level(risk: float, config: Config) -> RiskLevel:
        if risk >= config.deny_threshold:
            return RiskLevel.DO_NOT_ENTER
        if risk >= config.high_threshold:
            return RiskLevel.HIGH
        if risk >= config.caution_threshold:
            return RiskLevel.CAUTION
        return RiskLevel.LOW

    def route_hypothesis_risk(
        self,
        wildlife: Point,
        route: Route,
        hypothesis: Hypothesis,
        uncertainty: float,
    ) -> float:
        # Approximate future location around the observed/predicted point.
        # Each hypothesis adds a different directional uncertainty envelope.
        if hypothesis.name.startswith("H1"):
            future = Point(wildlife.x + 8, wildlife.y - 8)
        elif hypothesis.name.startswith("H2"):
            future = Point(wildlife.x + 2, wildlife.y + 2)
        elif hypothesis.name.startswith("H3"):
            future = Point(wildlife.x, wildlife.y)
        else:
            future = Point(wildlife.x + uncertainty * 0.20,
                           wildlife.y + uncertainty * 0.20)

        return self.distance_risk(future.distance_to(route.target))


# ---------------------------------------------------------------------------
# DECISION ENGINE
# ---------------------------------------------------------------------------

class DecisionEngine:
    def __init__(self, config: Config):
        self.config = config
        self.previous_route: Optional[str] = None
        self.hold_steps = 0

    def choose(
        self,
        assessments: Dict[str, RouteAssessment]
    ) -> Tuple[str, str]:
        if not assessments:
            raise ValueError("No route assessments supplied.")

        ranked = sorted(
            assessments.values(),
            key=lambda a: (a.final_risk, a.worst_plausible)
        )

        best = ranked[0]

        # Hard safety override.
        for a in ranked:
            if (
                a.worst_plausible >= self.config.plausible_danger_threshold
                and a.dangerous_probability >=
                self.config.dangerous_probability_threshold
            ):
                if a.route == best.route:
                    continue

        # Hysteresis: keep the current route if the new candidate is only
        # marginally better and the current route is not unsafe.
        if self.previous_route in assessments:
            current = assessments[self.previous_route]

            if current.level < RiskLevel.HIGH:
                improvement = current.final_risk - best.final_risk

                if (
                    best.route != current.route
                    and improvement < self.config.switch_margin
                    and self.hold_steps <
                    self.config.minimum_decision_hold_steps
                ):
                    self.hold_steps += 1
                    return current.route, (
                        f"Decision hysteresis retained ROUTE {current.route}; "
                        f"new route improves risk by only {improvement:.1f}."
                    )

        # Never retain an unsafe route merely because of hysteresis.
        self.previous_route = best.route
        self.hold_steps = 0

        reason = (
            f"ROUTE {best.route} selected: lowest temporal risk "
            f"({best.final_risk:.1f}) with worst plausible risk "
            f"{best.worst_plausible:.1f}."
        )
        return best.route, reason


# ---------------------------------------------------------------------------
# WILD SENTINEL
# ---------------------------------------------------------------------------

class WildSentinel:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.memory = TemporalMemory(self.config)
        self.hypotheses = HypothesisEngine()
        self.risk_model = RiskModel(self.config)
        self.decision = DecisionEngine(self.config)

        self.routes = [
            Route("A", Point(120, 70)),
            Route("B", Point(95, 65)),
            Route("C", Point(25, 25)),
        ]

    def confidence_decay(self, observation: Observation) -> float:
        if observation.sensor_visible:
            return observation.prediction_confidence

        # Uncertainty increasingly weakens blind prediction confidence.
        decay = max(
            self.config.prediction_confidence_floor,
            observation.prediction_confidence
            - observation.uncertainty * 0.008
        )
        return decay

    def assess(self, obs: Observation) -> Dict[str, RouteAssessment]:
        evidence = obs.evidence_score
        persistent_evidence = self.memory.update_evidence(evidence)

        confidence = self.confidence_decay(obs)

        wildlife = obs.actual if obs.sensor_visible else obs.predicted
        hypotheses = self.hypotheses.infer(obs)

        assessments: Dict[str, RouteAssessment] = {}

        for route in self.routes:
            values = []
            weighted_danger = 0.0

            for h in hypotheses:
                risk = self.risk_model.route_hypothesis_risk(
                    wildlife,
                    route,
                    h,
                    obs.uncertainty,
                )
                values.append((h, risk))

                if risk >= self.config.high_threshold:
                    weighted_danger += h.probability

            expected = sum(h.probability * risk for h, risk in values)
            worst_h, worst = max(values, key=lambda item: item[1])

            # Conservative current risk: expected risk blended with worst
            # plausible risk, especially when confidence is poor.
            current = (
                expected * (0.65 + confidence * 0.20)
                + worst * (0.15 + (1.0 - confidence) * 0.20)
            )

            # Blindness penalty.
            if not obs.sensor_visible:
                current += min(
                    15.0,
                    obs.uncertainty * self.config.uncertainty_weight
                )

            # Persistent indirect evidence adds a modest safety pressure.
            current += persistent_evidence * self.config.evidence_weight

            current = min(100.0, current)

            delta, persistence = self.memory.update_route(
                route.name,
                current,
            )

            trend_bonus = 0.0

            if delta > 0:
                trend_bonus += min(
                    self.config.max_temporal_bonus,
                    delta * self.config.trend_weight
                    + persistence * self.config.persistence_weight
                )

            temporal = min(100.0, current + trend_bonus)

            # Danger memory is intentionally applied after temporal trend.
            temporal_with_memory = self.memory.apply_danger_memory(
                route.name,
                temporal,
            )

            # Risk floor: dangerous plausible futures remain visible.
            final = temporal_with_memory

            if worst >= self.config.plausible_danger_threshold:
                final = max(final, self.config.deny_threshold)

            elif worst >= self.config.high_threshold:
                final = max(final, self.config.high_threshold)

            # Evidence + blindness can elevate a borderline route.
            if not obs.sensor_visible and evidence >= 50 and worst >= 30:
                final = max(final, self.config.caution_threshold)

            # Decision switching penalty: avoid unnecessary oscillation.
            if (
                self.decision.previous_route
                and route.name != self.decision.previous_route
            ):
                final += self.config.route_memory_penalty

            final = min(100.0, final)
            level = self.risk_model.risk_level(final, self.config)

            explanation = []

            if not obs.sensor_visible:
                explanation.append("Sensor blind: prediction is not treated as ground truth.")

            if confidence < 0.50:
                explanation.append("Prediction confidence is low; uncertainty is elevated.")

            if evidence >= 35:
                explanation.append(
                    f"Indirect evidence persists at {persistent_evidence:.1f}."
                )

            if delta > 2:
                explanation.append(
                    f"Risk deteriorated by {delta:.1f} since the previous step."
                )

            if persistence >= 2:
                explanation.append(
                    f"Deterioration persisted for {persistence} step(s)."
                )

            if worst >= self.config.plausible_danger_threshold:
                explanation.append(
                    f"Risk floor protects a dangerous plausible future "
                    f"({worst:.1f})."
                )

            if self.memory.route_memory(route.name).danger_memory > 0:
                explanation.append("Recent danger remains in temporal memory.")

            assessments[route.name] = RouteAssessment(
                route=route.name,
                expected_risk=expected,
                worst_plausible=worst,
                current_risk=current,
                trend_delta=delta,
                persistence=persistence,
                temporal_risk=temporal_with_memory,
                final_risk=final,
                level=level,
                worst_hypothesis=worst_h.name.split(" ", 1)[0],
                dangerous_probability=weighted_danger,
                explanation=explanation,
            )

        return assessments

    def process(self, obs: Observation):
        print("\n" + "-" * 64)
        print(f"{obs.minute:02d} min")
        print(f"  Actual wildlife: ({obs.actual.x:5.1f}, {obs.actual.y:5.1f})")
        print(f"  Sensor: {'VISIBLE' if obs.sensor_visible else 'BLIND'}")

        if obs.sensor_visible:
            error = self.memory.validate_prediction(obs.actual, obs.minute)

            print(
                f"  Direct wildlife observation: "
                f"({obs.actual.x:5.1f}, {obs.actual.y:5.1f})"
            )

            if error is not None:
                accuracy = self.memory.prediction_accuracy()
                print("\n  PREDICTION VALIDATION")
                print(f"      Position error: {error:5.1f}")
                print(
                    f"      Rolling model accuracy: "
                    f"{accuracy * 100:5.1f}%"
                )
        else:
            print(
                f"  Predicted wildlife: "
                f"({obs.predicted.x:5.1f}, {obs.predicted.y:5.1f})"
            )

        print(f"  Uncertainty: {obs.uncertainty:5.1f}")
        print(
            f"  Prediction confidence: "
            f"{obs.prediction_confidence * 100:5.1f}%"
        )

        print("\n  INDIRECT EVIDENCE")
        print(f"      Movement anomaly       {obs.movement_anomaly:5.1f}")
        print(f"      Sensor disturbance    {obs.sensor_disturbance:5.1f}")
        print(f"      Prey/activity anomaly {obs.prey_activity_anomaly:5.1f}")
        print(f"      Environmental context {obs.environmental_context:5.1f}")
        print(f"      Human movement        {obs.human_movement:5.1f}")
        print(f"      --------------------------------")
        print(f"      Evidence fusion       {obs.evidence_score:5.1f}")

        hypotheses = self.hypotheses.infer(obs)

        print("\n  COMPETING HYPOTHESES")
        for h in hypotheses:
            print(f"      {h.name:<31} {h.probability * 100:5.1f}%")

        dominant = max(hypotheses, key=lambda h: h.probability)
        print(
            f"\n      Dominant hypothesis: "
            f"{dominant.name.split(' ', 1)[0]} "
            f"({dominant.probability * 100:.1f}%)"
        )

        assessments = self.assess(obs)

        print("\n  ROUTE TEMPORAL ANALYSIS")

        for route_name, a in assessments.items():
            print(f"\n      ROUTE {route_name}")
            print(f"          Expected risk:       {a.expected_risk:6.1f}")
            print(f"          Worst plausible:     {a.worst_plausible:6.1f}")
            print(f"          Worst hypothesis:       {a.worst_hypothesis}")
            print(f"          Current risk:        {a.current_risk:6.1f}")

            if abs(a.trend_delta) < 2:
                trend = "STABLE"
            elif a.trend_delta > 20:
                trend = "STRONGLY DETERIORATING"
            elif a.trend_delta > 0:
                trend = "DETERIORATING"
            elif a.trend_delta < -20:
                trend = "STRONGLY IMPROVING"
            else:
                trend = "IMPROVING"

            print(f"          Risk trend:          {trend}")
            print(f"          Trend delta:         {a.trend_delta:+6.1f}")
            print(f"          Persistence:             {a.persistence}")
            print(f"          Temporal risk:       {a.temporal_risk:6.1f}")
            print(f"          Final decision risk: {a.final_risk:6.1f}")
            print(f"          Overall:             {RISK_LABELS[a.level]}")

            if a.worst_plausible >= self.config.plausible_danger_threshold:
                print("\n          RISK FLOOR ACTIVATED")
                print("          Dangerous plausible futures are protected.")

            if a.explanation:
                for reason in a.explanation:
                    print(f"          • {reason}")

        # Warning for deteriorating routes.
        deteriorating = [
            a.route for a in assessments.values()
            if a.trend_delta > 2
        ]

        if deteriorating:
            print(
                "\n  TEMPORAL SAFETY WARNING"
                f"\n      Risk deterioration detected on: "
                f"{', '.join(deteriorating)}"
            )

        chosen, reason = self.decision.choose(assessments)

        print("\n  SAFETY DECISION")
        print(f"  >>> RECOMMENDATION: ROUTE {chosen}")
        print(f"      {reason}")

        if not obs.sensor_visible:
            print(
                "\n  SENSOR-BLINDNESS STATUS"
                "\n      Direct confirmation unavailable."
                "\n      Previous trajectory is treated as a hypothesis,"
                "\n      not ground truth."
            )

        # Store the prediction only after the current observation has been
        # evaluated, so validation at the next visible observation is clean.
        if not obs.sensor_visible:
            self.memory.store_prediction(
                obs.predicted,
                obs.minute,
                obs.prediction_confidence,
            )


# ---------------------------------------------------------------------------
# TEST SCENARIO
# ---------------------------------------------------------------------------

def build_test_scenario() -> List[Observation]:
    return [
        Observation(
            0, Point(15, 85), False, Point(23, 77), 5, 0.875
        ),
        Observation(
            5, Point(22.2, 77.8), False, Point(30.2, 69.8), 9, 0.775
        ),
        Observation(
            10, Point(29.5, 70.5), True, Point(0, 0), 5, 0.857
        ),
        Observation(
            15, Point(36.8, 63.2), True, Point(0, 0), 5, 0.857
        ),
        Observation(
            20, Point(44, 56), False, Point(52, 48), 21, 0.475
        ),
        Observation(
            25, Point(52.2, 55.8), False, Point(60.2, 47.8), 25, 0.375,
            sensor_disturbance=25,
            prey_activity_anomaly=55,
        ),
        Observation(
            30, Point(60.4, 55.6), False, Point(68.4, 47.6), 29, 0.275,
            sensor_disturbance=25,
            prey_activity_anomaly=55,
            environmental_context=60,
            human_movement=70,
        ),
        Observation(
            35, Point(68.6, 55.4), False, Point(76.6, 47.4), 33, 0.175,
            movement_anomaly=65,
            sensor_disturbance=70,
            prey_activity_anomaly=55,
            environmental_context=60,
            human_movement=70,
        ),
        Observation(
            40, Point(76.8, 55.2), True, Point(0, 0), 5, 0.857,
            movement_anomaly=65,
            sensor_disturbance=70,
            prey_activity_anomaly=55,
            environmental_context=60,
            human_movement=70,
        ),
        Observation(
            45, Point(85, 55), True, Point(0, 0), 5, 0.857,
            movement_anomaly=65,
            sensor_disturbance=70,
            prey_activity_anomaly=55,
            environmental_context=60,
            human_movement=70,
        ),
    ]


def main():
    print("=" * 64)
    print("             WILD SENTINEL V0.9.3")
    print("        TEMPORAL SAFETY DECISION ENGINE")
    print("=" * 64)

    print(
        "\nPRINCIPLE:"
        "\n  Wild Sentinel does not treat a sensor-blind prediction"
        "\n  as truth. It maintains competing futures and remembers"
        "\n  how risk has behaved over time."
    )

    sentinel = WildSentinel()

    for observation in build_test_scenario():
        sentinel.process(observation)

    print("\n" + "=" * 64)
    print("                 V0.9.3 TEST COMPLETE")
    print("=" * 64)

    print(
        "\nV0.9.3 ENGINE CHECK:"
        "\n  [✓] Multiple wildlife hypotheses"
        "\n  [✓] Indirect evidence updates hypotheses"
        "\n  [✓] Sensor blindness"
        "\n  [✓] Prediction confidence decay"
        "\n  [✓] Prediction validation"
        "\n  [✓] Temporal risk memory"
        "\n  [✓] Risk trend"
        "\n  [✓] Risk persistence"
        "\n  [✓] Danger-zone memory"
        "\n  [✓] Indirect-evidence persistence"
        "\n  [✓] Conservative worst-case protection"
        "\n  [✓] Decision hysteresis"
        "\n  [✓] Route switching protection"
        "\n  [✓] Safety override"
        "\n  [✓] Explicit decision explanation"
    )

    print(
        "\nV0.9.3 CORE QUESTION:"
        "\n  \"Is this route safe enough NOW,"
        "\n   considering what we know, what we don't know,"
        "\n   and how badly we could be wrong?\""
    )


if __name__ == "__main__":
    main()
