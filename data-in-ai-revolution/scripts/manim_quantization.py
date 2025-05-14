from manim import *
import numpy as np

class QuantizationVisualization(Scene):
    def construct(self):
        # Original FP32 matrix
        fp32_matrix = np.array([
            [0.235, -0.789, 1.456],
            [3.141, -2.718, 0.577],
            [-1.414, 2.236, -0.693]
        ], dtype=np.float32)

        # Quantization parameters
        scale = (fp32_matrix.max() - fp32_matrix.min()) / 255
        zero_point = round(-fp32_matrix.min() / scale)

        # Quantization function
        def quantize(x):
            return np.clip(np.round(x / scale) + zero_point, 0, 255).astype(np.uint8)

        # Dequantization function
        def dequantize(x):
            return scale * (x.astype(np.float32) - zero_point)

        # Quantized INT8 matrix
        int8_matrix = quantize(fp32_matrix)

        # Dequantized matrix
        dequantized_matrix = dequantize(int8_matrix)

        # Create matrix visualizations
        fp32_viz = self.create_matrix_viz(fp32_matrix, title="Original FP32 Matrix")
        int8_viz = self.create_matrix_viz(int8_matrix, title="Quantized INT8 Matrix")
        dequant_viz = self.create_matrix_viz(dequantized_matrix, title="Dequantized Matrix")

        # Position matrices
        fp32_viz.to_corner(UL)
        int8_viz.to_corner(UR)
        dequant_viz.to_edge(DL)

        # Animations
        self.play(Write(fp32_viz))
        self.wait(1)

        quant_arrow = Arrow(fp32_viz.get_right(), int8_viz.get_left(), buff=0.5)
        quant_text = Text("Quantize", font_size=24).next_to(quant_arrow, UP)
        self.play(GrowArrow(quant_arrow), Write(quant_text))
        self.play(Write(int8_viz))
        self.wait(1)

        dequant_arrow = Arrow(int8_viz.get_bottom(), dequant_viz.get_top(), buff=0.5)
        dequant_text = Text("Dequantize", font_size=24).next_to(dequant_arrow, UP)
        self.play(GrowArrow(dequant_arrow), Write(dequant_text))
        self.play(Write(dequant_viz))
        self.wait(1)

        # Show quantization error
        error_matrix = np.abs(fp32_matrix - dequantized_matrix)
        error_viz = self.create_matrix_viz(error_matrix, title="Quantization Error")

        error_viz.to_edge(DR)
        #error_viz.next_to(dequant_viz, RIGHT, buff=1)

        error_arrow = Arrow(dequant_viz.get_right(), error_viz.get_left(), buff=0.5)
        error_text = Text("Calculate Error", font_size=24).next_to(error_arrow, UP)
        self.play(GrowArrow(error_arrow), Write(error_text))
        self.play(Write(error_viz))
        self.wait(2)

    def create_matrix_viz(self, matrix, title):
        cells = VGroup()
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                value = matrix[i, j]
                cell = Rectangle(height=0.6, width=1.2, fill_opacity=0.8, color=self.value_to_color(value))
                text = Text(f"{value:.3f}", font_size=16).move_to(cell)
                cells.add(VGroup(cell, text))
        cells.arrange_in_grid(rows=matrix.shape[0], cols=matrix.shape[1], buff=0.1)
        title = Text(title, font_size=24).next_to(cells, UP)
        return VGroup(title, cells)

    def value_to_color(self, value):
        # Map value to a color (you can adjust this for better visualization)
        return rgb_to_color([(value + 3) / 6, 0, (3 - value) / 6])