"""
WILD SENTINEL V0.10.7

MULTI-ROUTE VISUAL / LIVE SIMULATION PROTOTYPE

V0.10.7 is a presentation layer above the frozen V0.10.6
multi-route scenario engine.

CORE PRINCIPLE:

    THE VISUAL LAYER DOES NOT MAKE SAFETY DECISIONS.

V0.10.6 remains the source of truth for:
    - temporal state
    - safety decision
    - uncertainty
    - prediction
    - safety history

V0.10.7 only:
    - creates demonstration scenarios
    - submits them to V0.10.6
    - visualises the returned results
"""

import tkinter as tk
from tkinter import ttk

import wild_sentinel_v0_10_6 as v106


APP_TITLE = "WILD SENTINEL V0.10.7"
WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 700


class WildSentinel107:
    """Visual shell around the frozen V0.10.6 engine."""

    def __init__(self, root):
        self.root = root

        self.root.title(APP_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(900, 600)

        # Frozen safety engine.
        self.engine = v106.WildSentinel106()

        self.assessments = {}

        self.build_header()
        self.build_route_panel()
        self.build_status_panel()
        self.build_controls()

        self.show_initial_state()

    def build_header(self):
        header = ttk.Frame(self.root, padding=15)
        header.pack(fill="x")

        title = ttk.Label(
            header,
            text="WILD SENTINEL",
            font=("Arial", 22, "bold"),
        )
        title.pack()

        subtitle = ttk.Label(
            header,
            text="V0.10.7 - LIVE WILDLIFE SAFETY VIEW",
            font=("Arial", 11),
        )
        subtitle.pack(pady=(4, 0))

    def build_route_panel(self):
        panel = ttk.LabelFrame(
            self.root,
            text="ROUTE OVERVIEW",
            padding=15,
        )
        panel.pack(fill="x", padx=20, pady=10)

        self.route_labels = {}

        for route_name in ("ROUTE A", "ROUTE B", "ROUTE C"):
            row = ttk.Frame(panel)
            row.pack(fill="x", pady=5)

            name = ttk.Label(
                row,
                text=route_name,
                width=15,
                font=("Arial", 11, "bold"),
            )
            name.pack(side="left")

            status = ttk.Label(
                row,
                text="READY",
                width=30,
                font=("Arial", 11, "bold"),
            )
            status.pack(side="left")

            self.route_labels[route_name] = status

    def build_status_panel(self):
        panel = ttk.LabelFrame(
            self.root,
            text="CURRENT ENGINE STATE",
            padding=15,
        )
        panel.pack(fill="both", expand=True, padx=20, pady=10)

        self.status_text = tk.Text(
            panel,
            height=15,
            font=("Consolas", 11),
            state="disabled",
        )
        self.status_text.pack(fill="both", expand=True)

    def build_controls(self):
        controls = ttk.Frame(self.root, padding=(20, 0, 20, 15))
        controls.pack(fill="x")

        run_button = ttk.Button(
            controls,
            text="RUN 3-ROUTE SIMULATION",
            command=self.run_simulation,
        )
        run_button.pack(side="left")

    def write_status(self, text):
        self.status_text.configure(state="normal")
        self.status_text.delete("1.0", tk.END)
        self.status_text.insert(tk.END, text)
        self.status_text.configure(state="disabled")

    def show_initial_state(self):
        for label in self.route_labels.values():
            label.configure(text="READY")

        self.write_status(
            "V0.10.7 MULTI-ROUTE VISUAL PROTOTYPE\n"
            "=====================================\n\n"
            "Frozen engine loaded:\n"
            "    V0.10.6 Multi-Route Scenario Engine\n\n"
            "Three routes are available for simulation:\n"
            "    ROUTE A\n"
            "    ROUTE B\n"
            "    ROUTE C\n\n"
            "Click RUN 3-ROUTE SIMULATION.\n\n"
            "IMPORTANT:\n"
            "V0.10.7 does not make safety decisions.\n"
            "All decisions come from V0.10.6."
        )

    def build_scenarios(self):
        """
        Create three independent sensor-blind scenarios.

        These are demonstration inputs only.

        None at the final observation time means the animal is
        not observed during the sensor-blind interval.

        The GUI does NOT determine what the safety decision is.
        """

        return [
            v106.RouteScenario(
                route_id="A",
                observations={
                    0.0: (50, 20),
                    5.0: (50, 25),
                    10.0: (50, 30),
                    15.0: None,
                },
            ),
            v106.RouteScenario(
                route_id="B",
                observations={
                    0.0: (30, 20),
                    5.0: (30, 25),
                    10.0: (30, 30),
                    15.0: None,
                },
            ),
            v106.RouteScenario(
                route_id="C",
                observations={
                    0.0: (70, 20),
                    5.0: (70, 25),
                    10.0: (70, 30),
                    15.0: None,
                },
            ),
        ]

    def run_simulation(self):
        """
        Evaluate all three routes through V0.10.6 multi-route API.
        """

        scenarios = self.build_scenarios()

        # V0.10.6 is the sole safety authority.
        # Evaluate all routes through its native multi-route API.
        multi_assessment = self.engine.evaluate_routes(scenarios)

        self.assessments = multi_assessment.routes

        for route_id in ("A", "B", "C"):
            assessment = self.assessments[route_id]
            final_step = assessment.final_step

            self.route_labels[
                f"ROUTE {route_id}"
            ].configure(
                text=final_step.decision
            )

        # Display detailed results for all three routes.
        lines = [
            "V0.10.7 THREE-ROUTE SIMULATION",
            "===============================",
            "",
            "ALL RESULTS BELOW COME FROM V0.10.6",
            "",
        ]

        for route_id in ("A", "B", "C"):
            assessment = self.assessments[route_id]
            step = assessment.final_step

            lines.extend(
                [
                    f"ROUTE {route_id}",
                    "-" * 40,
                    f"Time:               {step.time_min} min",
                    f"Observed position:  {step.observed_position}",
                    f"Predicted position: {step.predicted_position}",
                    f"Uncertainty radius: {step.uncertainty_radius}",
                    f"Visible:            {step.visible}",
                    f"Blind:              {step.blind}",
                    f"Temporal state:     {step.temporal_state}",
                    f"Decision:           {step.decision}",
                    f"Safety cleared:     {step.safety_cleared}",
                    f"Prediction error:   {step.prediction_error}",
                    f"Input source:       {step.input_source}",
                    "",
                ]
            )

        lines.extend(
            [
                "SAFETY ARCHITECTURE",
                "-------------------",
                "V0.10.6 = safety authority",
                "V0.10.7 = visualisation only",
                "",
                "Sensor blindness is explicitly represented.",
                "Prediction is not treated as observation.",
                "A route is not marked safe by the GUI.",
                "",
                "MULTI-ROUTE EVALUATION",
                "----------------------",
                "All routes evaluated through V0.10.6.evaluate_routes().",
                "No route influences another route's result.",
            ]
        )

        self.write_status("\n".join(lines))

def main():
    root = tk.Tk()
    WildSentinel107(root)
    root.mainloop()


if __name__ == "__main__":
    main()