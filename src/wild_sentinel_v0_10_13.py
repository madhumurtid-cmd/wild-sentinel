"""
WILD SENTINEL V0.10.13

COMMUNITY ALERT TIMELINE

Purpose
-------
Convert the V0.10.12 HOUSE -> SCHOOL scenario into a simple
chronological community safety demonstration.

ARCHITECTURE
------------
V0.10.6  = Safety Authority
V0.10.12 = House -> School Scenario
V0.10.13 = Community Alert Timeline

SAFETY PRINCIPLES
-----------------
1. V0.10.6 remains the sole safety authority.
2. Prediction is not observation.
3. Sensor blindness is explicitly displayed.
4. Uncertainty is explicitly displayed.
5. Safety decisions are inherited from V0.10.6.
6. V0.10.13 does not rank routes.
7. V0.10.13 does not create a new safety decision.
8. V0.10.13 does not override the safety engine.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import wild_sentinel_v0_10_6 as v106


class WildSentinel1013:
    """Community-facing chronological safety presentation."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(
            "Wild Sentinel V0.10.13 - Community Alert Timeline"
        )
        self.root.geometry("1100x760")
        self.root.minsize(950, 680)

        self.engine = v106.WildSentinel106()

        self.scenarios = self.create_scenarios()
        self.assessment = self.engine.evaluate_routes(self.scenarios)
        self.routes = self.assessment.routes

        self.build_ui()

    # ------------------------------------------------------------------
    # Scenario
    # ------------------------------------------------------------------

    def create_scenarios(self):
        """
        HOUSE -> SCHOOL scenario.

        Observations stop at 15 minutes, creating an explicit
        sensor-blind period.
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
    # UI
    # ------------------------------------------------------------------

    def build_ui(self):
        main = ttk.Frame(self.root, padding=18)
        main.pack(fill="both", expand=True)

        title = ttk.Label(
            main,
            text="WILD SENTINEL",
            font=("Segoe UI", 24, "bold"),
        )
        title.pack()

        subtitle = ttk.Label(
            main,
            text="HOUSE → SCHOOL COMMUNITY SAFETY TIMELINE",
            font=("Segoe UI", 14, "bold"),
        )
        subtitle.pack(pady=(2, 12))

        authority = ttk.Label(
            main,
            text=(
                "V0.10.6 = SAFETY AUTHORITY    |    "
                "V0.10.13 = COMMUNITY PRESENTATION"
            ),
            font=("Segoe UI", 10, "bold"),
        )
        authority.pack(pady=(0, 12))

        self.build_timeline(main)

        ttk.Separator(main, orient="horizontal").pack(
            fill="x",
            pady=14,
        )

        self.build_status(main)

        ttk.Separator(main, orient="horizontal").pack(
            fill="x",
            pady=14,
        )

        self.build_message(main)

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------

    def build_timeline(self, parent):
        frame = ttk.LabelFrame(
            parent,
            text=" COMMUNITY SAFETY TIMELINE ",
            padding=12,
        )
        frame.pack(fill="x")

        steps = [
            (
                "00 min",
                "WILDLIFE OBSERVED",
                "Sensor observation available",
            ),
            (
                "05 min",
                "MOVEMENT DETECTED",
                "Sensor observation continues",
            ),
            (
                "10 min",
                "MOVEMENT CONTINUES",
                "Latest confirmed observation",
            ),
            (
                "15 min",
                "SENSOR BLIND",
                "Position is predicted — not observed",
            ),
        ]

        for time_text, event_text, detail in steps:
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=5)

            time_label = ttk.Label(
                row,
                text=time_text,
                width=9,
                font=("Segoe UI", 10, "bold"),
            )
            time_label.pack(side="left")

            event_label = ttk.Label(
                row,
                text=event_text,
                width=24,
                font=("Segoe UI", 10, "bold"),
            )
            event_label.pack(side="left")

            detail_label = ttk.Label(
                row,
                text=detail,
                font=("Segoe UI", 10),
            )
            detail_label.pack(side="left", padx=10)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def build_status(self, parent):
        frame = ttk.LabelFrame(
            parent,
            text=" CURRENT SAFETY STATUS ",
            padding=12,
        )
        frame.pack(fill="x")

        columns = (
            "Route",
            "State",
            "Decision",
            "Cleared",
            "Uncertainty",
            "Sensor",
        )

        tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            height=4,
        )

        widths = {
            "Route": 80,
            "State": 150,
            "Decision": 130,
            "Cleared": 100,
            "Uncertainty": 130,
            "Sensor": 160,
        }

        for column in columns:
            tree.heading(column, text=column)
            tree.column(
                column,
                width=widths[column],
                anchor="center",
            )

        for route_id, route in self.routes.items():
            tree.insert(
                "",
                "end",
                values=(
                    f"Route {route_id}",
                    route.temporal_state,
                    route.decision,
                    "YES" if route.safety_cleared else "NO",
                    f"{route.uncertainty_radius:.2f}",
                    "BLIND" if route.blind else "VISIBLE",
                ),
            )

        tree.pack(fill="x")

        self.status_tree = tree

    # ------------------------------------------------------------------
    # Community message
    # ------------------------------------------------------------------

    def build_message(self, parent):
        frame = ttk.LabelFrame(
            parent,
            text=" COMMUNITY SAFETY MESSAGE ",
            padding=14,
        )
        frame.pack(fill="both", expand=True)

        message = (
            "SENSOR BLINDNESS DETECTED\n\n"
            "Wildlife is not currently being observed by the sensor.\n"
            "The displayed position is therefore a prediction based on "
            "the last observation and movement.\n\n"
            "Prediction is NOT observation.\n"
            "Uncertainty is explicitly shown.\n\n"
            "CURRENT SAFETY DECISION: CAUTION\n"
            "SAFETY CLEARED: NO\n\n"
            "The safety decision shown here originates from V0.10.6."
        )

        label = ttk.Label(
            frame,
            text=message,
            justify="left",
            anchor="w",
            font=("Segoe UI", 11),
        )
        label.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self):
        self.root.mainloop()


def main():
    root = tk.Tk()
    WildSentinel1013(root).run()


if __name__ == "__main__":
    main()