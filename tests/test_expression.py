from pathlib import Path
import unittest
import numpy as np
from streamlit.testing.v1 import AppTest
from signal_processing import evaluate_expression


class ExpressionTests(unittest.TestCase):
    def setUp(self):
        self.signals = {"S1": np.array([2., 4., 6.]), "S2": np.array([1., 2., 3.]), "S3": np.array([3., 2., 1.])}

    def test_precedence_parentheses_constants(self):
        np.testing.assert_allclose(evaluate_expression("S1 + S2 * S3", self.signals), [5, 8, 9])
        np.testing.assert_allclose(evaluate_expression("(S1 + S2) * S3", self.signals), [9, 12, 9])
        np.testing.assert_allclose(evaluate_expression("-S1 + +S2 / 2", self.signals), [-1.5, -3, -4.5])
        np.testing.assert_allclose(evaluate_expression("2.5", self.signals), [2.5] * 3)
        np.testing.assert_allclose(evaluate_expression("S1 / S2 / 2", self.signals), [1] * 3)
        np.testing.assert_array_equal(self.signals["S1"], [2, 4, 6])

    def test_division_and_overflow(self):
        self.assertTrue(np.all(np.isnan(evaluate_expression("S1 / (S2 - S2)", self.signals))))
        self.assertTrue(np.all(np.isnan(evaluate_expression("(1e308 * 2) * 0", self.signals))))
        np.testing.assert_allclose(evaluate_expression("1 / S1", self.signals), [0.5, .25, 1 / 6])

    def test_reject_invalid_or_executable_expressions(self):
        for expression in ("", "S9", "S1 +", "S1 ** 2", "S1[0]", "S1.real", "True", "'S1'", "1e999",
                           "__import__('os')", "abs(S1)", "[S1]", "S1 if 1 else S2", "S1; S2", "2S1", "2" * 257):
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                evaluate_expression(expression, self.signals)

    def test_custom_expression_ui(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
        app.button[0].click().run()
        app.button[0].click().run()
        app.checkbox(key="use_expression").check().run()
        app.text_input(key="custom_expression").set_value("(S1 + S2) * S3").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(len(app.get("plotly_chart")), 2)
        app.button(key="remove_3").click().run()
        self.assertIn("Unknown signal 'S3'", app.error[0].value)
        self.assertEqual(len(app.get("plotly_chart")), 0)
        app.text_input(key="custom_expression").set_value("S1 / (S2 - S2)").run()
        self.assertTrue(app.warning)
        self.assertEqual(len(app.get("plotly_chart")), 2)
        app.text_input(key="custom_expression").set_value("S1 +").run()
        self.assertTrue(app.error)
        app.checkbox(key="use_expression").uncheck().run()
        self.assertFalse(app.error)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("plotly_chart")), 2)
