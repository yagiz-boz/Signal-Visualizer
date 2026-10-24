from pathlib import Path
import json
import unittest
import numpy as np
from streamlit.testing.v1 import AppTest
from plotting import plot_indices
from settings import load_settings, dump_settings
from test_settings import example


class PlottingTests(unittest.TestCase):
    def test_full_detail_and_zoom_data(self):
        values = np.zeros(100000)
        values[54321] = 1
        np.testing.assert_array_equal(plot_indices(values), np.arange(100000))
        np.testing.assert_array_equal(plot_indices(values[:10]), np.arange(10))

    def test_overview_preserves_pulse_and_spectral_peak(self):
        values = np.zeros(100000)
        values[54321] = 4
        values[12345] = -3
        indices = plot_indices(values, overview=True)
        self.assertIn(54321, indices)
        self.assertIn(12345, indices)
        self.assertEqual(indices[0], 0)
        self.assertEqual(indices[-1], 99999)
        self.assertTrue(np.all(np.diff(indices) > 0))
        self.assertLessEqual(len(indices), 20000)
        # Separate traces must choose their own extrema, not share a stride.
        other = np.zeros(100000)
        other[77777] = 10
        self.assertIn(77777, plot_indices(other, overview=True))

    def test_undefined_gaps_are_preserved(self):
        values = np.ones(100000)
        values[55551:55553] = np.nan
        indices = plot_indices(values, overview=True)
        for boundary in (55550, 55551, 55552, 55553):
            self.assertIn(boundary, indices)
        self.assertTrue(np.any(np.isnan(values[indices])))

    def test_detail_selection_and_settings_compatibility(self):
        config = example()
        del config["view"]["plot_detail"]
        self.assertEqual(load_settings(json.dumps(config))["view"]["plot_detail"], "Full detail")
        config["view"]["plot_detail"] = "Overview"
        self.assertEqual(load_settings(dump_settings(config))["view"]["plot_detail"], "Overview")
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
        app.number_input(key="shared_fs").set_value(100000.).run()
        app.selectbox(key="wave_1").select("Pulse").run()
        app.number_input(key="start_t_1").set_value(.54321).run()
        app.number_input(key="width_t_1").set_value(.00001).run()
        self.assertEqual(app.radio(key="plot_detail").value, "Full detail")
        self.assertFalse(app.exception)
        app.radio(key="plot_detail").set_value("Overview").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(len(app.get("plotly_chart")), 2)
        plot = json.loads(app.get("plotly_chart")[0].proto.spec)
        self.assertFalse(plot["data"][0]["connectgaps"])
        self.assertIn("Index", plot["data"][0]["hovertemplate"])
