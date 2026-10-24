import copy
import json
import io
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from streamlit.testing.v1 import AppTest
from settings import dump_settings, load_settings, settings_state
from signal_processing import generate_signal, evaluate_expression


def example(mode="Continuous"):
    discrete = mode == "Discrete"
    return dict(version=1, mode=mode, duration=1., sampling_frequency=1000., samples=100,
                signals=[dict(id=2, waveform="Sine", amplitude=2., frequency=.5 if discrete else 10., phase=30., start=0 if discrete else 0., pulse_width=1 if discrete else .1),
                         dict(id=5, waveform="Pulse", amplitude=3., frequency=0., phase=0., start=3 if discrete else .25, pulse_width=2 if discrete else .1)],
                operation="Multiply", use_expression=True, expression="S2 + 0.5 * S5",
                view=dict(show_inputs=False, fft_traces=["S2", "Result"], plot_detail="Full detail", fft_window="Rectangular"))


class SettingsTests(unittest.TestCase):
    def test_round_trip_preserves_results_and_ids(self):
        for mode in ("Continuous", "Discrete"):
            config = example(mode)
            restored = load_settings(dump_settings(config))
            self.assertEqual(restored, config)
            state = settings_state(restored)
            self.assertEqual(state["signal_ids"], [2, 5])
            self.assertEqual(state["next_signal_id"], 6)
            def output(settings):
                signals = {}
                for item in settings["signals"]:
                    _, values, _ = generate_signal(mode=settings["mode"], duration=settings["duration"], sampling_frequency=settings["sampling_frequency"], samples=settings["samples"], **{k:v for k,v in item.items() if k != "id"})
                    signals[f"S{item['id']}"] = values
                return evaluate_expression(settings["expression"], signals)
            np.testing.assert_array_equal(output(config), output(restored))

    def test_bad_files_and_limits(self):
        for content in (b"bad", b"[]", b"null", b"\xff", b" " * 65537):
            with self.assertRaises(ValueError):
                load_settings(content)
        changes = [{"version": 99}, {"mode": "bad"}, {"samples": True}, {"samples": 100001},
                   {"duration": -1}, {"duration": float("nan")}, {"duration": 100000},
                   {"signals": []}, {"signals": example()["signals"] * 2},
                   {"use_expression": True, "expression": "S99"},
                   {"view": {"fft_traces": ["S1"]}}, {"operation": "eval"}]
        for change in changes:
            data = example()
            data.update(change)
            before = copy.deepcopy(data)
            with self.subTest(change=change), self.assertRaises(ValueError):
                load_settings(json.dumps(data).encode())
            # Validation does not modify the supplied dictionaries.
            self.assertEqual(data["signals"], before["signals"])

    def test_restored_widgets(self):
        for mode in ("Continuous", "Discrete"):
            config = example(mode)
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30)
            for key, value in settings_state(config).items():
                app.session_state[key] = value
            app.run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            self.assertEqual(app.selectbox(key="signal_mode").value, mode)
            self.assertEqual(app.text_input(key="custom_expression").value, config["expression"])
            self.assertFalse(app.checkbox(key="show_inputs").value)
            self.assertEqual(app.multiselect(key="fft_traces").value, ["S2", "Result"])
            self.assertEqual(app.number_input(key="amp_5").value, 3.)
            app.button(key="add_signal").click().run()
            self.assertEqual(list(app.session_state["signal_ids"]), [2, 5, 6])
            self.assertFalse(app.exception)

    def test_load_without_file_keeps_setup(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
        app.number_input(key="amp_1").set_value(3.).run()
        app.button(key="load_settings").click().run()
        self.assertTrue(app.error)
        self.assertEqual(app.number_input(key="amp_1").value, 3.)
        self.assertFalse(app.exception)

    def test_upload_callback_is_atomic(self):
        import streamlit as st
        file = io.BytesIO(dump_settings(example("Discrete")))
        def uploader(*args, **kwargs):
            st.session_state[kwargs["key"]] = file
            return file
        with patch("streamlit.file_uploader", side_effect=uploader):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
            app.button(key="load_settings").click().run()
            self.assertEqual(list(app.session_state["signal_ids"]), [2, 5])
            self.assertEqual(app.selectbox(key="signal_mode").value, "Discrete")
            self.assertEqual(app.number_input(key="amp_5").value, 3.)
            self.assertFalse(app.exception)
            file = io.BytesIO(b'{"version":99}')
            app.run()
            app.button(key="load_settings").click().run()
            self.assertTrue(app.error)
            self.assertEqual(list(app.session_state["signal_ids"]), [2, 5])
            self.assertEqual(app.number_input(key="amp_5").value, 3.)
            self.assertFalse(app.exception)
