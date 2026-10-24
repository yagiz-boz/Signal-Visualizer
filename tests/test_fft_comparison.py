from pathlib import Path
import json
import unittest
from streamlit.testing.v1 import AppTest


class SpectrumComparisonTests(unittest.TestCase):
    def test_selection_invalid_result_and_modes(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
        app.button(key="add_signal").click().run()
        app.number_input(key="freq_2").set_value(30.).run()
        self.assertEqual(app.multiselect(key="fft_traces").value, ["S1", "S2", "Result"])
        spectrum = json.loads(app.get("plotly_chart")[1].proto.spec)
        self.assertEqual([trace["name"] for trace in spectrum["data"]], ["S1", "S2", "Result"])
        time = json.loads(app.get("plotly_chart")[0].proto.spec)
        self.assertEqual([t["marker"]["color"] for t in time["data"]], [t["marker"]["color"] for t in spectrum["data"]])
        app.multiselect(key="fft_traces").set_value(["S2"]).run()
        spectrum = json.loads(app.get("plotly_chart")[1].proto.spec)
        self.assertEqual([t["name"] for t in spectrum["data"]], ["S2"])
        app.multiselect(key="fft_traces").set_value([]).run()
        self.assertEqual(len(app.get("plotly_chart")), 1)
        app.multiselect(key="fft_traces").set_value(["S1", "S2", "Result"]).run()
        app.selectbox(key="operation").select("Divide").run()
        spectrum = json.loads(app.get("plotly_chart")[1].proto.spec)
        self.assertEqual([t["name"] for t in spectrum["data"]], ["S1", "S2"])
        app.multiselect(key="fft_traces").set_value(["Result"]).run()
        self.assertEqual(len(app.get("plotly_chart")), 1)
        app.selectbox(key="operation").select("Add").run()
        app.selectbox(key="signal_mode").select("Discrete").run()
        spectrum = json.loads(app.get("plotly_chart")[1].proto.spec)
        self.assertIn("rad/sample", spectrum["layout"]["xaxis"]["title"]["text"])
        app.button(key="remove_2").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertNotIn("S2", app.multiselect(key="fft_traces").options)
