import csv
import io
import unittest
import numpy as np
from signal_processing import combine_signals, signals_csv, generate_signal, amplitude_spectrum


class ArithmeticTests(unittest.TestCase):
    def test_operations_in_order(self):
        signals = [np.array([24., 48.]), np.array([3., 4.]), np.array([2., 3.])]
        expected = {"Add": [29, 55], "Subtract": [19, 41],
                    "Multiply": [144, 576], "Divide": [4, 4]}
        for operation, result in expected.items():
            np.testing.assert_allclose(combine_signals(signals, operation), result)
        np.testing.assert_array_equal(signals[0], [24, 48])
        for operation in expected:
            np.testing.assert_array_equal(combine_signals(signals[:1], operation), signals[0])

    def test_division_gaps_and_export(self):
        signals = [np.ones(4), np.array([0., 1e-12, -2., 2.])]
        result = combine_signals(signals, "Divide")
        self.assertTrue(np.all(np.isnan(result[:2])))
        np.testing.assert_allclose(result[2:], [-.5, .5])
        data = list(csv.reader(io.StringIO(signals_csv(np.arange(4), signals, ["S1", "S2"], result, True).decode())))
        self.assertEqual(data[0], ["sample_index", "S1", "S2", "result"])
        self.assertEqual(data[1][-1], "")
        self.assertEqual(len(data), 5)

    def test_shared_grid_and_mixing_spectrum(self):
        t, a, _ = generate_signal(frequency=10, sampling_frequency=1000)
        other_t, b, _ = generate_signal(frequency=30, sampling_frequency=1000)
        np.testing.assert_array_equal(t, other_t)
        _, summed = amplitude_spectrum(combine_signals([a, b]), 1000)
        np.testing.assert_allclose(summed[[10, 30]], [1, 1])
        _, mixed = amplitude_spectrum(combine_signals([a, b], "Multiply"), 1000)
        np.testing.assert_allclose(mixed[[20, 40]], [.5, .5])

    def test_bad_inputs_and_overflow(self):
        for signals in ([], [[1, 2], [1, 2, 3]], [[1, float("nan")]]):
            with self.assertRaises(ValueError):
                combine_signals(signals)
        with self.assertRaises(ValueError):
            combine_signals([[1, 2]], "Unknown")
        self.assertTrue(np.all(np.isnan(combine_signals([[1e308, 1e308]] * 2, "Multiply"))))
