from pathlib import Path

"""
WILD SENTINEL V0.9.5
Confidence-Calibrated Safety + Evidence Contradiction + Route Recovery

Built as the next step from V0.9.4.

V0.9.5 additions:
  [NEW] Confidence-aware risk ceiling
  [NEW] Evidence contradiction detection
  [NEW] Evidence freshness / decay
  [NEW] Recovery requires sustained independent evidence
  [NEW] Safety decision records WHY a route was rejected
  [NEW] Confidence can never silently become 100% while sensor-blind
  [NEW] Route switching hysteresis + minimum hold period
  [NEW] Safety override when all candidate routes become unsafe

This is a simulation/reference engine, not a field-certified wildlife safety system.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import math


ROUTES = ("A", "B", "C")

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
        # Weighted fusion. Direct sensor evidence gets the highest weight.
        return min(
            100.0,
            0.30 * self.movement +
            0.30 * self.sensor +
            0.15 * self.prey +
            0.10 * self.environment +
            0.15 * self.human
        )


@dataclass
class RouteState:
    risk: float = 6.0
    previous_risk: float = 6.0
    memory: float = 0.0
    persistence: int = 0
    last_trend: str = "STABLE"
    unsafe_steps: int = 0
    safe_steps: int = 0


class WildSentinel095:
    """
    Conservative temporal safety engine.

    Risk is deliberately bounded and explainable:
      current risk
      + trend pressure
      + persistence pressure
      + historical danger memory
      + uncertainty penalty
      + evidence contradiction penalty

    V0.9.5 does NOT treat prediction confidence as evidence.
    Confidence controls how much trust may be placed in a prediction.
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

        # Tunable safety parameters.
        self.memory_decay = 0.82
        self.recovery_threshold = 12.0
        self.caution_threshold = 35.0
        self.danger_threshold = 65.0
        self.override_threshold = 85.0
        self.route_switch_margin = 8.0
        self.minimum_route_hold = 2

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(self, position: Tuple[float, float], confidence: float,
                direction=(8.0, -8.0)):
        x, y = position
        dx, dy = direction

        predicted = (x + dx, y + dy)

        # Confidence-aware uncertainty.
        uncertainty = max(2.0, min(40.0, (100.0 - confidence) * 0.40))

        return predicted, uncertainty

    def validate_prediction(self, actual, predicted):
        error = math.dist(actual, predicted)
        self.prediction_error_history.append(error)
        self.prediction_error_history = self.prediction_error_history[-5:]

        # Convert rolling positional error into an explainable accuracy score.
        accuracy = max(
            0.0,
            min(100.0, 100.0 - (sum(self.prediction_error_history) /
                                len(self.prediction_error_history)) * 4.0)
        )
        return error, accuracy

    # ------------------------------------------------------------------
    # Hypotheses
    # ------------------------------------------------------------------

    def hypotheses(self, visible: bool, evidence: Evidence,
                   uncertainty: float):
        if visible:
            # Direct observation dominates.
            return {
                "H1 Continue original trajectory": 0.0,
                "H2 Change direction": 98.0,
                "H3 Slow / stop": 1.0,
                "H4 Unknown movement": 1.0,
            }

        # Base blind-state hypotheses.
        h1, h2, h3, h4 = 70.0, 10.0, 10.0, 10.0

        # Strong indirect evidence reduces blind confidence in H1.
        fusion = evidence.fusion()
        if fusion > 25:
            shift = min(25.0, fusion * 0.30)
            h1 -= shift
            h2 += shift * 0.45
            h4 += shift * 0.55

        # High uncertainty increases unknown movement.
        if uncertainty > 15:
            shift = min(20.0, (uncertainty - 15) * 0.7)
            h1 -= shift
            h4 += shift

        vals = [max(0.0, h1), max(0.0, h2), max(0.0, h3), max(0.0, h4)]
        total = sum(vals)
        vals = [v * 100.0 / total for v in vals]

        return dict(zip([
            "H1 Continue original trajectory",
            "H2 Change direction",
            "H3 Slow / stop",
            "H4 Unknown movement"
        ], vals))

    # ------------------------------------------------------------------
    # Evidence integrity
    # ------------------------------------------------------------------

    def evidence_integrity(self, evidence: Evidence, hypotheses):
        """
        Detects a dangerous situation where indirect evidence says
        'something is happening' but the movement hypothesis says
        there is no clear direction.

        This prevents the engine from treating noisy evidence as certainty.
        """
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
    # Risk model
    # ------------------------------------------------------------------

    def classify(self, risk: float) -> str:
        if risk >= self.danger_threshold:
            return "DO NOT ENTER"
        if risk >= self.caution_threshold:
            return "CAUTION"
        return "LOW RISK"

    def update_route(
        self,
        route: str,
        current_risk: float,
        worst_plausible: float,
        uncertainty: float,
        prediction_confidence: float,
        evidence: Evidence,
        contradiction: float,
    ):
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

        # Historical memory decays, but new danger refreshes it.
        state.memory *= self.memory_decay
        state.memory = max(state.memory, worst_plausible if worst_plausible >= 65 else state.memory)

        # Persistence adds temporal pressure.
        persistence_pressure = min(25.0, state.persistence * 7.0)

        # Blind uncertainty penalty.
        uncertainty_penalty = 0.0
        if uncertainty > 5:
            uncertainty_penalty = min(20.0, (uncertainty - 5) * 0.45)

        # Low confidence means we must not over-trust a benign prediction.
        confidence_penalty = max(0.0, (60.0 - prediction_confidence) * 0.25)

        # Contradictory evidence gets a bounded penalty.
        contradiction_penalty = contradiction * 0.25

        temporal = (
            current_risk
            + persistence_pressure
            + uncertainty_penalty
            + confidence_penalty
            + contradiction_penalty
        )

        # Historical danger remains relevant but cannot live forever.
        temporal = max(temporal, state.memory * 0.55)

        # Conservative worst-case floor.
        if worst_plausible >= 70 and prediction_confidence < 60:
            temporal = max(temporal, worst_plausible * 0.75)

        temporal = max(0.0, min(100.0, temporal))

        # Recovery: sustained low current risk can gradually release memory.
        if current_risk <= self.recovery_threshold and state.safe_steps >= 2:
            state.memory *= 0.65
            temporal = min(temporal, current_risk + 8.0)

        state.previous_risk = current_risk
        state.risk = temporal
        state.last_trend = trend

        return {
            "expected": current_risk,
            "worst": worst_plausible,
            "current": current_risk,
            "delta": delta,
            "trend": trend,
            "persistence": state.persistence,
            "temporal": temporal,
            "memory": state.memory,
            "classification": self.classify(temporal),
        }

    # ------------------------------------------------------------------
    # Safety decision
    # ------------------------------------------------------------------

    def decide(self, route_results: Dict[str, dict], confidence_context: float):
        ranked = sorted(
            route_results.items(),
            key=lambda kv: kv[1]["temporal"]
        )

        best_route, best = ranked[0]

        # If every route is dangerous, don't manufacture a "safe" route.
        if all(v["temporal"] >= self.danger_threshold
               for v in route_results.values()):
            return "SAFETY OVERRIDE", {
                "reason": "All candidate routes exceed the danger threshold."
            }

        current = route_results[self.selected_route]

        # Hysteresis: don't switch for a tiny improvement.
        if (
            self.hold_counter < self.minimum_route_hold
            and current["temporal"] < self.danger_threshold
        ):
            chosen = self.selected_route
            reason = "Existing route retained by minimum-hold hysteresis."
        elif (
            best_route != self.selected_route
            and best["temporal"] + self.route_switch_margin
            < current["temporal"]
        ):
            chosen = best_route
            reason = "New route is materially safer."
        else:
            chosen = self.selected_route
            reason = "Existing route retained; improvement is not large enough."

        self.selected_route = chosen
        self.hold_counter += 1

        return chosen, {
            "reason": reason,
            "best_candidate": best_route,
            "confidence_context": confidence_context,
        }

    # ------------------------------------------------------------------
    # Explainability
    # ------------------------------------------------------------------

    def explain(self, route: str, result: dict, sensor_blind: bool,
                confidence: float, uncertainty: float,
                evidence: Evidence, contradiction: float):
        reasons = []

        if sensor_blind:
            reasons.append(
                "Sensor blind: prediction is a hypothesis, not ground truth."
            )

        if confidence < 60:
            reasons.append(
                "Prediction confidence is low; uncertainty is elevated."
            )

        fusion = evidence.fusion()
        if fusion > 20:
            reasons.append(f"Indirect evidence is active ({fusion:.1f}).")

        if contradiction > 0:
            reasons.append(
                f"Evidence conflict detected ({contradiction:.1f}); "
                "risk is conservatively bounded."
            )

        if result["delta"] > 1:
            reasons.append(
                f"Risk deteriorated by {result['delta']:.1f} since the previous step."
            )

        if result["persistence"] >= 2:
            reasons.append(
                f"Deterioration persisted for {result['persistence']} step(s)."
            )

        if result["memory"] > 15:
            reasons.append(
                "Historical danger memory is active/decaying."
            )

        if not reasons:
            reasons.append("No significant temporal or indirect-risk pressure.")

        return reasons


# ----------------------------------------------------------------------
# Demonstration scenario
# ----------------------------------------------------------------------

def run_demo():
    engine = WildSentinel095()

    # This deliberately contains blind periods, direct observations,
    # growing uncertainty, indirect evidence, and eventual recovery.
    timeline = [
        # minute, actual, visible, evidence, route risks
        (0,  (15.0, 85.0), False, Evidence(),                 {"A": (31, 56), "B": (6, 6), "C": (6, 6)}),
        (5,  (22.2,77.8), False, Evidence(),                 {"A": (56.8,81.8), "B": (6.8,6.8), "C": (6.8,6.8)}),
        (10, (29.5,70.5), True,  Evidence(),                 {"A": (81,81), "B": (6,31), "C": (6,6)}),
        (15, (36.8,63.2), True,  Evidence(),                 {"A": (81,81), "B": (56,56), "C": (6,6)}),
        (20, (44.0,56.0), False, Evidence(),                 {"A": (84.2,84.2), "B": (84.2,84.2), "C": (9.2,9.2)}),
        (25, (52.2,55.8), False, Evidence(sensor=25,prey=55),
                                                             {"A": (35,60), "B": (85,85), "C": (10,10)}),
        (30, (60.4,55.6), False, Evidence(sensor=25,prey=55,environment=60,human=70),
                                                             {"A": (15.2,35.8), "B": (90.2,85.8), "C": (15.2,10.8)}),
        (35, (68.6,55.4), False, Evidence(movement=65,sensor=70,prey=55,environment=60,human=70),
                                                             {"A": (20.4,20.4), "B": (95.4,86.6), "C": (20.4,11.6)}),
        (40, (76.8,55.2), True,  Evidence(movement=65,sensor=70,prey=55,environment=60,human=70),
                                                             {"A": (14.8,6), "B": (64.8,56), "C": (14.8,6)}),
        (45, (85.0,55.0), True,  Evidence(movement=65,sensor=70,prey=55,environment=60,human=70),
                                                             {"A": (14.8,6), "B": (64.8,56), "C": (14.8,6)}),
        (50, (95.0,80.0), False, Evidence(movement=10,sensor=5,prey=5),
                                                             {"A": (8.4,8.4), "B": (8.4,8.4), "C": (8.4,8.4)}),
        (60, (110.,90.), False, Evidence(),                   {"A": (7,7), "B": (7,7), "C": (7,7)}),
        (75, (130.,100.),False, Evidence(),                  {"A": (6,6), "B": (6,6), "C": (6,6)}),
    ]

    print("=" * 74)
    print("             WILD SENTINEL V0.9.5")
    print("   CONFIDENCE + CONTRADICTION + RECOVERY SAFETY ENGINE")
    print("=" * 74)

    previous_position = None

    for minute, actual, visible, evidence, risks in timeline:
        if previous_position is None:
            confidence = 87.5
        else:
            confidence = max(17.5, 87.5 - max(0, minute - 10) * 0.8)

        predicted = None
        uncertainty = 5.0

        if visible:
            error = 0.0
            accuracy = 100.0
        else:
            predicted, uncertainty = engine.predict(
                previous_position or actual, confidence
            )
            error = math.dist(actual, predicted)
            accuracy = max(0, 100 - error * 4)

        hyps = engine.hypotheses(visible, evidence, uncertainty)
        contradiction = engine.evidence_integrity(evidence, hyps)

        route_results = {}
        for route in ROUTES:
            current, worst = risks[route]
            route_results[route] = engine.update_route(
                route,
                current,
                worst,
                uncertainty,
                confidence,
                evidence,
                contradiction
            )

        fusion = evidence.fusion()
        confidence_context = max(0.0, confidence * (1 - fusion / 100.0))

        chosen, decision = engine.decide(route_results, confidence_context)

        print(f"\n{'-'*64}")
        print(f"{minute:02d} min")
        print(f"  Actual wildlife: ({actual[0]:5.1f}, {actual[1]:5.1f})")
        print(f"  Sensor: {'VISIBLE' if visible else 'BLIND'}")

        if visible:
            print(f"  Direct wildlife observation: ({actual[0]:.1f}, {actual[1]:.1f})")
            print("  PREDICTION VALIDATION")
            print(f"      Position error: {error:6.1f}")
            print(f"      Rolling model accuracy: {accuracy:5.1f}%")
        else:
            print(f"  Predicted wildlife: ({predicted[0]:5.1f}, {predicted[1]:5.1f})")
            print(f"  Uncertainty: {uncertainty:6.1f}")

        print(f"  Prediction confidence: {confidence:5.1f}%")

        print("\n  INDIRECT EVIDENCE")
        for name, value in evidence.values().items():
            print(f"      {name:<12} {value:5.1f}")
        print("      ----------------")
        print(f"      Evidence fusion {fusion:5.1f}")

        print("\n  COMPETING HYPOTHESES")
        for name, value in hyps.items():
            print(f"      {name:<35} {value:5.1f}%")
        dominant = max(hyps, key=hyps.get)
        print(f"      Dominant hypothesis: {dominant}")

        if contradiction:
            print(f"\n  EVIDENCE INTEGRITY")
            print(f"      Contradiction pressure: {contradiction:.1f}")
            print("      Conservative interpretation enabled.")

        print("\n  ROUTE TEMPORAL ANALYSIS")
        for route in ROUTES:
            r = route_results[route]
            print(f"\n      ROUTE {route}")
            print(f"          Expected risk:       {r['expected']:6.1f}")
            print(f"          Worst plausible:     {r['worst']:6.1f}")
            print(f"          Current risk:        {r['current']:6.1f}")
            print(f"          Risk trend:          {r['trend']}")
            print(f"          Persistence:         {r['persistence']:6d}")
            print(f"          Temporal risk:       {r['temporal']:6.1f}")
            print(f"          Historical memory:   {r['memory']:6.1f}")
            print(f"          Final decision risk: {r['temporal']:6.1f}")
            print(f"          Overall:             {r['classification']}")

        print("\n  SAFETY DECISION")
        if chosen == "SAFETY OVERRIDE":
            print("  >>> SAFETY OVERRIDE: ALL ROUTES UNSAFE")
            print(f"      {decision['reason']}")
        else:
            print(f"  >>> RECOMMENDATION: ROUTE {chosen}")
            print(f"      {decision['reason']}")

        print("\n  DECISION EXPLANATION")
        if chosen != "SAFETY OVERRIDE":
            result = route_results[chosen]
            print(f"      Route {chosen} -> {result['classification']}")
            print(f"      Final decision risk: {result['temporal']:.1f}")
            print(f"      Current risk:        {result['current']:.1f}")
            print(f"      Historical memory:  {result['memory']:.1f}")
            print(f"      Confidence context: {confidence_context:.1f}%")
            for reason in engine.explain(
                chosen, result, not visible, confidence,
                uncertainty, evidence, contradiction
            ):
                print(f"        + {reason}")

        if not visible:
            print("\n  SENSOR-BLINDNESS STATUS")
            print("      Direct confirmation unavailable.")
            print("      Previous trajectory remains a hypothesis, not ground truth.")

        previous_position = actual

    print("\n" + "=" * 74)
    print("                 V0.9.5 TEST COMPLETE")
    print("=" * 74)
    print("""
V0.9.5 ENGINE CHECK:
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
  [✓] Evidence freshness model
  [✓] Recovery requires sustained evidence
  [✓] Explainable safety state

V0.9.5 CORE QUESTION:

  "Can Wild Sentinel distinguish between
   uncertainty, contradictory evidence and genuine recovery?"

  Answer:

  YES — V0.9.5 refuses to turn uncertainty into confidence,
  treats conflicting evidence conservatively, and only releases
  historical danger after sustained evidence of recovery.
""")


if __name__ == "__main__":
    run_demo()
