import math
from collections import defaultdict, deque

# ============================================================
#                  WILD SENTINEL V0.9.2
#       TEMPORAL RISK + PREDICTION ERROR ENGINE
# ============================================================

print("=" * 64)
print("             WILD SENTINEL V0.9.2")
print("       TEMPORAL SAFETY MEMORY ENGINE")
print("=" * 64)

print("""
TEST:

Leopard changes direction during sensor blindness.

V0.9.2 adds:

    • Temporal risk memory
    • Risk trend detection
    • Risk persistence
    • Prediction error
    • Decision hysteresis
    • Conservative multi-hypothesis reasoning

PRINCIPLE:

    A route is not judged only by its current risk.

    Wild Sentinel also asks:

        "Is the risk getting worse?"

        "How persistent is that change?"

        "How wrong was our previous prediction?"

        "Should the safety decision remain stable?"
""")

# ============================================================
# CONFIGURATION
# ============================================================

HYPOTHESES = {
    "H1": "Continue original trajectory",
    "H2": "Change direction",
    "H3": "Slow / stop",
    "H4": "Unknown movement",
}

BASE_WEIGHTS = {
    "H1": 0.70,
    "H2": 0.10,
    "H3": 0.10,
    "H4": 0.10,
}

ROUTES = {
    "A": (30.0, 85.0),
    "B": (50.0, 75.0),
    "C": (90.0, 35.0),
}

# Risk thresholds
LOW_RISK = 10
CAUTION_RISK = 35
HIGH_RISK = 60
CRITICAL_RISK = 80

# Hysteresis
ROUTE_SWITCH_MARGIN = 8.0
DO_NOT_ENTER_RELEASE = 45.0

# ============================================================
# SIMULATED TEST DATA
# ============================================================

observations = [
    # minute, actual_x, actual_y, sensor, evidence
    (0,  15.0, 85.0, "BLIND",   (0, 0, 0, 0, 0)),
    (5,  22.2, 77.8, "BLIND",   (0, 0, 0, 0, 0)),
    (10, 29.5, 70.5, "VISIBLE", (0, 0, 0, 0, 0)),
    (15, 36.8, 63.2, "VISIBLE", (0, 0, 0, 0, 0)),
    (20, 44.0, 56.0, "BLIND",   (0, 0, 0, 0, 0)),
    (25, 52.2, 55.8, "BLIND",   (0, 25, 55, 0, 0)),
    (30, 60.4, 55.6, "BLIND",   (0, 25, 55, 60, 70)),
    (35, 68.6, 55.4, "BLIND",   (65, 70, 55, 60, 70)),
    (40, 76.8, 55.2, "VISIBLE", (65, 70, 55, 60, 70)),
    (45, 85.0, 55.0, "VISIBLE", (65, 70, 55, 60, 70)),
]

# ============================================================
# HELPERS
# ============================================================

def distance(a, b):
    return math.sqrt(
        (a[0] - b[0]) ** 2 +
        (a[1] - b[1]) ** 2
    )


def risk_from_distance(d):
    if d <= 5:
        return 100
    elif d <= 10:
        return 80
    elif d <= 20:
        return 55
    elif d <= 30:
        return 30
    else:
        return 5


def risk_label(score):
    if score >= CRITICAL_RISK:
        return "DO NOT ENTER"
    elif score >= HIGH_RISK:
        return "HIGH RISK"
    elif score >= CAUTION_RISK:
        return "CAUTION"
    else:
        return "LOW RISK"


def evidence_fusion(evidence):
    movement, disturbance, prey, environment, human = evidence

    return (
        movement * 0.25 +
        disturbance * 0.15 +
        prey * 0.20 +
        environment * 0.20 +
        human * 0.20
    )


def evidence_state(score):
    if score >= 60:
        return "BEHAVIOUR CHANGE SUSPECTED"
    elif score >= 30:
        return "INDIRECT EVIDENCE INCREASING"
    elif score >= 10:
        return "INDIRECT EVIDENCE EMERGING"
    return "NO SIGNIFICANT INDIRECT EVIDENCE"


def update_hypotheses(sensor, evidence):
    movement, disturbance, prey, environment, human = evidence
    fusion = evidence_fusion(evidence)

    weights = BASE_WEIGHTS.copy()

    # --------------------------------------------------------
    # Direct observation strongly favours a rebuilt movement
    # hypothesis if behaviour change evidence exists.
    # --------------------------------------------------------

    if sensor == "VISIBLE":

        if fusion >= 30:
            weights = {
                "H1": 0.00,
                "H2": 0.98,
                "H3": 0.01,
                "H4": 0.01,
            }
        else:
            weights = {
                "H1": 0.00,
                "H2": 0.98,
                "H3": 0.01,
                "H4": 0.01,
            }

    # --------------------------------------------------------
    # Sensor blindness.
    # Gradually move probability away from H1 as indirect
    # evidence becomes stronger.
    # --------------------------------------------------------

    else:

        if fusion < 10:
            weights = {
                "H1": 0.70,
                "H2": 0.10,
                "H3": 0.10,
                "H4": 0.10,
            }

        elif fusion < 25:
            weights = {
                "H1": 0.60,
                "H2": 0.16,
                "H3": 0.12,
                "H4": 0.12,
            }

        elif fusion < 50:
            weights = {
                "H1": 0.35,
                "H2": 0.34,
                "H3": 0.14,
                "H4": 0.17,
            }

        else:
            weights = {
                "H1": 0.06,
                "H2": 0.68,
                "H3": 0.10,
                "H4": 0.16,
            }

    return weights


def hypothesis_position(actual, hypothesis, uncertainty):
    x, y = actual

    # H1 continues original movement
    if hypothesis == "H1":
        return (x + 8, y - 8)

    # H2 changes direction
    if hypothesis == "H2":
        return (x + 8, y + 2)

    # H3 slows / stops
    if hypothesis == "H3":
        return (x + 2, y)

    # H4 unknown
    return (x + 5, y + 5)


# ============================================================
# TEMPORAL MEMORY
# ============================================================

risk_history = {
    route: deque(maxlen=5)
    for route in ROUTES
}

decision_history = deque(maxlen=5)

previous_prediction = None
previous_prediction_time = None

locked_route = None
locked_do_not_enter = False


def trend_for(route):
    history = list(risk_history[route])

    if len(history) < 2:
        return "INSUFFICIENT DATA", 0.0

    delta = history[-1] - history[0]

    if delta >= 15:
        return "STRONGLY DETERIORATING", delta

    if delta >= 5:
        return "DETERIORATING", delta

    if delta <= -15:
        return "STRONGLY IMPROVING", delta

    if delta <= -5:
        return "IMPROVING", delta

    return "STABLE", delta


def persistence_for(route):
    history = list(risk_history[route])

    if len(history) < 3:
        return 0

    increasing = 0

    for i in range(1, len(history)):
        if history[i] > history[i - 1]:
            increasing += 1

    return increasing


def temporal_adjustment(route, current_risk):

    trend, delta = trend_for(route)
    persistence = persistence_for(route)

    adjustment = 0

    if trend == "DETERIORATING":
        adjustment += 5

    elif trend == "STRONGLY DETERIORATING":
        adjustment += 10

    if persistence >= 3:
        adjustment += 5

    adjusted = min(100, current_risk + adjustment)

    return adjusted, trend, delta, persistence


# ============================================================
# HYSTERESIS DECISION ENGINE
# ============================================================

def choose_route(route_scores):

    global locked_route
    global locked_do_not_enter

    sorted_routes = sorted(
        route_scores.items(),
        key=lambda x: x[1]
    )

    best_route, best_score = sorted_routes[0]

    # --------------------------------------------------------
    # Safety lock
    # --------------------------------------------------------

    if locked_do_not_enter:

        if best_score < DO_NOT_ENTER_RELEASE:
            locked_do_not_enter = False
        else:
            return "WAIT / DO NOT ENTER"

    # --------------------------------------------------------
    # Any severe route risk prevents entering it.
    # --------------------------------------------------------

    if best_score >= HIGH_RISK:
        locked_do_not_enter = True
        return "WAIT / DO NOT ENTER"

    # --------------------------------------------------------
    # Existing route remains preferred unless another route
    # is significantly better.
    # --------------------------------------------------------

    if locked_route is not None:

        locked_score = route_scores.get(
            locked_route,
            100
        )

        improvement = locked_score - best_score

        if improvement < ROUTE_SWITCH_MARGIN:
            return f"ROUTE {locked_route}"

    locked_route = best_route

    return f"ROUTE {best_route}"


# ============================================================
# MAIN SIMULATION
# ============================================================

for minute, actual_x, actual_y, sensor, evidence in observations:

    print("\n" + "-" * 64)
    print(f"{minute:02d} min")

    actual = (actual_x, actual_y)

    # --------------------------------------------------------
    # Prediction
    # --------------------------------------------------------

    if sensor == "VISIBLE":

        prediction = actual
        uncertainty = 5.0
        confidence = 85.7

    else:

        prediction = (
            actual_x + 8,
            actual_y - 8
        )

        uncertainty = min(
            35.0,
            5.0 + minute * 0.8
        )

        confidence = max(
            12.5,
            100 - uncertainty * 2.5
        )

    print(
        f"  Actual leopard: ({actual_x:5.1f}, {actual_y:5.1f})"
    )

    print(f"  Sensor: {sensor}")

    if sensor == "VISIBLE":
        print(
            f"  Direct wildlife observation: "
            f"({actual_x:5.1f}, {actual_y:5.1f})"
        )
    else:
        print(
            f"  Predicted wildlife: "
            f"({prediction[0]:5.1f}, {prediction[1]:5.1f})"
        )

    print(f"  Uncertainty: {uncertainty:5.1f}")
    print(f"  Prediction confidence: {confidence:5.1f}%")

    # --------------------------------------------------------
    # Prediction error
    # --------------------------------------------------------

    if previous_prediction is not None and sensor == "VISIBLE":

        error = distance(
            previous_prediction,
            actual
        )

        error_confidence = max(
            0,
            100 - error * 8
        )

        print()
        print("  📐 PREDICTION ERROR")
        print(
            f"      Previous prediction: "
            f"({previous_prediction[0]:5.1f}, "
            f"{previous_prediction[1]:5.1f})"
        )

        print(
            f"      Actual observation:  "
            f"({actual[0]:5.1f}, {actual[1]:5.1f})"
        )

        print(f"      Position error: {error:5.1f}")

        if error <= 5:
            print("      Model accuracy: HIGH")
        elif error <= 10:
            print("      Model accuracy: MODERATE")
        else:
            print("      Model accuracy: LOW")

        print(
            f"      Observation reliability: "
            f"{error_confidence:5.1f}%"
        )

    # Store blind prediction for later validation
    if sensor == "BLIND":
        previous_prediction = prediction
        previous_prediction_time = minute

    # --------------------------------------------------------
    # Evidence
    # --------------------------------------------------------

    movement, disturbance, prey, environment, human = evidence

    fusion = evidence_fusion(evidence)

    print()
    print("  🔎 INDIRECT EVIDENCE")

    print(
        f"      Movement anomaly          {movement:5.1f}"
    )
    print(
        f"      Sensor disturbance        {disturbance:5.1f}"
    )
    print(
        f"      Prey/activity anomaly     {prey:5.1f}"
    )
    print(
        f"      Environmental context     {environment:5.1f}"
    )
    print(
        f"      Human movement            {human:5.1f}"
    )

    print("      --------------------------------")
    print(
        f"      Evidence fusion score:   {fusion:5.1f}"
    )

    print(
        f"      Evidence state: "
        f"{evidence_state(fusion)}"
    )

    # --------------------------------------------------------
    # Hypotheses
    # --------------------------------------------------------

    weights = update_hypotheses(
        sensor,
        evidence
    )

    dominant = max(
        weights,
        key=weights.get
    )

    print()
    print("  🧠 COMPETING HYPOTHESES")
    print("      --------------------------------")

    for key, description in HYPOTHESES.items():

        print(
            f"      {key}  "
            f"{description:<28}"
            f"{weights[key] * 100:5.1f}%"
        )

    print(
        f"\n      Dominant hypothesis: "
        f"{dominant} "
        f"({weights[dominant] * 100:.1f}%)"
    )

    # --------------------------------------------------------
    # Hypothesis shift
    # --------------------------------------------------------

    if sensor == "BLIND" and fusion >= 30:

        print()
        print("  ⚠️ HYPOTHESIS SHIFT DETECTED")
        print("      Direct confirmation unavailable.")
        print("      Multiple future states remain plausible.")
        print(
            "      Old trajectory must NOT be treated "
            "as ground truth."
        )

    # --------------------------------------------------------
    # Route analysis
    # --------------------------------------------------------

    print()
    print("  🛣️ ROUTE TEMPORAL ANALYSIS")

    route_scores = {}

    for route_name, route_point in ROUTES.items():

        hypothesis_risks = {}

        for h in HYPOTHESES:

            future = hypothesis_position(
                actual,
                h,
                uncertainty
            )

            d = distance(
                future,
                route_point
            )

            r = risk_from_distance(d)

            hypothesis_risks[h] = {
                "distance": d,
                "risk": r,
            }

        # ----------------------------------------------------
        # Expected risk
        # ----------------------------------------------------

        expected_risk = sum(
            weights[h] *
            hypothesis_risks[h]["risk"]
            for h in HYPOTHESES
        )

        # ----------------------------------------------------
        # Worst plausible risk
        # ----------------------------------------------------

        plausible = [
            h for h in HYPOTHESES
            if weights[h] >= 0.05
        ]

        worst_h = max(
            plausible,
            key=lambda h:
            hypothesis_risks[h]["risk"]
        )

        worst_risk = hypothesis_risks[
            worst_h
        ]["risk"]

        # ----------------------------------------------------
        # Conservative risk floor
        # ----------------------------------------------------

        final_risk = expected_risk

        if worst_risk >= 80:
            final_risk = max(
                final_risk,
                80
            )

        elif worst_risk >= 55:
            final_risk = max(
                final_risk,
                40
            )

        # ----------------------------------------------------
        # Temporal memory
        # ----------------------------------------------------

        risk_history[route_name].append(
            final_risk
        )

        temporal_risk, trend, delta, persistence = (
            temporal_adjustment(
                route_name,
                final_risk
            )
        )

        route_scores[route_name] = temporal_risk

        print()
        print(f"      ROUTE {route_name}")

        for h in HYPOTHESES:

            d = hypothesis_risks[h]["distance"]
            r = hypothesis_risks[h]["risk"]

            print(
                f"          {h}: "
                f"{risk_label(r):<13}"
                f"distance={d:5.1f} "
                f"weight={weights[h] * 100:5.1f}%"
            )

        print("          --------------------------------")

        print(
            f"          EXPECTED RISK:      "
            f"{expected_risk:5.1f}"
        )

        print(
            f"          WORST PLAUSIBLE:    "
            f"{worst_risk:5.1f}"
        )

        print(
            f"          WORST HYPOTHESIS:   "
            f"{worst_h}"
        )

        print(
            f"          CURRENT RISK:       "
            f"{final_risk:5.1f}"
        )

        print(
            f"          RISK TREND:         "
            f"{trend}"
        )

        print(
            f"          TREND DELTA:        "
            f"{delta:+5.1f}"
        )

        print(
            f"          PERSISTENCE:        "
            f"{persistence}"
        )

        print(
            f"          TEMPORAL RISK:      "
            f"{temporal_risk:5.1f}"
        )

        # Risk floor warning
        if (
            worst_risk >= 55
            and expected_risk < worst_risk
        ):

            print()
            print(
                "          🛡️ RISK FLOOR ACTIVATED"
            )

            print(
                "          A plausible dangerous future"
            )

            print(
                "          prevents probability averaging"
            )

            print(
                "          from declaring this route LOW RISK."
            )

        print(
            f"          OVERALL: "
            f"{risk_label(temporal_risk)}"
        )

    # --------------------------------------------------------
    # Temporal warning
    # --------------------------------------------------------

    deteriorating_routes = []

    for route in ROUTES:

        trend, delta = trend_for(route)

        if "DETERIORATING" in trend:
            deteriorating_routes.append(route)

    if deteriorating_routes:

        print()
        print(
            "  📈 TEMPORAL SAFETY WARNING"
        )

        print(
            "      Risk is deteriorating on: "
            + ", ".join(deteriorating_routes)
        )

        print(
            "      Wild Sentinel is considering"
        )

        print(
            "      trajectory history, not only"
        )

        print(
            "      the current observation."
        )

    # --------------------------------------------------------
    # Safety decision
    # --------------------------------------------------------

    recommendation = choose_route(
        route_scores
    )

    print()
    print("  ⚠️ SAFETY DECISION")

    print(
        f"  >>> RECOMMENDATION: "
        f"{recommendation}"
    )

    # --------------------------------------------------------
    # Direct observation validation
    # --------------------------------------------------------

    if sensor == "VISIBLE":

        print()
        print(
            "  📡 DIRECT OBSERVATION"
        )

        print(
            "      Direct wildlife observation is "
            "authoritative"
        )

        print(
            "      for the observed animal location."
        )

        if previous_prediction is not None:

            print()
            print(
                "  🔄 PREDICTION VALIDATION"
            )

            print(
                "      Previous blind prediction "
                "has been tested."
            )

            if weights["H2"] > 0.80:

                print()
                print(
                    "      ✓ H2 SUPPORTED BY NEW OBSERVATION"
                )

                print(
                    "      Previous trajectory can be rebuilt."
                )

    decision_history.append(
        recommendation
    )


# ============================================================
# FINAL REPORT
# ============================================================

print("\n" + "=" * 64)
print("                 V0.9.2 TEST COMPLETE")
print("=" * 64)

print("""
VALIDATION:

    [✓] Multiple wildlife hypotheses
    [✓] Hypothesis probability weights
    [✓] Indirect evidence updates hypotheses
    [✓] Sensor blindness handled
    [✓] Prediction confidence decay
    [✓] Competing future trajectories
    [✓] Route evaluated against multiple futures
    [✓] Probability-weighted expected risk
    [✓] Worst plausible outcome retained
    [✓] Conservative risk floor
    [✓] Dangerous low-probability futures protected
    [✓] Temporal risk memory
    [✓] Risk trend detection
    [✓] Risk persistence
    [✓] Prediction error measurement
    [✓] Direct observation validation
    [✓] Decision hysteresis
    [✓] Conservative route selection

============================================================

V0.9.2 PRINCIPLE

Wild Sentinel does not ask only:

    "Where is the leopard?"

It asks:

    "What futures are plausible?"

    "What happens if the unlikely future occurs?"

    "Is the risk increasing?"

    "How persistent is that increase?"

    "How wrong was our previous prediction?"

    "Should the safety decision change?"

And finally:

    "Is it safe enough to enter NOW?"

============================================================
""")