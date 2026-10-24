from pathlib import Path
import unittest
import numpy as np
from streamlit.testing.v1 import AppTest
from signal_processing import generate_signal, amplitude_spectrum, evaluate_expression


class WaveformTests(unittest.TestCase):
    def test_dc_and_spectrum(self):
        for mode in ("Continuous", "Discrete"):
            _, values, warnings = generate_signal(mode=mode, waveform="DC", amplitude=-3)
            np.testing.assert_array_equal(values, np.full(len(values), -3))
            _, spectrum = amplitude_spectrum(values)
            self.assertAlmostEqual(spectrum[0], 3)
            np.testing.assert_allclose(spectrum[1:], 0, atol=1e-12)
            self.assertFalse(warnings)

    def test_triangle_samples_and_phase(self):
        _, values, _ = generate_signal(waveform="Triangle", frequency=1, duration=1, sampling_frequency=4, amplitude=2)
        np.testing.assert_allclose(values, [-2, 0, 2, 0])
        _, shifted, _ = generate_signal(waveform="Triangle", frequency=1, phase=90, duration=1, sampling_frequency=4)
        np.testing.assert_allclose(shifted, [0, 1, 0, -1])
        _, discrete, _ = generate_signal(mode="Discrete", waveform="Triangle", frequency=np.pi / 2, samples=4)
        np.testing.assert_allclose(discrete, [-1, 0, 1, 0])

    def test_step_and_pulse_boundaries(self):
        _, step, _ = generate_signal(waveform="Unit step", start=.25, sampling_frequency=4)
        np.testing.assert_array_equal(step, [0, 1, 1, 1])
        _, pulse, _ = generate_signal(waveform="Pulse", start=.25, pulse_width=.5, sampling_frequency=4)
        np.testing.assert_array_equal(pulse, [0, 1, 1, 0])
        _, impulse, _ = generate_signal(mode="Discrete", waveform="Pulse", start=2, pulse_width=1, samples=5)
        np.testing.assert_array_equal(impulse, [0, 0, 1, 0, 0])
        _, default_impulse, _ = generate_signal(mode="Discrete", waveform="Pulse", samples=3)
        np.testing.assert_array_equal(default_impulse, [1, 0, 0])
        _, step_n, _ = generate_signal(mode="Discrete", waveform="Unit step", start=2, samples=5)
        np.testing.assert_array_equal(step_n, [0, 0, 1, 1, 1])
        np.testing.assert_array_equal(evaluate_expression("S1 + 2 * S2", {"S1": step, "S2": pulse}), [0, 3, 3, 1])

    def test_validation_and_unsampled_pulse(self):
        for kwargs in ({"pulse_width": 0}, {"start": float("nan")},
                       {"mode": "Discrete", "start": .5},
                       {"mode": "Discrete", "pulse_width": 1.5}):
            with self.assertRaises(ValueError):
                generate_signal(waveform="Pulse", **kwargs)
        _, pulse, warnings = generate_signal(waveform="Pulse", start=2)
        self.assertFalse(np.any(pulse))
        self.assertTrue(any("no sampled points" in warning for warning in warnings))

    def test_controls_and_expression(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
        for mode in ("Continuous", "Discrete"):
            app.selectbox(key="signal_mode").select(mode).run()
            for waveform in ("DC", "Triangle", "Unit step", "Pulse"):
                app.selectbox(key="wave_1").select(waveform).run()
                self.assertFalse(app.exception)
                self.assertFalse(app.error)
                self.assertEqual(len(app.get("plotly_chart")), 2)
                labels = [widget.label for widget in app.number_input]
                if waveform in ("DC", "Unit step", "Pulse"):
                    self.assertNotIn("Phase [deg]", labels)
                    self.assertNotIn("Frequency [Hz]", labels)
                if waveform == "Pulse":
                    self.assertIn("Pulse width [samples]" if mode == "Discrete" else "Pulse width [s]", labels)
        app.button[0].click().run()
        app.selectbox(key="wave_2").select("DC").run()
        app.checkbox(key="use_expression").check().run()
        app.text_input(key="custom_expression").set_value("S1 + 2 * S2").run()
        self.assertFalse(app.error)
        self.assertFalse(app.exception)
