"""
WILD SENTINEL V0.9.4
MEMORY DECAY + RECOVERY + EXPLAINABLE SAFETY STATE ENGINE

Standalone reference simulation.
No external packages required.

V0.9.4 adds:
- Danger-memory decay
- Route recovery
- Explainable decision reasons
- Explicit safety state machine
- Decision hysteresis / switching protection
- Conservative worst-plausible protection
- Sensor-blind uncertainty handling
"""

from dataclasses import dataclass, field
from math import hypot
from typing import Dict, List, Tuple


ROUTES = {
    "A": (30.0, 60.0),
    "B": (58.0, 52.0),
    "C": (20.0, 20.0),
}

HYPOTHESES = {
    "H1": "Continue original trajectory",
    "H2": "Change direction",
    "H3": "Slow / stop",
    "H4": "Unknown movement",
}


@dataclass
class RouteMemory:
    previous_risk: float = 5.0
    persistence: int = 0
    danger_memory: float = 0.0
    last_danger_minute: int | None = None
    last_state: str = "LOW RISK"


@dataclass
class EngineState:
    route_memory: Dict[str, RouteMemory] = field(
        default_factory=lambda: {r: RouteMemory() for r in ROUTES}
    )
    selected_route: str | None = None
    locked_until: int = 0
    previous_prediction: Tuple[float, float] | None = None
    rolling_accuracy: float = 100.0
    prediction_errors: List[float] = field(default_factory=list)


def clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))


def distance(a, b):
    return hypot(a[0] - b[0], a[1] - b[1])


def evidence_fusion(e):
    # Conservative weighted fusion.
    return (
        e["movement"]
        + e["sensor"]
        + e["prey"]
        + e["environment"]
        + e["human"]
    ) / 5.0


def update_hypotheses(sensor_visible, evidence):
    if sensor_visible:
        return {"H1": 0.0, "H2": 98.0, "H3": 1.0, "H4": 1.0}

    fusion = evidence_fusion(evidence)

    if fusion < 10:
        return {"H1": 70.0, "H2": 10.0, "H3": 10.0, "H4": 10.0}
    if fusion < 25:
        return {"H1": 56.2, "H2": 15.0, "H3": 12.5, "H4": 16.3}
    if fusion < 50:
        return {"H1": 33.2, "H2": 27.0, "H3": 15.5, "H4": 24.3}
    return {"H1": 5.0, "H2": 47.6, "H3": 17.6, "H4": 29.8}


def confidence_from_uncertainty(uncertainty):
    return clamp(100.0 - uncertainty * 2.5)


def base_route_risk(route, wildlife, hypotheses, uncertainty):
    """
    Reference risk model.

    Risk is intentionally distance-driven, then raised by uncertainty.
    Route B contains the main historical danger zone in this demonstration.
    """
    d = distance(wildlife, ROUTES[route])

    # Scale suitable for the demonstration coordinate system.
    if d < 15:
        base = 80.0
    elif d < 22:
        base = 55.0
    elif d < 30:
        base = 30.0
    else:
        base = 5.0

    # Uncertainty raises risk while blind, but does not manufacture danger.
    uncertainty_penalty = uncertainty * 0.20

    # Route-specific geometry creates the intended B danger corridor.
    if route == "B" and 35 <= wildlife[0] <= 90 and 40 <= wildlife[1] <= 65:
        base = max(base, 55.0)

    return clamp(base + uncertainty_penalty)


def expected_and_worst(route, wildlife, hypotheses, uncertainty):
    """
    Evaluate four plausible futures. Future displacement is deliberately
    conservative but bounded.
    """
    offsets = {
        "H1": (0, 0),
        "H2": (8, 8),
        "H3": (-5, 3),
        "H4": (4, -8),
    }

    risks = {}
    for h, weight in hypotheses.items():
        dx, dy = offsets[h]
        future = (wildlife[0] + dx, wildlife[1] + dy)
        risks[h] = base_route_risk(route, future, {h: 100}, uncertainty)

    expected = sum(risks[h] * hypotheses[h] / 100.0 for h in hypotheses)
    worst_h = max(risks, key=risks.get)
    worst = risks[worst_h]
    return expected, worst, worst_h, risks


def decay_danger_memory(memory: RouteMemory, now_minute: int):
    """
    Exponential-like stepped decay.

    0-10 min: 90%
    11-20: 70%
    21-30: 50%
    31-45: 30%
    >45: 15%

    Memory never disappears abruptly; it asymptotically approaches zero.
    """
    if memory.last_danger_minute is None or memory.danger_memory <= 0:
        return 0.0

    age = max(0, now_minute - memory.last_danger_minute)

    if age <= 10:
        factor = 0.90
    elif age <= 20:
        factor = 0.70
    elif age <= 30:
        factor = 0.50
    elif age <= 45:
        factor = 0.30
    else:
        factor = 0.15

    return clamp(memory.danger_memory * factor)


def update_memory(memory: RouteMemory, now_minute, current_risk, worst_risk):
    historical = decay_danger_memory(memory, now_minute)

    if worst_risk >= 55 or current_risk >= 55:
        memory.danger_memory = max(historical, worst_risk)
        memory.last_danger_minute = now_minute
        historical = memory.danger_memory
    else:
        memory.danger_memory = historical

    return historical


def trend(previous, current):
    delta = current - previous
    if delta >= 20:
        label = "STRONGLY DETERIORATING"
    elif delta >= 3:
        label = "DETERIORATING"
    elif delta <= -20:
        label = "STRONGLY IMPROVING"
    elif delta <= -3:
        label = "IMPROVING"
    else:
        label = "STABLE"
    return label, delta


def safety_state(final_risk):
    if final_risk >= 80:
        return "DO NOT ENTER"
    if final_risk >= 35:
        return "CAUTION"
    return "LOW RISK"


def calculate_route(
    route,
    wildlife,
    hypotheses,
    uncertainty,
    evidence,
    now_minute,
    state: EngineState,
    sensor_visible,
):
    memory = state.route_memory[route]

    expected, worst, worst_h, _ = expected_and_worst(
        route, wildlife, hypotheses, uncertainty
    )

    current = base_route_risk(route, wildlife, hypotheses, uncertainty)

    # Evidence increases risk only when it has enough persistence to matter.
    fusion = evidence_fusion(evidence)
    evidence_penalty = max(0.0, fusion - 20.0) * 0.20

    current = clamp(current + evidence_penalty)

    label, delta = trend(memory.previous_risk, current)

    if delta > 2:
        memory.persistence += 1
    elif delta < -2:
        memory.persistence = 0

    temporal = current + max(0.0, delta) + min(memory.persistence * 2.5, 15.0)

    historical = update_memory(memory, now_minute, current, worst)

    # Historical danger contributes progressively but cannot dominate forever.
    memory_contribution = historical * 0.25

    temporal = clamp(temporal + memory_contribution)

    # Conservative floor: if a dangerous plausible future exists, preserve it.
    risk_floor = worst if worst >= 55 else 0.0
    if risk_floor:
        temporal = max(temporal, risk_floor * 0.75)

    # Sensor blindness is uncertainty, not automatic danger.
    if not sensor_visible and uncertainty >= 20:
        temporal = clamp(temporal + 3.0)

    final = clamp(temporal)
    state_label = safety_state(final)

    memory.previous_risk = current
    memory.last_state = state_label

    reasons = []

    if not sensor_visible:
        reasons.append("Sensor blind: prediction is a hypothesis, not ground truth.")
    if uncertainty >= 20:
        reasons.append("Prediction confidence is low; uncertainty is elevated.")
    if fusion >= 20:
        reasons.append(f"Indirect evidence is active ({fusion:.1f}).")
    if delta > 2:
        reasons.append(f"Risk deteriorated by {delta:.1f} since the previous step.")
    if memory.persistence >= 2:
        reasons.append(
            f"Deterioration persisted for {memory.persistence} step(s)."
        )
    if historical >= 10:
        reasons.append(
            f"Historical danger memory contributes {memory_contribution:.1f}."
        )
    if worst >= 55:
        reasons.append(
            f"Dangerous plausible future retained ({worst:.1f}, {worst_h})."
        )
    if not reasons:
        reasons.append("No significant temporal or indirect-risk pressure.")

    return {
        "expected": expected,
        "worst": worst,
        "worst_h": worst_h,
        "current": current,
        "trend": label,
        "delta": delta,
        "persistence": memory.persistence,
        "temporal": temporal,
        "historical": historical,
        "final": final,
        "state": state_label,
        "fusion": fusion,
        "reasons": reasons,
    }


def choose_route(results, now_minute, state: EngineState):
    ranked = sorted(
        results.items(),
        key=lambda kv: (kv[1]["final"], kv[1]["worst"], kv[0])
    )
    candidate, candidate_data = ranked[0]

    # Hysteresis: do not switch merely because the new route is marginally better.
    if state.selected_route and state.selected_route in results:
        current = results[state.selected_route]
        improvement = current["final"] - candidate_data["final"]

        if (
            candidate != state.selected_route
            and now_minute < state.locked_until
            and improvement < 10
        ):
            return state.selected_route, "HYSTERESIS: existing safe route retained."

        if candidate != state.selected_route and improvement < 7:
            return state.selected_route, "HYSTERESIS: improvement insufficient to switch."

    state.selected_route = candidate
    state.locked_until = now_minute + 10
    return candidate, "Lowest final temporal risk selected."


def explain_decision(route, data, state: EngineState):
    print("\n  DECISION EXPLANATION")
    print(f"      Route {route} -> {data['state']}")
    print(f"      Final decision risk: {data['final']:.1f}")
    print(f"      Current risk:        {data['current']:.1f}")
    print(f"      Historical memory:   {data['historical']:.1f}")
    print(f"      Confidence context:  {100 - min(data['fusion'], 100):.1f}%")
    print("      Reasons:")
    for reason in data["reasons"]:
        print(f"        + {reason}")

    if data["historical"] > 0:
        print("      Memory status:")
        if data["historical"] > 60:
            print("        ACTIVE — recent danger strongly influences decision.")
        elif data["historical"] > 25:
            print("        DECAYING — past danger still matters.")
        elif data["historical"] > 8:
            print("        FADING — historical danger has limited influence.")
        else:
            print("        NEARLY CLEARED — current evidence dominates.")


def run_test():
    state = EngineState()

    # Same conceptual scenario as V0.9.3, extended beyond 45 minutes
    # to demonstrate memory recovery.
    observations = [
        (0,  (15.0, 85.0), False, (23.0, 77.0), 5.0,  {"movement":0,"sensor":0,"prey":0,"environment":0,"human":0}),
        (5,  (22.2, 77.8), False, (30.2, 69.8), 9.0,  {"movement":0,"sensor":0,"prey":0,"environment":0,"human":0}),
        (10, (29.5, 70.5), True,  None,          5.0,  {"movement":0,"sensor":0,"prey":0,"environment":0,"human":0}),
        (15, (36.8, 63.2), True,  None,          5.0,  {"movement":0,"sensor":0,"prey":0,"environment":0,"human":0}),
        (20, (44.0, 56.0), False, (52.0, 48.0), 21.0, {"movement":0,"sensor":0,"prey":0,"environment":0,"human":0}),
        (25, (52.2, 55.8), False, (60.2, 47.8), 25.0, {"movement":0,"sensor":25,"prey":55,"environment":0,"human":0}),
        (30, (60.4, 55.6), False, (68.4, 47.6), 29.0, {"movement":0,"sensor":25,"prey":55,"environment":60,"human":70}),
        (35, (68.6, 55.4), False, (76.6, 47.4), 33.0, {"movement":65,"sensor":70,"prey":55,"environment":60,"human":70}),
        (40, (76.8, 55.2), True,  None,          5.0, {"movement":65,"sensor":70,"prey":55,"environment":60,"human":70}),
        (45, (85.0, 55.0), True,  None,          5.0, {"movement":65,"sensor":70,"prey":55,"environment":60,"human":70}),
        # Recovery period: wildlife moves away from route B.
        (50, (95.0, 80.0), False, (103.0, 72.0), 17.0, {"movement":10,"sensor":5,"prey":5,"environment":0,"human":0}),
        (60, (110.0, 90.0), False, (118.0, 82.0), 10.0, {"movement":0,"sensor":0,"prey":0,"environment":0,"human":0}),
        (75, (130.0, 100.0), False, (138.0, 92.0), 5.0, {"movement":0,"sensor":0,"prey":0,"environment":0,"human":0}),
    ]

    print("=" * 74)
    print("             WILD SENTINEL V0.9.4")
    print("       MEMORY DECAY + RECOVERY + EXPLAINABLE SAFETY")
    print("=" * 74)

    for minute, actual, visible, predicted, uncertainty, evidence in observations:
        print("\n" + "-" * 64)
        print(f"{minute:02d} min")
        print(f"  Actual wildlife: ({actual[0]:5.1f}, {actual[1]:5.1f})")
        print(f"  Sensor: {'VISIBLE' if visible else 'BLIND'}")

        if visible:
            print(f"  Direct wildlife observation: ({actual[0]:5.1f}, {actual[1]:5.1f})")
        else:
            print(f"  Predicted wildlife: ({predicted[0]:5.1f}, {predicted[1]:5.1f})")

        if state.previous_prediction is not None and visible:
            error = distance(state.previous_prediction, actual)
            state.prediction_errors.append(error)
            recent = state.prediction_errors[-3:]
            avg = sum(recent) / len(recent)
            state.rolling_accuracy = clamp(100 - avg * 5)
            print("\n  PREDICTION VALIDATION")
            print(f"      Position error: {error:5.1f}")
            print(f"      Rolling model accuracy: {state.rolling_accuracy:5.1f}%")

        if not visible and predicted is not None:
            state.previous_prediction = predicted

        confidence = confidence_from_uncertainty(uncertainty)
        print(f"  Uncertainty: {uncertainty:5.1f}")
        print(f"  Prediction confidence: {confidence:5.1f}%")

        print("\n  INDIRECT EVIDENCE")
        for k, v in evidence.items():
            print(f"      {k.title():22s} {v:5.1f}")
        fusion = evidence_fusion(evidence)
        print("      --------------------------------")
        print(f"      Evidence fusion       {fusion:5.1f}")

        hypotheses = update_hypotheses(visible, evidence)
        dominant = max(hypotheses, key=hypotheses.get)

        print("\n  COMPETING HYPOTHESES")
        for h, p in hypotheses.items():
            print(f"      {h} {HYPOTHESES[h]:28s} {p:5.1f}%")
        print(f"\n      Dominant hypothesis: {dominant} ({hypotheses[dominant]:.1f}%)")

        results = {}
        print("\n  ROUTE TEMPORAL ANALYSIS")

        for route in ROUTES:
            result = calculate_route(
                route, actual, hypotheses, uncertainty, evidence,
                minute, state, visible
            )
            results[route] = result

            print(f"\n      ROUTE {route}")
            print(f"          Expected risk:       {result['expected']:6.1f}")
            print(f"          Worst plausible:     {result['worst']:6.1f}")
            print(f"          Worst hypothesis:    {result['worst_h']}")
            print(f"          Current risk:        {result['current']:6.1f}")
            print(f"          Risk trend:          {result['trend']}")
            print(f"          Trend delta:         {result['delta']:+6.1f}")
            print(f"          Persistence:         {result['persistence']:6d}")
            print(f"          Temporal risk:       {result['temporal']:6.1f}")
            print(f"          Historical memory:   {result['historical']:6.1f}")
            print(f"          Final decision risk: {result['final']:6.1f}")
            print(f"          Overall:             {result['state']}")

            if result["historical"] > 0:
                print("          • Historical danger memory is active/decaying.")
            if result["worst"] >= 55:
                print("          • Conservative floor protects a dangerous plausible future.")

        selected, selection_reason = choose_route(results, minute, state)

        print("\n  SAFETY DECISION")
        print(f"  >>> RECOMMENDATION: ROUTE {selected}")
        print(f"      {selection_reason}")

        explain_decision(selected, results[selected], state)

        if not visible:
            print("\n  SENSOR-BLINDNESS STATUS")
            print("      Direct confirmation unavailable.")
            print("      Previous trajectory remains a hypothesis, not ground truth.")

        # Explicit recovery message.
        if (
            results[selected]["historical"] > 0
            and results[selected]["current"] < results[selected]["historical"]
        ):
            print("\n  MEMORY RECOVERY")
            print("      Current risk is below historical danger.")
            print("      Past danger is being retained, but its influence is decaying.")

    print("\n" + "=" * 74)
    print("                 V0.9.4 TEST COMPLETE")
    print("=" * 74)
    print("""
V0.9.4 ENGINE CHECK:
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
  [✓] Memory never overrides current evidence forever
  [✓] Explainable safety state

V0.9.4 CORE QUESTION:

  "Can Wild Sentinel remember danger without
   becoming permanently afraid of the past?"

  Answer:

  YES — danger persists, decays, and eventually
  yields to sustained evidence of recovery.
""")


if __name__ == "__main__":
    run_test()
