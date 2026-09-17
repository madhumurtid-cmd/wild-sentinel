"""
WILD SENTINEL V0.10.14

LIVE TIME PROGRESSION DEMONSTRATION

Purpose
-------
Present the authoritative V0.10.6 route assessment as a
time-progressing community safety demonstration.

ARCHITECTURE
------------
V0.10.6  = Safety Authority
V0.10.12 = House -> School Scenario
V0.10.13 = Community Alert Timeline
V0.10.14 = Live Time Progression Presentation

SAFETY PRINCIPLES
-----------------
1. V0.10.6 remains the sole safety authority.
2. Prediction is not observation.
3. Sensor blindness is explicitly displayed.
4. Uncertainty is explicitly displayed.
5. Safety decisions are inherited from V0.10.6.
6. V0.10.14 does not rank routes.
7. V0.10.14 does not create a new safety decision.
8. V0.10.14 does not override the safety engine.
9. Time progression only reveals existing assessment steps.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import wild_sentinel_v0_10_6 as v106


class WildSentinel1014:
    """Live community presentation of authoritative safety steps."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(
            "Wild Sentinel V0.10.14 - Live Time Progression"
        )
        self.root.geometry("1150x800")
        self.root.minsize(1000, 720)

        self.engine = v106.WildSentinel106()

        self.scenarios = self.create_scenarios()

        # V0.10.6 is the sole source of safety assessment.
        self.assessment = self.engine.evaluate_routes(self.scenarios)
        self.routes = self.assessment.routes

        self.time_index = 0
        self.timeline_steps = self.build_timeline_steps()

        self.build_ui()
        self.update_display()

    # ------------------------------------------------------------------
    # Scenario
    # ------------------------------------------------------------------

    def create_scenarios(self):
        """
        Same three-route HOUSE -> SCHOOL scenario used by
        the previous presentation layers.

        No safety logic is added here.
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
    # Timeline
    # ------------------------------------------------------------------

    def build_timeline_steps(self):
        """
        Build the presentation timeline from the actual V0.10.6
        RouteAssessment steps.

        The presentation never invents future safety states.
        """

        times = set()

        for route in self.routes.values():
            for step in route.steps:
                times.add(step.time_min)

        return sorted(times)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def build_ui(self):
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)

        title = ttk.Label(
            main,
            text="WILD SENTINEL",
            font=("Segoe UI", 24, "bold"),
        )
        title.pack()

        subtitle = ttk.Label(
            main,
            text="HOUSE → SCHOOL LIVE SAFETY DEMONSTRATION",
            font=("Segoe UI", 14, "bold"),
        )
        subtitle.pack(pady=(2, 4))

        authority = ttk.Label(
            main,
            text=(
                "V0.10.6 = SAFETY AUTHORITY    |    "
                "V0.10.14 = TIME PROGRESSION PRESENTATION"
            ),
            font=("Segoe UI", 10, "bold"),
        )
        authority.pack(pady=(0, 12))

        self.build_clock(main)

        ttk.Separator(main, orient="horizontal").pack(
            fill="x",
            pady=10,
        )

        self.build_status(main)

        ttk.Separator(main, orient="horizontal").pack(
            fill="x",
            pady=10,
        )

        self.build_evidence(main)

        ttk.Separator(main, orient="horizontal").pack(
            fill="x",
            pady=10,
        )

        self.build_controls(main)

        ttk.Separator(main, orient="horizontal").pack(
            fill="x",
            pady=10,
        )

        self.build_message(main)

    # ------------------------------------------------------------------
    # Clock
    # ------------------------------------------------------------------

    def build_clock(self, parent):
        frame = ttk.LabelFrame(
            parent,
            text=" CURRENT SIMULATION TIME ",
            padding=12,
        )
        frame.pack(fill="x")

        self.time_label = ttk.Label(
            frame,
            text="T+00.0 min",
            font=("Segoe UI", 22, "bold"),
            anchor="center",
        )
        self.time_label.pack(fill="x")

        self.progress = ttk.Progressbar(
            frame,
            orient="horizontal",
            mode="determinate",
            maximum=max(self.timeline_steps) if self.timeline_steps else 1,
        )
        self.progress.pack(fill="x", pady=(8, 0))

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def build_status(self, parent):
        frame = ttk.LabelFrame(
            parent,
            text=" LIVE ROUTE SAFETY STATUS ",
            padding=10,
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

        self.tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            height=4,
        )

        widths = {
            "Route": 80,
            "State": 145,
            "Decision": 125,
            "Cleared": 95,
            "Uncertainty": 120,
            "Sensor": 150,
        }

        for column in columns:
            self.tree.heading(column, text=column)
            self.tree.column(
                column,
                width=widths[column],
                anchor="center",
            )

        self.tree.pack(fill="x")

    # ------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------

    def build_evidence(self, parent):
        frame = ttk.LabelFrame(
            parent,
            text=" CURRENT EVIDENCE ",
            padding=10,
        )
        frame.pack(fill="x")

        self.evidence_label = ttk.Label(
            frame,
            text="",
            justify="left",
            anchor="w",
            font=("Segoe UI", 10),
        )
        self.evidence_label.pack(fill="x")

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------

    def build_controls(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="x")

        self.previous_button = ttk.Button(
            frame,
            text="◀ PREVIOUS",
            command=self.previous_step,
        )
        self.previous_button.pack(side="left", padx=5)

        self.play_button = ttk.Button(
            frame,
            text="▶ PLAY",
            command=self.play,
        )
        self.play_button.pack(side="left", padx=5)

        self.next_button = ttk.Button(
            frame,
            text="NEXT ▶",
            command=self.next_step,
        )
        self.next_button.pack(side="left", padx=5)

        self.reset_button = ttk.Button(
            frame,
            text="RESET",
            command=self.reset,
        )
        self.reset_button.pack(side="left", padx=5)

        self.playing = False

    # ------------------------------------------------------------------
    # Community message
    # ------------------------------------------------------------------

    def build_message(self, parent):
        frame = ttk.LabelFrame(
            parent,
            text=" COMMUNITY INTERPRETATION ",
            padding=10,
        )
        frame.pack(fill="both", expand=True)

        self.message_label = ttk.Label(
            frame,
            text="",
            justify="left",
            anchor="nw",
            font=("Segoe UI", 11),
        )
        self.message_label.pack(
            fill="both",
            expand=True,
        )

    # ------------------------------------------------------------------
    # Step lookup
    # ------------------------------------------------------------------

    def get_step(self, route, time_min):
        for step in route.steps:
            if step.time_min == time_min:
                return step

        return None

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def update_display(self):
        if not self.timeline_steps:
            return

        current_time = self.timeline_steps[self.time_index]

        self.time_label.config(
            text=f"T+{current_time:.1f} min"
        )

        self.progress["value"] = current_time

        for item in self.tree.get_children():
            self.tree.delete(item)

        current_steps = []

        for route_id, route in self.routes.items():
            step = self.get_step(route, current_time)

            if step is None:
                continue

            current_steps.append((route_id, step))

            self.tree.insert(
                "",
                "end",
                values=(
                    f"Route {route_id}",
                    step.temporal_state,
                    step.decision,
                    "YES" if step.safety_cleared else "NO",
                    f"{step.uncertainty_radius:.2f}",
                    "BLIND" if step.blind else "VISIBLE",
                ),
            )

        self.update_evidence(current_steps)
        self.update_message(current_steps)

        self.previous_button.config(
            state=(
                "normal"
                if self.time_index > 0
                else "disabled"
            )
        )

        self.next_button.config(
            state=(
                "normal"
                if self.time_index < len(self.timeline_steps) - 1
                else "disabled"
            )
        )

    # ------------------------------------------------------------------
    # Evidence display
    # ------------------------------------------------------------------

    def update_evidence(self, current_steps):
        if not current_steps:
            return

        step = current_steps[0][1]

        observed = (
            "NONE — sensor blind"
            if step.observed_position is None
            else str(step.observed_position)
        )

        predicted = str(step.predicted_position)

        source = step.input_source

        text = (
            f"Observed position:  {observed}\n"
            f"Predicted position: {predicted}\n"
            f"Uncertainty radius: {step.uncertainty_radius:.2f}\n"
            f"Input source:       {source}\n"
            f"Prediction error:   {step.prediction_error}"
        )

        self.evidence_label.config(text=text)

    # ------------------------------------------------------------------
    # Community interpretation
    # ------------------------------------------------------------------

    def update_message(self, current_steps):
        if not current_steps:
            return

        blind = any(step.blind for _, step in current_steps)
        cleared = all(
            step.safety_cleared
            for _, step in current_steps
        )

        if blind:
            message = (
                "⚠ SENSOR BLINDNESS DETECTED\n\n"
                "The wildlife position is not currently observed.\n"
                "The displayed position is a prediction based on "
                "available evidence.\n\n"
                "Prediction is NOT observation.\n"
                "Uncertainty is explicitly displayed.\n\n"
                "Safety clearance has NOT been established."
            )
        elif cleared:
            message = (
                "CURRENT SENSOR STATE\n\n"
                "Wildlife position is being observed.\n\n"
                "The displayed safety state comes directly "
                "from the V0.10.6 safety authority."
            )
        else:
            message = (
                "CURRENT SAFETY STATE\n\n"
                "The authoritative safety engine has not "
                "cleared the route.\n\n"
                "Continue to follow the displayed safety status."
            )

        self.message_label.config(text=message)

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------

    def next_step(self):
        if self.time_index < len(self.timeline_steps) - 1:
            self.time_index += 1
            self.update_display()

    def previous_step(self):
        if self.time_index > 0:
            self.time_index -= 1
            self.update_display()

    def reset(self):
        self.playing = False
        self.play_button.config(text="▶ PLAY")
        self.time_index = 0
        self.update_display()

    def play(self):
        if self.playing:
            self.playing = False
            self.play_button.config(text="▶ PLAY")
            return

        if self.time_index >= len(self.timeline_steps) - 1:
            self.time_index = 0

        self.playing = True
        self.play_button.config(text="⏸ PAUSE")
        self.advance_playback()

    def advance_playback(self):
        if not self.playing:
            return

        if self.time_index >= len(self.timeline_steps) - 1:
            self.playing = False
            self.play_button.config(text="▶ PLAY")
            return

        self.time_index += 1
        self.update_display()

        self.root.after(1500, self.advance_playback)

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self):
        self.root.mainloop()


def main():
    root = tk.Tk()
    WildSentinel1014(root).run()


if __name__ == "__main__":
    main()