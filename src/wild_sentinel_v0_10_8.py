"""
WILD SENTINEL V0.10.8

TEMPORAL SAFETY VISUALIZATION

V0.10.8 is a visualization layer above V0.10.6.

CORE PRINCIPLE:

    V0.10.6 = SAFETY AUTHORITY
    V0.10.8 = VISUALIZATION ONLY

V0.10.8 does NOT:
    - calculate safety independently
    - modify V0.10.6 decisions
    - rank routes
    - manufacture SAFE states
    - allow one route to influence another

It visualizes the actual MultiRouteAssessment returned by
V0.10.6.evaluate_routes().

Displayed information includes:
    - temporal state
    - decision
    - safety cleared
    - observed/predicted position
    - sensor blindness
    - uncertainty radius
    - prediction error
    - input source
    - historical safety indicators
"""


import tkinter as tk
from tkinter import ttk

import wild_sentinel_v0_10_6 as v106


class WildSentinel108:
    """Temporal visualization layer above V0.10.6."""

    def __init__(self, root):
        self.root = root
        self.root.title("Wild Sentinel V0.10.8 - Temporal Safety Visualization")
        self.root.geometry("1200x800")

        self.engine = v106.WildSentinel106()

        self.assessment = None
        self.routes = []

        self.build_header()
        self.build_controls()
        self.build_timeline()
        self.build_status()

        self.build_scenarios()
        self.show_initial_state()

    # ---------------------------------------------------------
    # GUI
    # ---------------------------------------------------------

    def build_header(self):
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill="x")

        title = ttk.Label(
            header,
            text="WILD SENTINEL V0.10.8",
            font=("Arial", 20, "bold"),
        )
        title.pack(anchor="w")

        subtitle = ttk.Label(
            header,
            text="Temporal Safety Visualization — V0.10.6 remains the safety authority",
            font=("Arial", 11),
        )
        subtitle.pack(anchor="w")

    def build_controls(self):
        frame = ttk.Frame(self.root, padding=(10, 5))
        frame.pack(fill="x")

        self.run_button = ttk.Button(
            frame,
            text="RUN THREE-ROUTE SIMULATION",
            command=self.run_simulation,
        )
        self.run_button.pack(side="left")

    def build_timeline(self):
        frame = ttk.LabelFrame(
            self.root,
            text="Temporal Route Assessment",
            padding=10,
        )
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = (
            "route",
            "time",
            "observed",
            "predicted",
            "uncertainty",
            "visible",
            "state",
            "decision",
            "cleared",
            "source",
        )

        self.tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
        )

        headings = {
            "route": "Route",
            "time": "Time",
            "observed": "Observed Position",
            "predicted": "Predicted Position",
            "uncertainty": "Uncertainty",
            "visible": "Visible",
            "state": "Temporal State",
            "decision": "Decision",
            "cleared": "Safety Cleared",
            "source": "Input Source",
        }

        widths = {
            "route": 70,
            "time": 70,
            "observed": 130,
            "predicted": 130,
            "uncertainty": 100,
            "visible": 80,
            "state": 150,
            "decision": 120,
            "cleared": 110,
            "source": 230,
        }

        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(
                column,
                width=widths[column],
                anchor="center",
            )

        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.tree.yview,
        )

        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def build_status(self):
        frame = ttk.LabelFrame(
            self.root,
            text="Safety History",
            padding=10,
        )
        frame.pack(fill="x", padx=10, pady=5)

        self.status = tk.Text(
            frame,
            height=10,
            wrap="word",
            font=("Consolas", 10),
        )
        self.status.pack(fill="x")

    # ---------------------------------------------------------
    # SCENARIOS
    # ---------------------------------------------------------

    def build_scenarios(self):
        """
        Three independent routes.

        These are intentionally the same scenario definitions
        used by the V0.10.7 visual prototype.
        """

        self.scenarios = [
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

    # ---------------------------------------------------------
    # SIMULATION
    # ---------------------------------------------------------

    def run_simulation(self):
        """Run the real V0.10.6 multi-route evaluation."""

        self.clear_display()

        self.assessment = self.engine.evaluate_routes(
            self.scenarios
        )

        self.routes = self.assessment.routes

        for route_id, route in self.routes.items():
            self.display_route(route)

        self.display_summary()

    # ---------------------------------------------------------
    # DISPLAY
    # ---------------------------------------------------------

    def display_route(self, route):
        for step in route.steps:

            observed = (
                str(step.observed_position)
                if step.observed_position is not None
                else "None"
            )

            predicted = (
                str(step.predicted_position)
                if step.predicted_position is not None
                else "None"
            )

            source = getattr(
                step,
                "input_source",
                "UNKNOWN",
            )

            self.tree.insert(
                "",
                "end",
                values=(
                    route.route_id,
                    f"{step.time_min:.1f}",
                    observed,
                    predicted,
                    f"{step.uncertainty_radius:.2f}",
                    str(step.visible),
                    step.temporal_state,
                    step.decision,
                    str(step.safety_cleared),
                    source,
                ),
            )

    def display_summary(self):
        self.status.delete("1.0", tk.END)

        self.status.insert(
            tk.END,
            "V0.10.8 TEMPORAL SAFETY VISUALIZATION\n"
        )
        self.status.insert(
            tk.END,
            "=====================================\n\n"
        )

        self.status.insert(
            tk.END,
            "SAFETY AUTHORITY\n"
            "V0.10.6 = safety engine\n"
            "V0.10.8 = visualization only\n\n"
        )
        for route_id, route in self.routes.items():
            self.status.insert(tk.END, f"ROUTE {route.route_id}\n")
            self.status.insert(
                tk.END,
                f"  Final state:       {route.temporal_state}\n"
            )
            self.status.insert(
                tk.END,
                f"  Final decision:    {route.decision}\n"
            )
            self.status.insert(
                tk.END,
                f"  Safety cleared:    {route.safety_cleared}\n"
            )
            self.status.insert(
                tk.END,
                f"  Ever blind:        {route.ever_blind}\n"
            )
            self.status.insert(
                tk.END,
                f"  Ever future conflict: {route.ever_future_conflict}\n"
            )
            self.status.insert(
                tk.END,
                f"  Ever window conflict: {route.ever_in_window_conflict}\n"
            )
            self.status.insert(
                tk.END,
                f"  Ever DO_NOT_ENTER: {route.ever_do_not_enter}\n"
            )
            self.status.insert(
                tk.END,
                f"  Maximum uncertainty: {route.maximum_uncertainty:.2f}\n"
            )
            self.status.insert(tk.END, "\n")
        self.status.insert(
            tk.END,
            "ARCHITECTURE PRINCIPLE\n"
            "Prediction is not observation.\n"
            "Sensor blindness is explicitly represented.\n"
            "Uncertainty is displayed, not hidden.\n"
            "The visualization does not create a SAFE route.\n"
        )

    # ---------------------------------------------------------
    # INITIAL / RESET
    # ---------------------------------------------------------

    def show_initial_state(self):
        self.status.insert(
            tk.END,
            "Ready.\n"
            "Press RUN THREE-ROUTE SIMULATION to evaluate "
            "Routes A, B and C through V0.10.6.\n"
        )

    def clear_display(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.status.delete("1.0", tk.END)


def main():
    root = tk.Tk()
    app = WildSentinel108(root)
    root.mainloop()


if __name__ == "__main__":
    main()