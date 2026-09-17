"""
WILD SENTINEL V0.10.11

ROUTE CONFLICT VISUALIZATION

Purpose:
    Visualization-only layer above V0.10.6.

Architecture:
    V0.10.6  = Safety Authority
    V0.10.11 = Spatial / temporal conflict visualization

CORE PRINCIPLES:

1. V0.10.6 remains the sole safety authority.
2. Prediction is not observation.
3. Sensor blindness is explicitly represented.
4. Uncertainty is visualized.
5. Route geometry is visualized.
6. V0.10.11 does not create a new safety decision.
7. V0.10.11 does not rank routes.
8. V0.10.11 does not override V0.10.6.
"""

import math
import tkinter as tk
from tkinter import ttk

import wild_sentinel_v0_10_6 as v106


class WildSentinel1011:
    """Visualization-only spatial conflict layer."""

    def __init__(self, root):
        self.root = root
        self.root.title(
            "Wild Sentinel V0.10.11 - Route Conflict Visualization"
        )
        self.root.geometry("1250x900")

        self.engine = v106.WildSentinel106()
        self.assessment = None
        self.routes = {}

        self.canvas_width = 850
        self.canvas_height = 480

        self.build_interface()

    # ------------------------------------------------------------------
    # INTERFACE
    # ------------------------------------------------------------------

    def build_interface(self):
        header = tk.Frame(self.root)
        header.pack(fill="x", padx=15, pady=10)

        tk.Label(
            header,
            text="WILD SENTINEL V0.10.11",
            font=("Arial", 20, "bold"),
        ).pack()

        tk.Label(
            header,
            text="ROUTE CONFLICT VISUALIZATION",
            font=("Arial", 12),
        ).pack(pady=(3, 0))

        tk.Label(
            self.root,
            text=(
                "SAFETY AUTHORITY: V0.10.6    |    "
                "V0.10.11: VISUALIZATION ONLY"
            ),
            font=("Arial", 10, "bold"),
        ).pack(pady=(0, 8))

        controls = tk.Frame(self.root)
        controls.pack(fill="x", padx=15, pady=5)

        tk.Button(
            controls,
            text="RUN CONFLICT VISUALIZATION",
            command=self.run_simulation,
            font=("Arial", 11, "bold"),
            padx=15,
            pady=8,
        ).pack(side="left")

        self.status_label = tk.Label(
            controls,
            text="Ready",
            font=("Arial", 10),
        )
        self.status_label.pack(side="left", padx=15)

        # --------------------------------------------------------------
        # Spatial canvas
        # --------------------------------------------------------------

        canvas_frame = tk.LabelFrame(
            self.root,
            text="SPATIAL ROUTE / UNCERTAINTY VIEW",
            font=("Arial", 11, "bold"),
        )
        canvas_frame.pack(
            fill="x",
            padx=15,
            pady=8,
        )

        self.canvas = tk.Canvas(
            canvas_frame,
            width=self.canvas_width,
            height=self.canvas_height,
            bg="white",
            highlightthickness=1,
        )
        self.canvas.pack(
            padx=10,
            pady=10,
        )

        # --------------------------------------------------------------
        # Temporal evidence table
        # --------------------------------------------------------------

        table_frame = tk.LabelFrame(
            self.root,
            text="TEMPORAL CONFLICT EVIDENCE",
            font=("Arial", 11, "bold"),
        )
        table_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=8,
        )

        columns = (
            "route",
            "time",
            "observed",
            "predicted",
            "uncertainty",
            "state",
            "decision",
            "cleared",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=10,
        )

        headings = {
            "route": "Route",
            "time": "Time",
            "observed": "Observed",
            "predicted": "Predicted",
            "uncertainty": "Uncertainty",
            "state": "Temporal State",
            "decision": "Decision",
            "cleared": "Safety Cleared",
        }

        widths = {
            "route": 60,
            "time": 65,
            "observed": 155,
            "predicted": 155,
            "uncertainty": 95,
            "state": 155,
            "decision": 125,
            "cleared": 105,
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
        # Interpretation
        # --------------------------------------------------------------

        interpretation_frame = tk.LabelFrame(
            self.root,
            text="CONFLICT INTERPRETATION",
            font=("Arial", 11, "bold"),
        )
        interpretation_frame.pack(
            fill="x",
            padx=15,
            pady=(0, 10),
        )

        self.interpretation = tk.Text(
            interpretation_frame,
            height=7,
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
            "Run the visualization to display route geometry "
            "and predicted uncertainty."
        )

    # ------------------------------------------------------------------
    # SCENARIOS
    # ------------------------------------------------------------------

    def create_scenarios(self):
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

    # ------------------------------------------------------------------
    # SIMULATION
    # ------------------------------------------------------------------

    def run_simulation(self):
        self.tree.delete(*self.tree.get_children())
        self.canvas.delete("all")

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
            self.display_temporal_data(
                route_id,
                route,
            )

        self.draw_spatial_view()
        self.display_interpretation()

        self.status_label.config(
            text="Visualization complete"
        )

    # ------------------------------------------------------------------
    # TEMPORAL TABLE
    # ------------------------------------------------------------------

    def display_temporal_data(self, route_id, route):
        for step in route.steps:
            self.tree.insert(
                "",
                "end",
                values=(
                    route_id,
                    f"{step.time_min:.1f}",
                    self.format_position(
                        step.observed_position
                    ),
                    self.format_position(
                        step.predicted_position
                    ),
                    f"{step.uncertainty_radius:.2f}",
                    step.temporal_state,
                    step.decision,
                    (
                        "YES"
                        if step.safety_cleared
                        else "NO"
                    ),
                ),
            )

    # ------------------------------------------------------------------
    # COORDINATE TRANSFORMATION
    # ------------------------------------------------------------------

    def world_to_canvas(
        self,
        x,
        y,
        min_x=10.0,
        max_x=90.0,
        min_y=10.0,
        max_y=90.0,
    ):
        margin = 50

        px = (
            margin
            + (
                (x - min_x)
                / (max_x - min_x)
            )
            * (
                self.canvas_width
                - 2 * margin
            )
        )

        py = (
            self.canvas_height
            - margin
            - (
                (y - min_y)
                / (max_y - min_y)
            )
            * (
                self.canvas_height
                - 2 * margin
            )
        )

        return px, py

    # ------------------------------------------------------------------
    # ROUTE DRAWING
    # ------------------------------------------------------------------

    def draw_route(
        self,
        route_id,
        y_value,
    ):
        x1, y1 = self.world_to_canvas(
            10,
            y_value,
        )

        x2, y2 = self.world_to_canvas(
            90,
            y_value,
        )

        self.canvas.create_line(
            x1,
            y1,
            x2,
            y2,
            width=5,
        )

        self.canvas.create_text(
            x1 - 25,
            y1,
            text=route_id,
            font=("Arial", 11, "bold"),
        )

    # ------------------------------------------------------------------
    # UNCERTAINTY ENVELOPE
    # ------------------------------------------------------------------

    def draw_uncertainty_circle(
        self,
        position,
        radius,
        label,
    ):
        if position is None:
            return

        x, y = self.world_to_canvas(
            position[0],
            position[1],
        )

        scale_x = (
            self.canvas_width - 100
        ) / 80.0

        scale_y = (
            self.canvas_height - 100
        ) / 80.0

        radius_px = radius * min(
            scale_x,
            scale_y,
        )

        self.canvas.create_oval(
            x - radius_px,
            y - radius_px,
            x + radius_px,
            y + radius_px,
            outline="gray",
            dash=(5, 3),
            width=2,
        )

        self.canvas.create_text(
            x,
            y - radius_px - 8,
            text=label,
            font=("Arial", 8),
        )

    # ------------------------------------------------------------------
    # SPATIAL VIEW
    # ------------------------------------------------------------------

    def draw_spatial_view(self):
        self.canvas.create_text(
            self.canvas_width / 2,
            20,
            text=(
                "WILDLIFE PREDICTION / ROUTE SAFETY ENVELOPES"
            ),
            font=("Arial", 12, "bold"),
        )

        # Route positions correspond to the scenario definitions.
        route_y = {
            "A": 50.0,
            "B": 30.0,
            "C": 70.0,
        }

        for route_id, y_value in route_y.items():
            self.draw_route(
                route_id,
                y_value,
            )

        # Draw observations and predictions using the actual
        # V0.10.6 step data.
        for route_id, route in self.routes.items():

            for step in route.steps:

                position = step.predicted_position

                if position is None:
                    continue

                # Only show the latest temporal step for clarity.
                if step.time_min != route.final_step.time_min:
                    continue

                self.draw_uncertainty_circle(
                    position,
                    step.uncertainty_radius,
                    (
                        f"{route_id} "
                        f"t={step.time_min:.0f}"
                    ),
                )

                px, py = self.world_to_canvas(
                    position[0],
                    position[1],
                )

                self.canvas.create_oval(
                    px - 5,
                    py - 5,
                    px + 5,
                    py + 5,
                    fill="black",
                )

                self.canvas.create_text(
                    px,
                    py + 15,
                    text="PREDICTED",
                    font=("Arial", 8),
                )

                if step.observed_position is not None:
                    ox, oy = self.world_to_canvas(
                        step.observed_position[0],
                        step.observed_position[1],
                    )

                    self.canvas.create_oval(
                        ox - 5,
                        oy - 5,
                        ox + 5,
                        oy + 5,
                        outline="black",
                        width=2,
                    )

                    self.canvas.create_text(
                        ox,
                        oy - 15,
                        text="OBSERVED",
                        font=("Arial", 8),
                    )

        # Sensor blindness marker.
        blind_times = []

        for route in self.routes.values():
            for step in route.steps:
                if step.blind:
                    blind_times.append(
                        step.time_min
                    )

        if blind_times:
            blind_time = min(blind_times)

            marker_x = (
                50
                + (
                    blind_time / 30.0
                )
                * (
                    self.canvas_width - 100
                )
            )

            self.canvas.create_text(
                marker_x,
                self.canvas_height - 18,
                text=(
                    f"SENSOR BLIND FROM t={blind_time:.0f}"
                ),
                font=("Arial", 9, "bold"),
            )

    # ------------------------------------------------------------------
    # INTERPRETATION
    # ------------------------------------------------------------------

    def display_interpretation(self):
        lines = []

        lines.append(
            "WHAT THIS VIEW SHOWS"
        )
        lines.append(
            "The route corridors are displayed together with "
            "the latest predicted wildlife position and its "
            "uncertainty envelope."
        )
        lines.append("")

        lines.append(
            "IMPORTANT DISTINCTION"
        )
        lines.append(
            "A predicted position is not an observed position."
        )
        lines.append(
            "During sensor blindness, the envelope represents "
            "uncertainty around the prediction."
        )
        lines.append("")

        lines.append(
            "AUTHORITATIVE SAFETY RESULT"
        )

        for route_id, route in self.routes.items():
            lines.append(
                f"Route {route_id}: "
                f"state={route.temporal_state}, "
                f"decision={route.decision}, "
                f"cleared={route.safety_cleared}, "
                f"uncertainty="
                f"{route.maximum_uncertainty:.2f}"
            )

        lines.append("")
        lines.append(
            "V0.10.11 visualizes spatial evidence only."
        )
        lines.append(
            "It does not create, rank, replace or override "
            "the V0.10.6 safety decision."
        )

        self.interpretation.insert(
            "end",
            "\n".join(lines),
        )


def main():
    root = tk.Tk()

    WildSentinel1011(root)

    root.mainloop()


if __name__ == "__main__":
    main()