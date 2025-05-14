from manim import *
import numpy as np
import random
from names import names

'''
names = [ 
    'John', 'Ash', 'Mary', 'Jane', 'Wayne', 'Grace', 'Jasper', 'Ashley', 'Kris', 'Ava', 'Taylor'
]
'''

class MLDataAggregationVisualization(Scene):
    def construct(self):
        # Title
        title = Text("ML Prediction example").scale(0.75).to_edge(UP)
        self.play(Write(title))

        # Create multiple data points - each one equidistant from the previous one by UP * (5-i) / 2
        data_points = VGroup()
        for i in range(12): 
            chosen_name = random.choice(names)
            point = Text("[{}, {}, ${}k, {}]".format(
                chosen_name,
                random.randint(18, 44),
                random.randint(30, 70),
                random.randint(0, 4)
            ), font_size=13)
            point.move_to(LEFT * 5 + UP * (5 - i) / 2)
            data_points.add(point)

        # Show the data points
        self.play(Create(data_points))
        self.wait(3)
        # Indicating more data points
        dots = Text("...", font_size=36).next_to(data_points, DOWN, buff=0.2)
        self.play(Write(dots))

        # Create a "dataset" box
        dataset_box = Rectangle(height=4, width=3, color=BLUE)
        dataset_box.to_edge(LEFT)
        dataset_label = Text("Dataset", font_size=36).next_to(dataset_box, UP).scale(0.7)
        dataset = VGroup(dataset_box, dataset_label)

        # Move data points to the dataset box
        self.play(
            Create(dataset),
            *[point.animate.scale(0.8).move_to(dataset_box.get_center() + np.random.rand(3) * 0.2)
              for point in data_points],
            dots.animate.move_to(dataset_box.get_center())
        )

        # Create the ML model
        model = Rectangle(height=2, width=2, color=GREEN).scale(0.8)
        model.next_to(dataset_box, RIGHT, buff=3)
        model_label = Text("ML Model").next_to(model, UP).scale(0.5)
        ml_model = VGroup(model, model_label)

        # Show the ML model
        self.play(Create(ml_model))

        # Arrow from dataset to model and write to arrow
        arrow1 = Arrow(dataset_box.get_right(), model.get_left(), buff=0.1)
        self.play(Create(arrow1))
        arrow1_text = Text("training...").next_to(arrow1, UP, buff=0.1).scale(0.3)
        self.play(Write(arrow1_text))

        # Prediction output
        prediction_box = Rectangle(height=1, width=2, color=RED)
        prediction_box.next_to(model, RIGHT, buff=1)
        prediction_label = Text("Prediction", font_size=30).next_to(prediction_box, UP).scale(0.6)
        prediction = VGroup(prediction_box, prediction_label)

        # Arrow from model to prediction
        arrow2 = Arrow(model.get_right(), prediction_box.get_left(), buff=0.3)

        # Show prediction and arrow
        self.play(Create(arrow2), Create(prediction))
        self.wait(2)

        # Animate a new data point for prediction
        new_point = Text("[Alice, 28, $60k, 1]", font_size=24).move_to(LEFT * 5)
        new_point.to_edge(DOWN)
        self.play(Write(new_point))
        self.wait(2)

        # Move the new point through the model to get a prediction
        self.play(new_point.animate.scale(0.5).move_to(model.get_center()))
        self.play(new_point.animate.move_to(prediction_box.get_center()))

        # Show the final prediction
        final_prediction = Text("Buying Probability: 22%", font_size=18, color=YELLOW)
        final_prediction.next_to(prediction_box, DOWN)
        self.play(Write(final_prediction))

        # Final pause
        self.wait(2)

if __name__ == "__main__":
    scene = MLDataAggregationVisualization()
    scene.render()