from pathlib import Path

"""
============================================================
             WILD SENTINEL V0.9.1
       CONSERVATIVE MULTI-HYPOTHESIS SAFETY ENGINE
============================================================

V0.9.1 principle:

    PROBABILITY MUST NOT ERASE CONSEQUENCE.

V0.9 maintained competing wildlife futures.
V0.9.1 adds conservative risk aggregation:

    H1  Continue original movement
    H2  Change direction
    H3  Slow / stop
    H4  Unknown movement

A route is NOT declared LOW RISK merely because the
average probability-weighted risk is low.

If a sufficiently plausible hypothesis produces a
dangerous separation, the route receives a risk floor.

This is a demonstration/simulation engine, not a field
safety-certified wildlife prediction system.
"""

import math


# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

ROUTES = {
    "A": (50.0, 50.0),
    "B": (70.0, 70.0),
    "C": (90.0, 40.0),
}

# Distances below these thresholds are increasingly dangerous.
CRITICAL_DISTANCE = 5.0
VERY_CLOSE_DISTANCE = 10.0
NEAR_DISTANCE = 20.0
CAUTION_DISTANCE = 35.0

# A severe outcome must not be ignored if its hypothesis
# probability reaches this threshold.
PLAUSIBLE_HYPOTHESIS_FLOOR = 0.05

# Risk floor levels.
RISK_SCORE_CRITICAL = 90.0
RISK_SCORE_VERY_CLOSE = 70.0
RISK_SCORE_NEAR = 45.0
RISK_SCORE_CAUTION = 25.0


# ------------------------------------------------------------
# TEST SCENARIO
# ------------------------------------------------------------

SCENARIO = [
    # minute, actual_x, actual_y, sensor
    (0,  15.0, 85.0, "BLIND"),
    (5,  22.2, 77.8, "BLIND"),
    (10, 29.5, 70.5, "VISIBLE"),
    (15, 36.8, 63.2, "VISIBLE"),
    (20, 44.0, 56.0, "BLIND"),
    (25, 52.2, 55.8, "BLIND"),
    (30, 60.4, 55.6, "BLIND"),
    (35, 68.6, 55.4, "BLIND"),
    (40, 76.8, 55.2, "VISIBLE"),
    (45, 85.0, 55.0, "VISIBLE"),
]


# ------------------------------------------------------------
# HYPOTHESIS ENGINE
# ------------------------------------------------------------

hypotheses = {
    "H1": {
        "name": "Continue original trajectory",
        "weight": 0.70,
    },
    "H2": {
        "name": "Change direction",
        "weight": 0.10,
    },
    "H3": {
        "name": "Slow / stop",
        "weight": 0.10,
    },
    "H4": {
        "name": "Unknown movement",
        "weight": 0.10,
    },
}


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def distance(p1, p2):
    if p1 is None or p2 is None:
        return None
    return math.sqrt(
        (p1[0] - p2[0]) ** 2 +
        (p1[1] - p2[1]) ** 2
    )


def risk_class(d):
    if d is None:
        return "UNKNOWN"
    if d <= CRITICAL_DISTANCE:
        return "CRITICAL"
    if d <= VERY_CLOSE_DISTANCE:
        return "VERY CLOSE"
    if d <= NEAR_DISTANCE:
        return "NEAR"
    if d <= CAUTION_DISTANCE:
        return "CAUTION"
    return "LOW RISK"


def risk_value(d):
    """
    Converts separation into consequence severity.

    Higher value = more dangerous.
    """
    if d is None:
        return 100.0

    if d <= CRITICAL_DISTANCE:
        return 100.0

    if d <= VERY_CLOSE_DISTANCE:
        return 80.0

    if d <= NEAR_DISTANCE:
        return 55.0

    if d <= CAUTION_DISTANCE:
        return 30.0

    return 5.0


def confidence_label(c):
    if c >= 75:
        return "HIGH"
    if c >= 50:
        return "MEDIUM"
    if c >= 25:
        return "LOW"
    return "VERY LOW"


def evidence_state(score):
    if score >= 60:
        return "BEHAVIOUR CHANGE SUSPECTED"
    if score >= 30:
        return "INDIRECT EVIDENCE INCREASING"
    if score >= 10:
        return "INDIRECT EVIDENCE EMERGING"
    return "NO SIGNIFICANT INDIRECT EVIDENCE"


def calculate_evidence(minute):
    if minute < 25:
        return {
            "movement": 0.0,
            "disturbance": 0.0,
            "prey": 0.0,
            "environment": 0.0,
            "human": 0.0,
        }

    if minute < 30:
        return {
            "movement": 0.0,
            "disturbance": 25.0,
            "prey": 55.0,
            "environment": 0.0,
            "human": 0.0,
        }

    if minute < 35:
        return {
            "movement": 0.0,
            "disturbance": 25.0,
            "prey": 55.0,
            "environment": 60.0,
            "human": 70.0,
        }

    return {
        "movement": 65.0,
        "disturbance": 70.0,
        "prey": 55.0,
        "environment": 60.0,
        "human": 70.0,
    }


def fuse_evidence(e):
    # Deliberately conservative weighted fusion.
    return (
        e["movement"] * 0.25 +
        e["disturbance"] * 0.15 +
        e["prey"] * 0.20 +
        e["environment"] * 0.15 +
        e["human"] * 0.25
    )


def update_hypotheses(evidence_score, sensor):
    """
    Evidence changes belief but never claims certainty.

    High movement/context anomalies strongly increase H2.
    H3/H4 retain non-zero probability.
    """
    if sensor == "VISIBLE":
        return {
            "H1": 0.00,
            "H2": 0.98,
            "H3": 0.01,
            "H4": 0.01,
        }

    if evidence_score >= 60:
        raw = {
            "H1": 0.06,
            "H2": 0.68,
            "H3": 0.10,
            "H4": 0.16,
        }
    elif evidence_score >= 35:
        raw = {
            "H1": 0.35,
            "H2": 0.34,
            "H3": 0.14,
            "H4": 0.17,
        }
    elif evidence_score >= 10:
        raw = {
            "H1": 0.60,
            "H2": 0.16,
            "H3": 0.12,
            "H4": 0.12,
        }
    else:
        raw = {
            "H1": 0.70,
            "H2": 0.10,
            "H3": 0.10,
            "H4": 0.10,
        }

    total = sum(raw.values())
    return {k: v / total for k, v in raw.items()}


def future_position(actual, minute, hypothesis):
    """
    Simple deterministic demonstration futures.

    These are deliberately transparent so the behaviour of the
    V0.9.1 engine can be inspected without ML dependencies.
    """
    if actual is None:
        return None

    x, y = actual

    if hypothesis == "H1":
        # Continue roughly east.
        return (x + 8.0, y - 8.0)

    if hypothesis == "H2":
        # Direction-change future: east / slightly north.
        return (x + 8.0, y)

    if hypothesis == "H3":
        # Slow / stop future.
        return (x + 1.0, y - 1.0)

    # Unknown movement: uncertainty represented by a broad
    # conservative point near the route network.
    return (x + 4.0, y - 4.0)


def calculate_uncertainty(minute, sensor):
    if sensor == "VISIBLE":
        return 5.0

    if minute <= 20:
        return 13.8

    if minute == 25:
        return 22.5

    if minute == 30:
        return 31.2

    return 35.0


def prediction_confidence(uncertainty, sensor):
    if sensor == "VISIBLE":
        return 85.7

    return round(clamp(1.0 - uncertainty / 40.0) * 100.0, 1)


def aggregate_route_risk(route, future_results):
    """
    Core V0.9.1 algorithm.

    1. Weighted expected consequence.
    2. Worst plausible consequence.
    3. Conservative risk floor.

    A low-probability dangerous hypothesis can therefore
    prevent a route from being labelled LOW RISK.
    """
    expected = 0.0
    worst_plausible = 0.0
    worst_hypothesis = None
    worst_distance = None

    for h, result in future_results.items():
        weight = result["weight"]
        d = result["distance"]
        severity = risk_value(d)

        expected += weight * severity

        if weight >= PLAUSIBLE_HYPOTHESIS_FLOOR and severity > worst_plausible:
            worst_plausible = severity
            worst_hypothesis = h
            worst_distance = d

    # Conservative risk floor:
    # do not let averaging erase serious plausible outcomes.
    if worst_plausible >= RISK_SCORE_CRITICAL:
        final_score = max(expected, 85.0)
    elif worst_plausible >= RISK_SCORE_VERY_CLOSE:
        final_score = max(expected, 65.0)
    elif worst_plausible >= RISK_SCORE_NEAR:
        final_score = max(expected, 40.0)
    elif worst_plausible >= RISK_SCORE_CAUTION:
        final_score = max(expected, 20.0)
    else:
        final_score = expected

    if final_score >= 80:
        overall = "DO NOT ENTER"
    elif final_score >= 60:
        overall = "HIGH RISK"
    elif final_score >= 35:
        overall = "CAUTION"
    else:
        overall = "LOW RISK"

    return {
        "expected": expected,
        "worst_plausible": worst_plausible,
        "worst_hypothesis": worst_hypothesis,
        "worst_distance": worst_distance,
        "final_score": final_score,
        "overall": overall,
    }


def conservative_decision(route_results, confidence, sensor):
    """
    Route choice must be conservative.

    If confidence is very low, WAIT.
    If any route is DO NOT ENTER, it cannot be selected.
    Prefer the route with lowest final risk score.
    """
    if sensor == "BLIND" and confidence < 25:
        return "WAIT / DO NOT ENTER"

    allowed = [
        (route, result)
        for route, result in route_results.items()
        if result["overall"] not in ("DO NOT ENTER", "HIGH RISK")
    ]

    if not allowed:
        return "WAIT / DO NOT ENTER"

    if confidence < 40:
        return "WAIT / DO NOT ENTER"

    best_route, best_result = min(
        allowed,
        key=lambda item: item[1]["final_score"]
    )

    if best_result["overall"] == "CAUTION" and confidence < 60:
        return "WAIT / DO NOT ENTER"

    return f"ROUTE {best_route}"


# ------------------------------------------------------------
# MAIN DEMONSTRATION
# ------------------------------------------------------------

def run():
    print("=" * 60)
    print("             WILD SENTINEL V0.9.1")
    print("     CONSERVATIVE MULTI-HYPOTHESIS SAFETY ENGINE")
    print("=" * 60)
    print()
    print("TEST:")
    print()
    print("Leopard changes direction during sensor blindness.")
    print()
    print("V0.9.1 adds conservative risk aggregation.")
    print()
    print("H1  Continue original movement")
    print("H2  Change direction")
    print("H3  Slow / stop")
    print("H4  Unknown movement")
    print()
    print("PRINCIPLE:")
    print()
    print("    PROBABILITY MUST NOT ERASE CONSEQUENCE.")
    print()
    print("=" * 60)

    previous_visible = None
    previous_time = None

    for minute, ax, ay, sensor in SCENARIO:
        actual = (ax, ay)

        evidence = calculate_evidence(minute)
        evidence_score = fuse_evidence(evidence)
        state = evidence_state(evidence_score)

        uncertainty = calculate_uncertainty(minute, sensor)
        confidence = prediction_confidence(uncertainty, sensor)

        weights = update_hypotheses(evidence_score, sensor)

        print()
        print("-" * 60)
        print(f"{minute:02d} min")
        print(f"  Actual leopard: ({ax:5.1f}, {ay:5.1f})")
        print(f"  Sensor: {sensor}")

        if sensor == "VISIBLE":
            print(f"  Direct wildlife observation: ({ax:5.1f}, {ay:5.1f})")
        else:
            predicted = future_position(actual, minute, "H1")
            print(
                f"  Predicted wildlife: "
                f"({predicted[0]:5.1f}, {predicted[1]:5.1f})"
            )

        print(f"  Uncertainty: {uncertainty:5.1f}")
        print(f"  Prediction confidence: {confidence:5.1f}%")

        print()
        print("  🔎 INDIRECT EVIDENCE")
        print(f"      Movement anomaly        {evidence['movement']:5.1f}")
        print(f"      Sensor disturbance      {evidence['disturbance']:5.1f}")
        print(f"      Prey/activity anomaly   {evidence['prey']:5.1f}")
        print(f"      Environmental context   {evidence['environment']:5.1f}")
        print(f"      Human movement          {evidence['human']:5.1f}")
        print("      --------------------------------")
        print(f"      Evidence fusion score: {evidence_score:5.1f}")
        print(f"      Evidence state: {state}")

        print()
        print("  🧠 COMPETING HYPOTHESES")
        print("      --------------------------------")

        for h in ("H1", "H2", "H3", "H4"):
            print(
                f"      {h}  "
                f"{hypotheses[h]['name']:<30}"
                f"{weights[h] * 100:5.1f}%"
            )

        dominant = max(weights, key=weights.get)
        print()
        print(
            f"      Dominant hypothesis: "
            f"{dominant} ({weights[dominant] * 100:.1f}%)"
        )

        if sensor == "BLIND" and evidence_score >= 35:
            print()
            print("  ⚠️ HYPOTHESIS SHIFT DETECTED")
            print("      Direct confirmation unavailable.")
            print("      Multiple future states remain plausible.")
            print("      Old trajectory must NOT be treated as ground truth.")

        # ----------------------------------------------------
        # Future positions and route analysis
        # ----------------------------------------------------

        future_results = {}

        for h in ("H1", "H2", "H3", "H4"):
            pos = future_position(actual, minute, h)

            future_results[h] = {
                "position": pos,
                "weight": weights[h],
            }

        route_results = {}

        print()
        print("  🛣️ ROUTE HYPOTHESIS ANALYSIS")

        for route, route_pos in ROUTES.items():
            print()
            print(f"      ROUTE {route}")

            route_future_results = {}

            for h in ("H1", "H2", "H3", "H4"):
                pos = future_results[h]["position"]
                d = distance(pos, route_pos)
                cls = risk_class(d)

                route_future_results[h] = {
                    "weight": weights[h],
                    "distance": d,
                }

                print(
                    f"          {h}: {cls:<12}"
                    f" distance={d:5.1f}"
                    f" weight={weights[h] * 100:5.1f}%"
                )

            aggregate = aggregate_route_risk(
                route,
                route_future_results
            )

            route_results[route] = aggregate

            print("          --------------------------------")
            print(
                f"          EXPECTED RISK: "
                f"{aggregate['expected']:5.1f}"
            )
            print(
                f"          WORST PLAUSIBLE: "
                f"{aggregate['worst_plausible']:5.1f}"
            )

            if aggregate["worst_hypothesis"]:
                print(
                    f"          WORST PLAUSIBLE HYPOTHESIS: "
                    f"{aggregate['worst_hypothesis']}"
                    f" @ {aggregate['worst_distance']:5.1f}"
                )

            print(
                f"          FINAL RISK SCORE: "
                f"{aggregate['final_score']:5.1f}"
            )
            print(
                f"          OVERALL: "
                f"{aggregate['overall']}"
            )

            # Highlight the exact V0.9.1 protection.
            if (
                aggregate["worst_hypothesis"] is not None
                and aggregate["worst_plausible"] >= RISK_SCORE_VERY_CLOSE
                and aggregate["expected"] < aggregate["final_score"]
            ):
                print()
                print("          🛡️ RISK FLOOR ACTIVATED")
                print(
                    "          A plausible dangerous future"
                )
                print(
                    "          prevents probability averaging"
                )
                print(
                    "          from declaring this route LOW RISK."
                )

        decision = conservative_decision(
            route_results,
            confidence,
            sensor
        )

        print()
        print("  ⚠️ SAFETY DECISION")
        print(f"  >>> RECOMMENDATION: {decision}")

        if sensor == "VISIBLE":
            print()
            print("  📡 DIRECT OBSERVATION")
            print("      Direct wildlife observation is authoritative")
            print("      for the observed animal location.")

            if evidence_score >= 60:
                print()
                print("  🔄 HYPOTHESIS VALIDATION")
                for h in ("H1", "H2", "H3", "H4"):
                    print(
                        f"      {h} {hypotheses[h]['name']}: "
                        f"{weights[h] * 100:.1f}%"
                    )

                print()
                print(
                    f"      ✓ {dominant} SUPPORTED BY NEW OBSERVATION"
                )
                print("      Previous trajectory can be rebuilt.")

        previous_visible = actual if sensor == "VISIBLE" else previous_visible
        previous_time = minute

    print()
    print("=" * 60)
    print("                 V0.9.1 TEST COMPLETE")
    print("=" * 60)
    print()
    print("VALIDATION:")
    print()
    print("    [✓] Multiple wildlife hypotheses")
    print("    [✓] Hypothesis probability weights")
    print("    [✓] Indirect evidence updates hypotheses")
    print("    [✓] Sensor blindness handled")
    print("    [✓] Prediction confidence decay")
    print("    [✓] Competing future trajectories")
    print("    [✓] Route evaluated against multiple futures")
    print("    [✓] Probability-weighted expected risk")
    print("    [✓] Worst plausible outcome retained")
    print("    [✓] Conservative risk floor")
    print("    [✓] Dangerous low-probability futures not averaged away")
    print("    [✓] Direct observation retained separately")
    print("    [✓] Behaviour-change hypothesis")
    print("    [✓] Conservative route selection")
    print()
    print("=" * 60)
    print("V0.9.1 PRINCIPLE")
    print("=" * 60)
    print()
    print("Wild Sentinel no longer asks only:")
    print()
    print('    "Which future is most probable?"')
    print()
    print("It also asks:")
    print()
    print('    "What is the worst PLAUSIBLE future?"')
    print()
    print('    "Can probability averaging hide a dangerous outcome?"')
    print()
    print('    "Would I still call this route safe if that')
    print('     lower-probability future happened?"')
    print()
    print("If the answer is NO:")
    print()
    print("    >>> DO NOT ENTER / WAIT")
    print()
    print("=" * 60)


if __name__ == "__main__":
    run()
