from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
    def test_multiple_signals_and_modes(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("plotly_chart")), 2)
        app.button[0].click().run()
        app.number_input(key="freq_2").set_value(30.).run()
        app.number_input(key="amp_2").set_value(2.).run()
        for operation in ("Add", "Subtract", "Multiply", "Divide"):
            app.selectbox(key="operation").select(operation).run()
            self.assertFalse(app.exception)
        self.assertEqual(len(app.get("plotly_chart")), 1)
        self.assertTrue(app.warning)
        app.selectbox(key="operation").select("Add").run()
        app.button[0].click().run()
        self.assertEqual(list(app.session_state["signal_ids"]), [1, 2, 3])
        app.button(key="remove_1").click().run()
        self.assertEqual(list(app.session_state["signal_ids"]), [2, 3])
        self.assertEqual(app.number_input(key="amp_2").value, 2.)
        app.selectbox(key="wave_2").select("Cosine").run()
        app.selectbox(key="wave_2").select("Square").run()
        app.selectbox(key="wave_2").select("Sawtooth").run()
        app.selectbox(key="signal_mode").select("Discrete").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("plotly_chart")), 2)
        next(box for box in app.checkbox if box.label == "Show input signals").uncheck().run()
        app.button(key="remove_3").click().run()
        self.assertTrue(app.button(key="remove_2").disabled)
        for _ in range(7):
            app.button[0].click().run()
        self.assertTrue(app.button[0].disabled)
        self.assertFalse(app.exception)
