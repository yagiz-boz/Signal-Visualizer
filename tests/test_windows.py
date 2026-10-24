import json
from pathlib import Path
import unittest
import numpy as np
from streamlit.testing.v1 import AppTest
from signal_processing import amplitude_spectrum
from settings import load_settings, dump_settings, settings_state
from test_settings import example


class WindowTests(unittest.TestCase):
    def test_coherent_tone_dc_nyquist(self):
        for size in (100, 101):
            n = np.arange(size)
            for window in ("Rectangular", "Hann", "Hamming"):
                f, magnitude = amplitude_spectrum(2.5 * np.cos(2 * np.pi * 10 * n / size + .3), 1000, window=window)
                self.assertAlmostEqual(magnitude[10], 2.5)
                self.assertAlmostEqual(f[10], 10000 / size)
                _, dc = amplitude_spectrum(np.full(size, 3.), window=window)
                self.assertAlmostEqual(dc[0], 3.)
                if size % 2 == 0:
                    _, nyquist = amplitude_spectrum(2 * (-1.) ** n, window=window)
                    self.assertAlmostEqual(nyquist[-1], 2.)

    def test_off_bin_leakage_and_small_records(self):
        size = 1024
        values = np.sin(2 * np.pi * 50.3 * np.arange(size) / size)
        _, rectangular = amplitude_spectrum(values)
        for window in ("Hann", "Hamming"):
            _, tapered = amplitude_spectrum(values, window=window)
            self.assertLess(tapered[100], rectangular[100])
            for length in (2, 3):
                _, magnitude = amplitude_spectrum(np.ones(length), window=window)
                self.assertTrue(np.all(np.isfinite(magnitude)))
                self.assertAlmostEqual(magnitude[0], 1.)
        with self.assertRaises(ValueError):
            amplitude_spectrum(values, window="Unknown")

    def test_settings_compatibility(self):
        config = example()
        del config["view"]["fft_window"]
        self.assertEqual(load_settings(json.dumps(config))["view"]["fft_window"], "Rectangular")
        for window in ("Hann", "Hamming"):
            config["view"]["fft_window"] = window
            self.assertEqual(settings_state(load_settings(dump_settings(config)))["fft_window"], window)
        config["view"]["fft_window"] = "bad"
        with self.assertRaises(ValueError):
            dump_settings(config)

    def test_ui_applies_same_window_without_mutating_time_data(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
        app.button(key="add_signal").click().run()
        time_spec = app.get("plotly_chart")[0].proto.spec
        rectangular = app.get("plotly_chart")[1].proto.spec
        for window in ("Hann", "Hamming"):
            app.selectbox(key="fft_window").select(window).run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            self.assertEqual(app.get("plotly_chart")[0].proto.spec, time_spec)
            self.assertNotEqual(app.get("plotly_chart")[1].proto.spec, rectangular)
            traces = json.loads(app.get("plotly_chart")[1].proto.spec)["data"]
            self.assertEqual([t["name"] for t in traces], ["S1", "S2", "Result"])
        app.selectbox(key="signal_mode").select("Discrete").run()
        self.assertEqual(app.selectbox(key="fft_window").value, "Hamming")
        self.assertFalse(app.exception)
