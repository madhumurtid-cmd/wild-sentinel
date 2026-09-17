"""
WILD SENTINEL V0.10.12

HOUSE -> SCHOOL SAFETY SCENARIO

Purpose:
    Real-world community safety presentation layer.

Architecture:
    V0.10.6  = Safety Authority
    V0.10.12 = Scenario Presentation

Scenario:
    A person travels from HOUSE to SCHOOL using one of
    three possible routes while wildlife movement is
    being monitored.

CORE PRINCIPLES:

1. V0.10.6 remains the sole safety authority.
2. Prediction is not observation.
3. Sensor blindness is explicitly represented.
4. Uncertainty is visible.
5. Safety decisions are inherited from V0.10.6.
6. V0.10.12 does not rank routes.
7. V0.10.12 does not create a new safety decision.
8. V0.10.12 does not override the safety engine.
"""

import tkinter as tk
from tkinter import ttk

import wild_sentinel_v0_10_6 as v106


class WildSentinel1012:
    """House-to-school community safety presentation."""

    def __init__(self, root):
        self.root = root

        self.root.title(
            "Wild Sentinel V0.10.12 - House to School Safety"
        )

        self.root.geometry("1250x900")

        self.engine = v106.WildSentinel106()

        self.assessment = None
        self.routes = {}

        self.canvas_width = 850
        self.canvas_height = 500

        self.build_interface()

    # ================================================================
    # INTERFACE
    # ================================================================

    def build_interface(self):
        header = tk.Frame(self.root)
        header.pack(
            fill="x",
            padx=15,
            pady=10,
        )

        tk.Label(
            header,
            text="WILD SENTINEL",
            font=("Arial", 22, "bold"),
        ).pack()

        tk.Label(
            header,
            text="HOUSE → SCHOOL SAFETY SCENARIO",
            font=("Arial", 14, "bold"),
        ).pack(
            pady=(3, 0)
        )

        tk.Label(
            self.root,
            text=(
                "V0.10.6 = SAFETY AUTHORITY    |    "
                "V0.10.12 = COMMUNITY SCENARIO PRESENTATION"
            ),
            font=("Arial", 10, "bold"),
        ).pack(
            pady=(0, 8)
        )

        controls = tk.Frame(self.root)
        controls.pack(
            fill="x",
            padx=15,
            pady=5,
        )

        tk.Button(
            controls,
            text="RUN HOUSE → SCHOOL SCENARIO",
            command=self.run_scenario,
            font=("Arial", 11, "bold"),
            padx=15,
            pady=8,
        ).pack(
            side="left"
        )

        self.status_label = tk.Label(
            controls,
            text="Ready",
            font=("Arial", 10),
        )

        self.status_label.pack(
            side="left",
            padx=15,
        )

        # ------------------------------------------------------------
        # MAIN MAP
        # ------------------------------------------------------------

        map_frame = tk.LabelFrame(
            self.root,
            text="COMMUNITY SAFETY MAP",
            font=("Arial", 11, "bold"),
        )

        map_frame.pack(
            fill="x",
            padx=15,
            pady=8,
        )

        self.canvas = tk.Canvas(
            map_frame,
            width=self.canvas_width,
            height=self.canvas_height,
            bg="white",
            highlightthickness=1,
        )

        self.canvas.pack(
            padx=10,
            pady=10,
        )

        # ------------------------------------------------------------
        # STATUS PANEL
        # ------------------------------------------------------------

        status_frame = tk.LabelFrame(
            self.root,
            text="LIVE SAFETY STATUS",
            font=("Arial", 11, "bold"),
        )

        status_frame.pack(
            fill="x",
            padx=15,
            pady=8,
        )

        self.status_tree = ttk.Treeview(
            status_frame,
            columns=(
                "route",
                "state",
                "decision",
                "cleared",
                "uncertainty",
                "sensor",
            ),
            show="headings",
            height=4,
        )

        headings = {
            "route": "Route",
            "state": "Temporal State",
            "decision": "Decision",
            "cleared": "Safety Cleared",
            "uncertainty": "Uncertainty",
            "sensor": "Sensor",
        }

        widths = {
            "route": 80,
            "state": 180,
            "decision": 150,
            "cleared": 130,
            "uncertainty": 130,
            "sensor": 150,
        }

        for column in headings:
            self.status_tree.heading(
                column,
                text=headings[column],
            )

            self.status_tree.column(
                column,
                width=widths[column],
                anchor="center",
            )

        self.status_tree.pack(
            fill="x",
            padx=5,
            pady=5,
        )

        # ------------------------------------------------------------
        # MESSAGE
        # ------------------------------------------------------------

        message_frame = tk.LabelFrame(
            self.root,
            text="COMMUNITY SAFETY MESSAGE",
            font=("Arial", 11, "bold"),
        )

        message_frame.pack(
            fill="x",
            padx=15,
            pady=(0, 10),
        )

        self.message = tk.Text(
            message_frame,
            height=6,
            wrap="word",
            font=("Consolas", 11),
        )

        self.message.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=8,
        )

        self.message.insert(
            "end",
            (
                "Run the scenario to display the current "
                "wildlife movement and route safety status."
            )
        )

    # ================================================================
    # SCENARIOS
    # ================================================================

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

    # ================================================================
    # RUN
    # ================================================================

    def run_scenario(self):
        self.canvas.delete("all")

        for item in self.status_tree.get_children():
            self.status_tree.delete(item)

        self.message.delete(
            "1.0",
            "end",
        )

        scenarios = self.create_scenarios()

        self.assessment = self.engine.evaluate_routes(
            scenarios
        )

        self.routes = self.assessment.routes

        self.draw_map()

        self.display_status()

        self.display_message()

        self.status_label.config(
            text="Scenario running from latest engine assessment"
        )

    # ================================================================
    # COORDINATE SYSTEM
    # ================================================================

    def world_to_canvas(
        self,
        x,
        y,
        min_x=0.0,
        max_x=100.0,
        min_y=0.0,
        max_y=100.0,
    ):
        margin = 55

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

    # ================================================================
    # MAP
    # ================================================================

    def draw_map(self):
        self.canvas.create_text(
            self.canvas_width / 2,
            20,
            text="HOUSE → SCHOOL",
            font=("Arial", 13, "bold"),
        )

        # ------------------------------------------------------------
        # House
        # ------------------------------------------------------------

        hx, hy = self.world_to_canvas(
            10,
            50,
        )

        self.canvas.create_rectangle(
            hx - 18,
            hy - 18,
            hx + 18,
            hy + 18,
            outline="black",
            width=3,
        )

        self.canvas.create_text(
            hx,
            hy - 32,
            text="HOUSE",
            font=("Arial", 11, "bold"),
        )

        # ------------------------------------------------------------
        # School
        # ------------------------------------------------------------

        sx, sy = self.world_to_canvas(
            90,
            50,
        )

        self.canvas.create_rectangle(
            sx - 20,
            sy - 20,
            sx + 20,
            sy + 20,
            outline="black",
            width=3,
        )

        self.canvas.create_text(
            sx,
            sy - 35,
            text="SCHOOL",
            font=("Arial", 11, "bold"),
        )

        # ------------------------------------------------------------
        # Routes
        # ------------------------------------------------------------

        route_y = {
            "A": 70.0,
            "B": 50.0,
            "C": 30.0,
        }

        for route_id, y_value in route_y.items():
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

        # ------------------------------------------------------------
        # Latest wildlife prediction
        # ------------------------------------------------------------

        for route_id, route in self.routes.items():

            step = route.final_step

            position = step.predicted_position

            if position is None:
                continue

            px, py = self.world_to_canvas(
                position[0],
                position[1],
            )

            # Uncertainty envelope
            radius = step.uncertainty_radius

            scale = (
                self.canvas_width - 110
            ) / 100.0

            radius_px = radius * scale

            self.canvas.create_oval(
                px - radius_px,
                py - radius_px,
                px + radius_px,
                py + radius_px,
                outline="gray",
                dash=(6, 4),
                width=2,
            )

            # Prediction point
            self.canvas.create_oval(
                px - 6,
                py - 6,
                px + 6,
                py + 6,
                fill="black",
            )

            self.canvas.create_text(
                px,
                py - radius_px - 12,
                text=(
                    f"WILDLIFE PREDICTION "
                    f"R{route_id}"
                ),
                font=("Arial", 8, "bold"),
            )

        # ------------------------------------------------------------
        # Sensor blind marker
        # ------------------------------------------------------------

        blind_time = None

        for route in self.routes.values():
            for step in route.steps:
                if step.blind:
                    blind_time = step.time_min
                    break

            if blind_time is not None:
                break

        if blind_time is not None:
            self.canvas.create_text(
                self.canvas_width / 2,
                self.canvas_height - 18,
                text=(
                    f"SENSOR BLINDNESS ACTIVE "
                    f"FROM t={blind_time:.0f} MIN"
                ),
                font=("Arial", 10, "bold"),
            )

    # ================================================================
    # STATUS
    # ================================================================

    def display_status(self):
        for route_id, route in self.routes.items():

            step = route.final_step

            sensor = (
                "ACTIVE"
                if step.visible
                else "BLIND"
            )

            self.status_tree.insert(
                "",
                "end",
                values=(
                    route_id,
                    step.temporal_state,
                    step.decision,
                    (
                        "YES"
                        if step.safety_cleared
                        else "NO"
                    ),
                    f"{step.uncertainty_radius:.2f}",
                    sensor,
                ),
            )

    # ================================================================
    # COMMUNITY MESSAGE
    # ================================================================

    def display_message(self):
        blind_routes = []

        uncleared_routes = []

        for route_id, route in self.routes.items():

            if route.ever_blind:
                blind_routes.append(route_id)

            if not route.safety_cleared:
                uncleared_routes.append(route_id)

        lines = []

        lines.append(
            "WILD SENTINEL COMMUNITY SAFETY STATUS"
        )

        lines.append(
            "----------------------------------------"
        )

        lines.append(
            "Sensor status: BLINDNESS DETECTED"
        )

        lines.append(
            "Prediction remains active, but direct "
            "observation is unavailable."
        )

        lines.append("")

        lines.append(
            "Routes affected by sensor blindness: "
            + ", ".join(blind_routes)
        )

        lines.append(
            "Routes not safety-cleared: "
            + ", ".join(uncleared_routes)
        )

        lines.append("")

        lines.append(
            "IMPORTANT:"
        )

        lines.append(
            "A predicted wildlife position is not an "
            "observed position."
        )

        lines.append(
            "Uncertainty must not be interpreted as safety."
        )

        lines.append("")

        lines.append(
            "AUTHORITATIVE DECISION SOURCE:"
        )

        lines.append(
            "V0.10.6 safety engine."
        )

        lines.append("")

        lines.append(
            "V0.10.12 is a community presentation layer "
            "and does not create or override safety decisions."
        )

        self.message.insert(
            "end",
            "\n".join(lines),
        )


def main():
    root = tk.Tk()

    WildSentinel1012(root)

    root.mainloop()


if __name__ == "__main__":
    main()