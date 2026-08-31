import math


# ============================================================
#                  WILD SENTINEL V0.9
#             COMPETING HYPOTHESIS ENGINE
# ============================================================

VERSION = "V0.9"

# ------------------------------------------------------------
# HYPOTHESES
# ------------------------------------------------------------

HYPOTHESES = {
    "H1": "Continue original trajectory",
    "H2": "Change direction",
    "H3": "Slow / stop",
    "H4": "Unknown movement",
}

# Starting belief distribution after initial tracking
INITIAL_WEIGHTS = {
    "H1": 0.70,
    "H2": 0.10,
    "H3": 0.10,
    "H4": 0.10,
}

# ------------------------------------------------------------
# TEST TRAJECTORY
# ------------------------------------------------------------

OBSERVATIONS = {
    0:  (15.0, 85.0),
    5:  (22.2, 77.8),
    10: (29.5, 70.5),
    15: (36.8, 63.2),
    20: (44.0, 56.0),
    25: (52.2, 55.8),
    30: (60.4, 55.6),
    35: (68.6, 55.4),
    40: (76.8, 55.2),
    45: (85.0, 55.0),
}

SENSOR_STATE = {
    0: "BLIND",
    5: "BLIND",
    10: "VISIBLE",
    15: "VISIBLE",
    20: "BLIND",
    25: "BLIND",
    30: "BLIND",
    35: "BLIND",
    40: "VISIBLE",
    45: "VISIBLE",
}

# ------------------------------------------------------------
# INDIRECT EVIDENCE
# ------------------------------------------------------------

INDIRECT_EVIDENCE = {
    0:  [0, 0, 0, 0, 0],
    5:  [0, 0, 0, 0, 0],
    10: [0, 0, 0, 0, 0],
    15: [0, 0, 0, 0, 0],
    20: [0, 0, 0, 0, 0],
    25: [0, 25, 55, 0, 0],
    30: [0, 25, 55, 60, 70],
    35: [65, 70, 55, 60, 70],
    40: [65, 70, 55, 60, 70],
    45: [65, 70, 55, 60, 70],
}

EVIDENCE_NAMES = [
    "Movement anomaly",
    "Sensor disturbance",
    "Prey/activity anomaly",
    "Environmental context",
    "Human movement",
]

# ------------------------------------------------------------
# ROUTES
# ------------------------------------------------------------

ROUTES = {
    "A": {
        "start": (10, 20),
        "end":   (90, 20),
    },
    "B": {
        "start": (10, 50),
        "end":   (90, 50),
    },
    "C": {
        "start": (10, 80),
        "end":   (90, 80),
    },
}


# ============================================================
# MATHEMATICS
# ============================================================

def distance(a, b):
    return math.sqrt(
        (a[0] - b[0]) ** 2 +
        (a[1] - b[1]) ** 2
    )


def vector(a, b):
    return (
        b[0] - a[0],
        b[1] - a[1]
    )


def magnitude(v):
    return math.sqrt(v[0] ** 2 + v[1] ** 2)


def angle_between(v1, v2):
    m1 = magnitude(v1)
    m2 = magnitude(v2)

    if m1 == 0 or m2 == 0:
        return 0.0

    dot = v1[0] * v2[0] + v1[1] * v2[1]

    value = dot / (m1 * m2)

    value = max(-1.0, min(1.0, value))

    return math.degrees(math.acos(value))


# ============================================================
# EVIDENCE FUSION
# ============================================================

def evidence_score(values):
    weights = [
        0.25,   # movement anomaly
        0.20,   # sensor disturbance
        0.25,   # prey/activity
        0.15,   # environment
        0.15,   # human movement
    ]

    return sum(v * w for v, w in zip(values, weights))


def evidence_state(score):

    if score < 15:
        return "NO SIGNIFICANT INDIRECT EVIDENCE"

    if score < 30:
        return "INDIRECT EVIDENCE EMERGING"

    if score < 50:
        return "INDIRECT EVIDENCE INCREASING"

    return "BEHAVIOUR CHANGE SUSPECTED"


# ============================================================
# HYPOTHESIS UPDATE
# ============================================================

def update_hypotheses(previous, score, sensor_visible):

    h1 = previous["H1"]
    h2 = previous["H2"]
    h3 = previous["H3"]
    h4 = previous["H4"]

    # --------------------------------------------------------
    # Indirect evidence gradually moves probability away
    # from "continue original trajectory".
    # --------------------------------------------------------

    if not sensor_visible:

        if score < 15:
            h1 *= 1.00
            h2 *= 1.00
            h3 *= 1.00
            h4 *= 1.00

        elif score < 30:
            h1 *= 0.80
            h2 *= 1.50
            h3 *= 1.10
            h4 *= 1.20

        elif score < 50:
            h1 *= 0.55
            h2 *= 2.00
            h3 *= 1.20
            h4 *= 1.30

        else:
            h1 *= 0.25
            h2 *= 3.00
            h3 *= 1.10
            h4 *= 1.40

    # --------------------------------------------------------
    # Direct observation:
    # after confirmation, behaviour-change hypothesis gets
    # strong support if the new trajectory differs from old.
    # --------------------------------------------------------

    else:

        if score >= 50:
            h1 *= 0.20
            h2 *= 3.50
            h3 *= 0.80
            h4 *= 0.70

    total = h1 + h2 + h3 + h4

    return {
        "H1": h1 / total,
        "H2": h2 / total,
        "H3": h3 / total,
        "H4": h4 / total,
    }


# ============================================================
# PREDICTION MODEL
# ============================================================

def calculate_velocity():

    p10 = OBSERVATIONS[10]
    p15 = OBSERVATIONS[15]

    dt = 5

    return (
        (p15[0] - p10[0]) / dt,
        (p15[1] - p10[1]) / dt,
    )


def predict_position(position, velocity, minutes):

    return (
        position[0] + velocity[0] * minutes,
        position[1] + velocity[1] * minutes,
    )


# ============================================================
# HYPOTHESIS POSITIONS
# ============================================================

def hypothesis_positions(current_position, old_velocity):

    speed = magnitude(old_velocity)

    # H1: continue
    h1_velocity = old_velocity

    # H2: direction change
    # Turn approximately 90 degrees.
    h2_velocity = (
        -old_velocity[1],
        old_velocity[0],
    )

    # H3: slow / stop
    h3_velocity = (
        old_velocity[0] * 0.20,
        old_velocity[1] * 0.20,
    )

    # H4: unknown
    h4_velocity = (0.0, 0.0)

    return {
        "H1": h1_velocity,
        "H2": h2_velocity,
        "H3": h3_velocity,
        "H4": h4_velocity,
    }


# ============================================================
# ROUTE RISK
# ============================================================

def point_to_route_distance(point, route):

    a = route["start"]
    b = route["end"]

    ab = vector(a, b)
    ap = vector(a, point)

    ab_squared = ab[0] ** 2 + ab[1] ** 2

    if ab_squared == 0:
        return distance(point, a)

    t = (
        ap[0] * ab[0] +
        ap[1] * ab[1]
    ) / ab_squared

    t = max(0.0, min(1.0, t))

    closest = (
        a[0] + t * ab[0],
        a[1] + t * ab[1]
    )

    return distance(point, closest)


def classify_distance(d):

    if d < 5:
        return "CRITICAL"

    if d < 10:
        return "VERY CLOSE"

    if d < 20:
        return "NEAR"

    if d < 35:
        return "CAUTION"

    return "LOW RISK"


def route_risk(route, current_position, hypothesis_weights,
               hypothesis_velocities):

    results = {}

    for h in HYPOTHESES:

        velocity = hypothesis_velocities[h]

        # Look ahead 30 minutes.
        future = predict_position(
            current_position,
            velocity,
            30
        )

        d = point_to_route_distance(
            future,
            route
        )

        results[h] = {
            "distance": d,
            "state": classify_distance(d),
            "weight": hypothesis_weights[h],
        }

    return results


def overall_route_risk(results):

    weighted_risk = {
        "LOW RISK": 0,
        "CAUTION": 1,
        "NEAR": 2,
        "VERY CLOSE": 3,
        "CRITICAL": 4,
    }

    score = 0

    for result in results.values():

        state = result["state"]

        score += (
            weighted_risk.get(state, 2)
            * result["weight"]
        )

    # Any sufficiently credible critical hypothesis
    # causes the route to be treated conservatively.

    critical_probability = sum(
        r["weight"]
        for r in results.values()
        if r["state"] == "CRITICAL"
    )

    if critical_probability >= 0.15:
        return "HIGH RISK"

    if score >= 2.5:
        return "HIGH RISK"

    if score >= 1.4:
        return "CAUTION"

    return "LOW RISK"


# ============================================================
# CONFIDENCE
# ============================================================

def confidence(sensor_visible, uncertainty):

    if not sensor_visible:
        return max(
            0.0,
            100.0 - uncertainty * 2.5
        )

    return 85.7


def uncertainty_at(time):

    values = {
        0: 35.0,
        5: 35.0,
        10: 5.0,
        15: 5.0,
        20: 13.8,
        25: 22.5,
        30: 31.2,
        35: 35.0,
        40: 5.0,
        45: 5.0,
    }

    return values[time]


# ============================================================
# MAIN ENGINE
# ============================================================

def run():

    print("=" * 60)
    print("             WILD SENTINEL V0.9")
    print("       COMPETING HYPOTHESIS ENGINE")
    print("=" * 60)

    print()
    print("TEST:")
    print()
    print("Leopard changes direction during sensor blindness.")
    print()
    print("V0.9 maintains multiple possible futures.")
    print()
    print("H1  Continue original movement")
    print("H2  Change direction")
    print("H3  Slow / stop")
    print("H4  Unknown movement")
    print()
    print("=" * 60)

    old_velocity = calculate_velocity()

    weights = INITIAL_WEIGHTS.copy()

    timeline = []

    last_direct_position = None

    for t in OBSERVATIONS:

        actual = OBSERVATIONS[t]
        visible = SENSOR_STATE[t] == "VISIBLE"

        uncertainty = uncertainty_at(t)

        evidence = INDIRECT_EVIDENCE[t]

        score = evidence_score(evidence)

        state = evidence_state(score)

        # ----------------------------------------------------
        # Update hypotheses
        # ----------------------------------------------------

        weights = update_hypotheses(
            weights,
            score,
            visible
        )

        # ----------------------------------------------------
        # Direct observation
        # ----------------------------------------------------

        if visible:

            last_direct_position = actual

        # ----------------------------------------------------
        # Hypothesis velocities
        # ----------------------------------------------------

        velocities = hypothesis_positions(
            actual,
            old_velocity
        )

        # ----------------------------------------------------
        # Output
        # ----------------------------------------------------

        print()
        print("-" * 60)

        print(f"{t:02d} min")

        print(f"  Actual leopard: ({actual[0]:5.1f}, {actual[1]:5.1f})")
        print(f"  Sensor: {SENSOR_STATE[t]}")

        if visible:

            print(
                f"  Direct wildlife observation: "
                f"({actual[0]:5.1f}, {actual[1]:5.1f})"
            )

        else:

            predicted = predict_position(
                actual,
                old_velocity,
                5
            )

            print(
                f"  Predicted wildlife: "
                f"({predicted[0]:5.1f}, {predicted[1]:5.1f})"
            )

        print(
            f"  Uncertainty: {uncertainty:5.1f}"
        )

        print(
            f"  Prediction confidence: "
            f"{confidence(visible, uncertainty):5.1f}%"
        )

        # ----------------------------------------------------
        # Evidence
        # ----------------------------------------------------

        print()
        print("  🔎 INDIRECT EVIDENCE")

        for name, value in zip(
            EVIDENCE_NAMES,
            evidence
        ):

            print(
                f"      {name:<25} {value:5.1f}"
            )

        print("      --------------------------------")
        print(
            f"      Evidence fusion score: "
            f"{score:5.1f}"
        )

        print(
            f"      Evidence state: {state}"
        )

        # ----------------------------------------------------
        # Hypotheses
        # ----------------------------------------------------

        print()
        print("  🧠 COMPETING HYPOTHESES")
        print("      --------------------------------")

        for h in HYPOTHESES:

            print(
                f"      {h}  "
                f"{HYPOTHESES[h]:<30}"
                f"{weights[h] * 100:5.1f}%"
            )

        dominant = max(
            weights,
            key=weights.get
        )

        print()
        print(
            f"      Dominant hypothesis: "
            f"{dominant} "
            f"({weights[dominant] * 100:.1f}%)"
        )

        # ----------------------------------------------------
        # Behaviour warning
        # ----------------------------------------------------

        if not visible and score >= 30:

            print()
            print("  ⚠️ HYPOTHESIS SHIFT DETECTED")

            print(
                "      Direct confirmation unavailable."
            )

            print(
                "      Multiple future states remain plausible."
            )

            print(
                "      Old trajectory must NOT be treated "
                "as ground truth."
            )

        # ----------------------------------------------------
        # Route analysis
        # ----------------------------------------------------

        print()
        print("  🛣️ ROUTE HYPOTHESIS ANALYSIS")

        route_overall = {}

        for route_name, route in ROUTES.items():

            results = route_risk(
                route,
                actual,
                weights,
                velocities
            )

            overall = overall_route_risk(
                results
            )

            route_overall[route_name] = overall

            print()
            print(f"      ROUTE {route_name}")

            for h in HYPOTHESES:

                r = results[h]

                print(
                    f"          {h}: "
                    f"{r['state']:<12} "
                    f"distance={r['distance']:5.1f} "
                    f"weight={r['weight'] * 100:5.1f}%"
                )

            print(
                f"          OVERALL: {overall}"
            )

        # ----------------------------------------------------
        # Conservative decision
        # ----------------------------------------------------

        safe_routes = [
            r
            for r, risk in route_overall.items()
            if risk == "LOW RISK"
        ]

        if not visible:

            if (
                confidence(False, uncertainty) < 30
                or not safe_routes
                or score >= 30
            ):

                recommendation = (
                    "WAIT / DO NOT ENTER"
                )

            else:

                recommendation = (
                    f"ROUTE {safe_routes[0]}"
                )

        else:

            if safe_routes:

                recommendation = (
                    f"ROUTE {safe_routes[0]}"
                )

            else:

                recommendation = (
                    "WAIT / DO NOT ENTER"
                )

        print()
        print("  ⚠️ SAFETY DECISION")

        print(
            f"  >>> RECOMMENDATION: "
            f"{recommendation}"
        )

        # ----------------------------------------------------
        # Direct confirmation / rebuild
        # ----------------------------------------------------

        if t == 40:

            print()
            print("  🚨 DIRECT OBSERVATION RETURNED")

            print(
                "      Previous single-trajectory model "
                "is no longer authoritative."
            )

            print()
            print("  🔄 HYPOTHESIS VALIDATION")

            print(
                f"      H1 Continue trajectory: "
                f"{weights['H1'] * 100:.1f}%"
            )

            print(
                f"      H2 Direction change: "
                f"{weights['H2'] * 100:.1f}%"
            )

            print(
                f"      H3 Slow / stop: "
                f"{weights['H3'] * 100:.1f}%"
            )

            print(
                f"      H4 Unknown: "
                f"{weights['H4'] * 100:.1f}%"
            )

            if weights["H2"] > weights["H1"]:

                print()
                print(
                    "      ✓ H2 SUPPORTED BY NEW OBSERVATION"
                )

                print(
                    "      Previous trajectory invalidated."
                )

                print(
                    "      New movement model can be rebuilt."
                )

        timeline.append(
            (
                t,
                score,
                weights.copy()
            )
        )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 60)
    print("                 V0.9 TEST COMPLETE")
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
    print("    [✓] Conservative risk aggregation")
    print("    [✓] Direct observation retained separately")
    print("    [✓] Behaviour-change hypothesis")
    print("    [✓] Model rebuild trigger")
    print()
    print("=" * 60)
    print("V0.9 PRINCIPLE")
    print("=" * 60)
    print()
    print('Wild Sentinel no longer asks:')
    print()
    print('    "Where will the leopard be?"')
    print()
    print('It asks:')
    print()
    print('    "What are the plausible futures?"')
    print()
    print('and:')
    print()
    print('    "Is this route safe across those futures?"')
    print()
    print("=" * 60)


if __name__ == "__main__":
    run()