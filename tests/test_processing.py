import csv
import io
import unittest
import numpy as np
from signal_processing import amplitude_spectrum, generate_signal, signal_csv


class SignalTests(unittest.TestCase):
    def test_dc_and_nyquist_scaling(self):
        _, magnitude = amplitude_spectrum(np.ones(100) * 3)
        self.assertAlmostEqual(magnitude[0], 3)
        f, magnitude = amplitude_spectrum(2 * (-1.) ** np.arange(100), 100)
        self.assertEqual(f[-1], 50)
        self.assertAlmostEqual(magnitude[-1], 2)

    def test_sinusoid_even_and_odd(self):
        for size in (100, 101):
            for k in (7, size // 2):
                values = 2.5 * np.cos(2 * np.pi * k * np.arange(size) / size)
                _, magnitude = amplitude_spectrum(values)
                self.assertAlmostEqual(magnitude[k], 2.5)

    def test_parseval(self):
        for size in (99, 100):
            values = np.random.default_rng(42).normal(size=size)
            _, mag = amplitude_spectrum(values)
            energy = mag[0] ** 2 + sum(mag[1:] ** 2) / 2
            if size % 2 == 0:
                energy += mag[-1] ** 2 / 2
            self.assertAlmostEqual(energy, np.mean(values ** 2))

    def test_generation_and_csv(self):
        for waveform in ("Sine", "Cosine", "Square", "Sawtooth"):
            axis, values, _ = generate_signal(waveform=waveform, duration=.105, sampling_frequency=100)
            self.assertEqual(len(axis), 11)
            self.assertTrue(np.all(axis < .105))
            rows = list(csv.reader(io.StringIO(signal_csv(axis, values).decode())))
            self.assertEqual(len(rows), 12)
        axis, values, warnings = generate_signal(mode="Discrete", frequency=4, samples=101)
        self.assertTrue(warnings)
        f, _ = amplitude_spectrum(values, angular=True)
        self.assertLessEqual(f[-1], np.pi)

    def test_validation_and_warnings(self):
        for kwargs in ({"duration": -1}, {"samples": 1, "mode": "Discrete"},
                       {"amplitude": float("nan")}, {"duration": 1000},
                       {"duration": .001, "sampling_frequency": 1}):
            with self.assertRaises(ValueError):
                generate_signal(**kwargs)
        self.assertTrue(generate_signal(frequency=50, sampling_frequency=100)[2])
        self.assertTrue(generate_signal(waveform="Square")[2])


if __name__ == "__main__":
    unittest.main()
