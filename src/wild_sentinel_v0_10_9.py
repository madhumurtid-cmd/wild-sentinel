"""
WILD SENTINEL V0.10.9

TEMPORAL UNCERTAINTY VISUALIZATION

V0.10.9 is a visualization layer above V0.10.6.

CORE PRINCIPLE:

    V0.10.6 = SAFETY AUTHORITY
    V0.10.9 = VISUALIZATION ONLY

V0.10.9 does NOT:
    - calculate safety independently
    - modify V0.10.6 decisions
    - rank routes
    - manufacture SAFE states
    - alter uncertainty values
    - allow one route to influence another

It visualizes uncertainty over time using the actual
RouteAssessment.steps returned by V0.10.6.

The visualization explicitly distinguishes:

    OBSERVATION
        from
    PREDICTION DURING SENSOR BLINDNESS

and shows uncertainty growth as recorded by V0.10.6.
"""

import tkinter as tk
from tkinter import ttk

import wild_sentinel_v0_10_6 as v106


class WildSentinel109:
    """Temporal uncertainty visualization above V0.10.6."""

    def __init__(self, root):
        self.root = root
        self.root.title(
            "Wild Sentinel V0.10.9 - Temporal Uncertainty Visualization"
        )
        self.root.geometry("1250x850")

        self.engine = v106.WildSentinel106()

        self.assessment = None
        self.routes = {}

        self.build_header()
        self.build_controls()
        self.build_uncertainty_panel()
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

        ttk.Label(
            header,
            text="WILD SENTINEL V0.10.9",
            font=("Arial", 20, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            header,
            text=(
                "Temporal Uncertainty Visualization — "
                "V0.10.6 remains the safety authority"
            ),
            font=("Arial", 11),
        ).pack(anchor="w")

    def build_controls(self):
        frame = ttk.Frame(self.root, padding=(10, 5))
        frame.pack(fill="x")

        ttk.Button(
            frame,
            text="RUN THREE-ROUTE SIMULATION",
            command=self.run_simulation,
        ).pack(side="left")

    def build_uncertainty_panel(self):
        frame = ttk.LabelFrame(
            self.root,
            text="Uncertainty Over Time",
            padding=10,
        )
        frame.pack(fill="x", padx=10, pady=5)

        self.canvas = tk.Canvas(
            frame,
            height=250,
            background="white",
        )
        self.canvas.pack(fill="x")

    def build_timeline(self):
        frame = ttk.LabelFrame(
            self.root,
            text="Temporal Assessment",
            padding=10,
        )
        frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5,
        )

        columns = (
            "route",
            "time",
            "input",
            "observed",
            "predicted",
            "uncertainty",
            "state",
            "decision",
        )

        self.tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
        )

        headings = {
            "route": "Route",
            "time": "Time",
            "input": "Input",
            "observed": "Observed",
            "predicted": "Predicted",
            "uncertainty": "Uncertainty",
            "state": "State",
            "decision": "Decision",
        }

        widths = {
            "route": 70,
            "time": 70,
            "input": 230,
            "observed": 140,
            "predicted": 140,
            "uncertainty": 110,
            "state": 150,
            "decision": 120,
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
            frame,
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

    def build_status(self):
        frame = ttk.LabelFrame(
            self.root,
            text="Safety Interpretation",
            padding=10,
        )
        frame.pack(
            fill="x",
            padx=10,
            pady=5,
        )

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
        self.clear_display()

        self.assessment = self.engine.evaluate_routes(
            self.scenarios
        )

        self.routes = self.assessment.routes

        for route_id, route in self.routes.items():
            self.display_route(route)

        self.draw_uncertainty()

        self.display_summary()

    # ---------------------------------------------------------
    # TIMELINE
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
                    source,
                    observed,
                    predicted,
                    f"{step.uncertainty_radius:.2f}",
                    step.temporal_state,
                    step.decision,
                ),
            )

    # ---------------------------------------------------------
    # UNCERTAINTY VISUALIZATION
    # ---------------------------------------------------------

    def draw_uncertainty(self):
        self.canvas.delete("all")

        if not self.routes:
            return

        width = max(
            self.canvas.winfo_width(),
            1000,
        )
        height = 250

        left = 70
        right = width - 40
        top = 30
        bottom = height - 45

        all_steps = []

        for route in self.routes.values():
            all_steps.extend(route.steps)

        if not all_steps:
            return

        max_time = max(
            step.time_min
            for step in all_steps
        )

        max_uncertainty = max(
            step.uncertainty_radius
            for step in all_steps
        )

        if max_time <= 0:
            max_time = 1.0

        if max_uncertainty <= 0:
            max_uncertainty = 1.0

        # Axes
        self.canvas.create_line(
            left,
            bottom,
            right,
            bottom,
            width=2,
        )

        self.canvas.create_line(
            left,
            top,
            left,
            bottom,
            width=2,
        )

        self.canvas.create_text(
            15,
            top,
            text="Uncertainty",
            anchor="w",
        )

        self.canvas.create_text(
            right,
            height - 15,
            text="Time (minutes)",
            anchor="e",
        )

        # Scale labels
        self.canvas.create_text(
            left - 10,
            bottom,
            text="0",
            anchor="e",
        )

        self.canvas.create_text(
            left - 10,
            top,
            text=f"{max_uncertainty:.2f}",
            anchor="e",
        )

        # Route lines
        for route_id, route in self.routes.items():

            points = []

            for step in route.steps:
                x = (
                    left
                    + (
                        step.time_min
                        / max_time
                    )
                    * (right - left)
                )

                y = (
                    bottom
                    - (
                        step.uncertainty_radius
                        / max_uncertainty
                    )
                    * (bottom - top)
                )

                points.append((x, y))

            if len(points) >= 2:
                for i in range(len(points) - 1):
                    self.canvas.create_line(
                        points[i][0],
                        points[i][1],
                        points[i + 1][0],
                        points[i + 1][1],
                        width=3,
                    )

            for x, y in points:
                self.canvas.create_oval(
                    x - 4,
                    y - 4,
                    x + 4,
                    y + 4,
                )

            if points:
                lx, ly = points[-1]

                self.canvas.create_text(
                    lx + 8,
                    ly,
                    text=f"Route {route_id}",
                    anchor="w",
                )

        # Blind-period marker based on actual steps.
        blind_times = []

        for route in self.routes.values():
            for step in route.steps:
                if step.blind:
                    blind_times.append(step.time_min)

        if blind_times:
            blind_start = min(blind_times)

            x = (
                left
                + (
                    blind_start
                    / max_time
                )
                * (right - left)
            )

            self.canvas.create_line(
                x,
                top,
                x,
                bottom,
                dash=(6, 4),
                width=2,
            )

            self.canvas.create_text(
                x + 5,
                top + 5,
                text="SENSOR BLIND",
                anchor="nw",
            )

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    def display_summary(self):
        self.status.delete(
            "1.0",
            tk.END,
        )

        self.status.insert(
            tk.END,
            "V0.10.9 TEMPORAL UNCERTAINTY VISUALIZATION\n"
        )
        self.status.insert(
            tk.END,
            "============================================\n\n"
        )

        self.status.insert(
            tk.END,
            "SAFETY AUTHORITY\n"
            "V0.10.6 = safety engine\n"
            "V0.10.9 = visualization only\n\n"
        )

        for route_id, route in self.routes.items():

            self.status.insert(
                tk.END,
                f"ROUTE {route.route_id}\n"
            )

            self.status.insert(
                tk.END,
                f"  Final state:          "
                f"{route.temporal_state}\n"
            )

            self.status.insert(
                tk.END,
                f"  Final decision:       "
                f"{route.decision}\n"
            )

            self.status.insert(
                tk.END,
                f"  Safety cleared:       "
                f"{route.safety_cleared}\n"
            )

            self.status.insert(
                tk.END,
                f"  Ever blind:           "
                f"{route.ever_blind}\n"
            )

            self.status.insert(
                tk.END,
                f"  Maximum uncertainty:  "
                f"{route.maximum_uncertainty:.2f}\n"
            )

            self.status.insert(
                tk.END,
                "\n"
            )

        self.status.insert(
            tk.END,
            "TEMPORAL PRINCIPLE\n"
            "Observed positions have zero uncertainty in this "
            "scenario.\n"
            "During sensor blindness, observation becomes None.\n"
            "The engine uses prediction from the last observation "
            "plus motion.\n"
            "Uncertainty is explicitly represented rather than "
            "hidden.\n"
        )

    # ---------------------------------------------------------
    # RESET
    # ---------------------------------------------------------

    def show_initial_state(self):
        self.status.insert(
            tk.END,
            "Ready.\n"
            "Press RUN THREE-ROUTE SIMULATION.\n"
        )

    def clear_display(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.canvas.delete("all")

        self.status.delete(
            "1.0",
            tk.END,
        )


def main():
    root = tk.Tk()
    app = WildSentinel109(root)
    root.mainloop()


if __name__ == "__main__":
    main()