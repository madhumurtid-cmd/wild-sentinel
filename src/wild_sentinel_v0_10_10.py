"""
WILD SENTINEL V0.10.10

ROUTE SAFETY EVIDENCE COMPARISON

Purpose:
    Visualization-only layer above V0.10.6.

Architecture:
    V0.10.6 = Safety Authority
    V0.10.10 = Evidence Visualization

V0.10.10 makes the evidence chain explicit:

    OBSERVATION
        ->
    PREDICTION
        ->
    UNCERTAINTY
        ->
    TEMPORAL STATE
        ->
    SAFETY DECISION

CORE PRINCIPLES:

1. V0.10.6 remains the sole safety authority.
2. Prediction is not observation.
3. Sensor blindness is explicitly represented.
4. Uncertainty is visualized, not hidden.
5. V0.10.10 never creates a new safety decision.
6. V0.10.10 never ranks routes.
7. V0.10.10 never converts CAUTION into PROCEED.
8. V0.10.10 never overrides DO_NOT_ENTER.
"""

import tkinter as tk
from tkinter import ttk

import wild_sentinel_v0_10_6 as v106


class WildSentinel1010:
    """Visualization-only route evidence comparison."""

    def __init__(self, root):
        self.root = root
        self.root.title(
            "Wild Sentinel V0.10.10 - Route Safety Evidence"
        )
        self.root.geometry("1250x850")

        self.engine = v106.WildSentinel106()
        self.assessment = None
        self.routes = {}

        self.build_interface()

    # ------------------------------------------------------------------
    # INTERFACE
    # ------------------------------------------------------------------

    def build_interface(self):
        header = tk.Frame(self.root)
        header.pack(fill="x", padx=15, pady=12)

        title = tk.Label(
            header,
            text="WILD SENTINEL V0.10.10",
            font=("Arial", 20, "bold"),
        )
        title.pack()

        subtitle = tk.Label(
            header,
            text="ROUTE SAFETY EVIDENCE COMPARISON",
            font=("Arial", 12),
        )
        subtitle.pack(pady=(3, 0))

        authority = tk.Label(
            self.root,
            text=(
                "SAFETY AUTHORITY: V0.10.6    |    "
                "V0.10.10: VISUALIZATION ONLY"
            ),
            font=("Arial", 10, "bold"),
        )
        authority.pack(pady=(0, 8))

        controls = tk.Frame(self.root)
        controls.pack(fill="x", padx=15, pady=5)

        run_button = tk.Button(
            controls,
            text="RUN THREE-ROUTE EVIDENCE ANALYSIS",
            command=self.run_simulation,
            font=("Arial", 11, "bold"),
            padx=15,
            pady=8,
        )
        run_button.pack(side="left")

        self.status_label = tk.Label(
            controls,
            text="Ready",
            font=("Arial", 10),
        )
        self.status_label.pack(side="left", padx=15)

        # --------------------------------------------------------------
        # Evidence table
        # --------------------------------------------------------------

        table_frame = tk.LabelFrame(
            self.root,
            text="TEMPORAL SAFETY EVIDENCE",
            font=("Arial", 11, "bold"),
        )
        table_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=10,
        )

        columns = (
            "route",
            "time",
            "observed",
            "predicted",
            "uncertainty",
            "visibility",
            "state",
            "decision",
            "cleared",
            "source",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=20,
        )

        headings = {
            "route": "Route",
            "time": "Time",
            "observed": "Observed",
            "predicted": "Predicted",
            "uncertainty": "Uncertainty",
            "visibility": "Visibility",
            "state": "Temporal State",
            "decision": "Decision",
            "cleared": "Safety Cleared",
            "source": "Input Source",
        }

        widths = {
            "route": 60,
            "time": 60,
            "observed": 150,
            "predicted": 150,
            "uncertainty": 90,
            "visibility": 85,
            "state": 150,
            "decision": 125,
            "cleared": 100,
            "source": 220,
        }

        for column in columns:
            self.tree.heading(
                column,
                text=headings[column],
            )
            self.tree.column(
                column,
                width=widths[column],
                anchor="center",
            )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview,
        )

        self.tree.configure(
            yscrollcommand=scrollbar.set
        )

        self.tree.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        # --------------------------------------------------------------
        # Evidence interpretation
        # --------------------------------------------------------------

        interpretation_frame = tk.LabelFrame(
            self.root,
            text="EVIDENCE INTERPRETATION",
            font=("Arial", 11, "bold"),
        )
        interpretation_frame.pack(
            fill="x",
            padx=15,
            pady=(0, 10),
        )

        self.interpretation = tk.Text(
            interpretation_frame,
            height=8,
            wrap="word",
            font=("Consolas", 10),
        )

        self.interpretation.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=8,
        )

        self.interpretation.insert(
            "end",
            "Run the simulation to display the route evidence chain."
        )

    # ------------------------------------------------------------------
    # SCENARIOS
    # ------------------------------------------------------------------

    def create_scenarios(self):
        """
        Three-route scenario.

        Sensor observations stop at t=15 minutes.

        From t=15 onward the engine has no direct observation and
        must represent the animal through prediction and uncertainty.
        """

        return [
            v106.RouteScenario(
                route_id="A",
                observations={
                    0.0: (50.0, 20.0),
                    5.0: (50.0, 25.0),
                    10.0: (50.0, 30.0),
                    15.0: None,
                },
            ),
            v106.RouteScenario(
                route_id="B",
                observations={
                    0.0: (30.0, 20.0),
                    5.0: (30.0, 25.0),
                    10.0: (30.0, 30.0),
                    15.0: None,
                },
            ),
            v106.RouteScenario(
                route_id="C",
                observations={
                    0.0: (70.0, 20.0),
                    5.0: (70.0, 25.0),
                    10.0: (70.0, 30.0),
                    15.0: None,
                },
            ),
        ]

    # ------------------------------------------------------------------
    # FORMATTING
    # ------------------------------------------------------------------

    @staticmethod
    def format_position(position):
        if position is None:
            return "None"

        return (
            f"({position[0]:.1f}, "
            f"{position[1]:.1f})"
        )

    @staticmethod
    def format_value(value):
        if value is None:
            return "None"

        return f"{value:.2f}"

    # ------------------------------------------------------------------
    # SIMULATION
    # ------------------------------------------------------------------

    def run_simulation(self):
        self.tree.delete(*self.tree.get_children())

        self.interpretation.delete(
            "1.0",
            "end",
        )

        scenarios = self.create_scenarios()

        self.assessment = self.engine.evaluate_routes(
            scenarios
        )

        self.routes = self.assessment.routes

        for route_id, route in self.routes.items():
            self.display_route(
                route_id,
                route,
            )

        self.display_interpretation()

        self.status_label.config(
            text="Analysis complete"
        )

    # ------------------------------------------------------------------
    # ROUTE DISPLAY
    # ------------------------------------------------------------------

    def display_route(self, route_id, route):
        for step in route.steps:

            visibility = (
                "VISIBLE"
                if step.visible
                else "BLIND"
            )

            observed = self.format_position(
                step.observed_position
            )

            predicted = self.format_position(
                step.predicted_position
            )

            uncertainty = self.format_value(
                step.uncertainty_radius
            )

            cleared = (
                "YES"
                if step.safety_cleared
                else "NO"
            )

            self.tree.insert(
                "",
                "end",
                values=(
                    route_id,
                    f"{step.time_min:.1f}",
                    observed,
                    predicted,
                    uncertainty,
                    visibility,
                    step.temporal_state,
                    step.decision,
                    cleared,
                    step.input_source,
                ),
            )

    # ------------------------------------------------------------------
    # INTERPRETATION
    # ------------------------------------------------------------------

    def display_interpretation(self):
        lines = []

        lines.append(
            "ARCHITECTURE PRINCIPLE"
        )
        lines.append(
            "Prediction is not observation."
        )
        lines.append(
            ""
        )

        lines.append(
            "EVIDENCE CHAIN"
        )
        lines.append(
            "Observed position -> predicted position -> "
            "uncertainty -> temporal state -> safety decision"
        )
        lines.append(
            ""
        )

        lines.append(
            "ROUTE SUMMARY"
        )

        for route_id, route in self.routes.items():
            lines.append(
                f"Route {route_id}: "
                f"final state={route.temporal_state}, "
                f"decision={route.decision}, "
                f"cleared={route.safety_cleared}, "
                f"maximum uncertainty="
                f"{route.maximum_uncertainty:.2f}"
            )

        lines.append("")
        lines.append(
            "SAFETY INTERPRETATION"
        )

        blind_routes = [
            route_id
            for route_id, route in self.routes.items()
            if route.ever_blind
        ]

        if blind_routes:
            lines.append(
                "Sensor blindness detected on: "
                + ", ".join(blind_routes)
            )

        uncleared_routes = [
            route_id
            for route_id, route in self.routes.items()
            if not route.safety_cleared
        ]

        if uncleared_routes:
            lines.append(
                "Routes not safety-cleared by the "
                "authoritative engine: "
                + ", ".join(uncleared_routes)
            )

        lines.append("")
        lines.append(
            "V0.10.10 does not create or modify "
            "the safety decision."
        )

        lines.append(
            "All safety decisions shown above originate "
            "from V0.10.6."
        )

        self.interpretation.insert(
            "end",
            "\n".join(lines),
        )


def main():
    root = tk.Tk()

    app = WildSentinel1010(root)

    root.mainloop()


if __name__ == "__main__":
    main()