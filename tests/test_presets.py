from pathlib import Path
import unittest
import numpy as np
from streamlit.testing.v1 import AppTest
from presets import EXPERIMENTS, experiment_settings
from settings import dump_settings, load_settings
from signal_processing import generate_signal, combine_signals, evaluate_expression, amplitude_spectrum


def render(name):
    config = load_settings(dump_settings(experiment_settings(name)))
    signals = {}
    warnings = []
    for item in config["signals"]:
        axis, values, notices = generate_signal(mode=config["mode"], duration=config["duration"],
            sampling_frequency=config["sampling_frequency"], samples=config["samples"],
            **{k:v for k,v in item.items() if k != "id"})
        signals[f"S{item['id']}"] = values
        warnings.extend(notices)
    result = evaluate_expression(config["expression"], signals) if config["use_expression"] else combine_signals(signals.values(), config["operation"])
    frequency, magnitude = amplitude_spectrum(result, config["sampling_frequency"])
    return config, signals, result, frequency, magnitude, warnings


class PresetTests(unittest.TestCase):
    def test_beats_and_phase_cancellation(self):
        config, _, _, frequency, magnitude, _ = render("Beats")
        for peak in (10, 11):
            index = np.argmin(abs(frequency - peak))
            self.assertAlmostEqual(magnitude[index], 1.)
        _, _, result, _, _, _ = render("Phase cancellation")
        np.testing.assert_allclose(result, 0., atol=1e-13)

    def test_am_and_aliasing(self):
        _, _, _, frequency, magnitude, _ = render("Amplitude modulation")
        for peak, amplitude in ((40, 1.), (35, .25), (45, .25)):
            self.assertAlmostEqual(magnitude[np.argmin(abs(frequency - peak))], amplitude)
        _, _, _, frequency, magnitude, warnings = render("Aliasing")
        self.assertEqual(frequency[np.argmax(magnitude)], 30.)
        self.assertTrue(warnings)

    def test_leakage_and_independent_settings(self):
        config, signals, _, _, rectangular, _ = render("Spectral leakage")
        for window in ("Hann", "Hamming"):
            _, tapered = amplitude_spectrum(signals["S1"], config["sampling_frequency"], window=window)
            self.assertLess(tapered[50], rectangular[50])
        config = experiment_settings("Beats")
        config["signals"][0]["frequency"] = 99
        self.assertEqual(experiment_settings("Beats")["signals"][0]["frequency"], 10.)

    def test_load_and_edit_every_preset(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
        self.assertTrue(app.button(key="load_experiment").disabled)
        app.button(key="add_signal").click().run()
        app.selectbox(key="signal_mode").select("Discrete").run()
        for name in EXPERIMENTS:
            app.selectbox(key="experiment_choice").select(name).run()
            app.button(key="load_experiment").click().run()
            config = experiment_settings(name)
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            self.assertEqual(app.selectbox(key="signal_mode").value, "Continuous")
            self.assertEqual(list(app.session_state["signal_ids"]), [s["id"] for s in config["signals"]])
            self.assertEqual(app.selectbox(key="fft_window").value, "Rectangular")
            self.assertEqual(len(app.get("plotly_chart")), 2)
            self.assertTrue(any(name in info.value for info in app.info))
            app.number_input(key="amp_1").set_value(1.5).run()
            self.assertEqual(app.number_input(key="amp_1").value, 1.5)
            self.assertFalse(app.exception)
        app.selectbox(key="experiment_choice").select("Beats").run()
        app.button(key="load_experiment").click().run()
        self.assertEqual(app.number_input(key="amp_1").value, 1.)
