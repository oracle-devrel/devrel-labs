from manim import *

class PredictiveMLVisualization(Scene):
    def construct(self):
        # Title
        # Data point
        data_point = Text("[Name: John, Age: 30, Income: $50k, PreviousCars: 2]").scale(0.4).to_edge(UP)
        self.play(Write(data_point))

        # Target variable
        target_var = Text("Target Variable: Buying Probability (0-100%)").scale(0.4).set_color(YELLOW)
        target_var.next_to(data_point, DOWN, buff=0.5)
        self.play(Write(target_var))

        # Variable encoding
        encoded_vars = Text("Encoded Variables: [Age, Income, PreviousCars]").scale(0.4)
        encoded_vars.next_to(target_var, DOWN, buff=0.5)
        self.play(Write(encoded_vars))

        # Numerical representation
        num_repr = Text("Numerical: [30, 50000, 2]").scale(0.4)
        num_repr.next_to(encoded_vars, DOWN, buff=0.5)
        self.play(Write(num_repr))

        # Feature engineering
        feature_engineering = Text("Feature Engineering & Selection").scale(0.5)
        feature_engineering.next_to(num_repr, DOWN, buff=0.5)
        self.play(Write(feature_engineering))

        # Feature importance
        features = ["Age", "Income", "PreviousCars"]
        importances = [0.15, 0.6, 0.25]
        bar_chart = BarChart(
            values=importances,
            bar_names=features,
            y_range=[0, 1, 0.2],
            y_length=4,
            x_length=6,
            x_axis_config={"font_size": 24},
        ).scale(0.5)

        # Arrows connecting steps
        arrows = VGroup()
        for i in range(4):
            start = [data_point, target_var, encoded_vars, num_repr][i]
            end = [target_var, encoded_vars, num_repr, feature_engineering][i]
            arrow = Arrow(start=start.get_bottom(), end=end.get_top(), buff=0.1)
            arrows.add(arrow)


        bar_chart.next_to(feature_engineering, DOWN, buff=0.5)
        self.play(Create(bar_chart))

        self.play(Create(arrows))

        # Final pause
        self.wait(2)

if __name__ == "__main__":
    scenes = [PredictiveMLVisualization]
    for scene in scenes:
        scene().render()