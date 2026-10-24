"""Signal generation and correctly normalized one-sided amplitude spectra."""
import csv
import io
import numpy as np

MAX_SAMPLES = 100_000


def generate_signal(mode="Continuous", waveform="Sine", amplitude=1.0,
                    frequency=10.0, phase=0.0, duration=1.0,
                    sampling_frequency=1000.0, samples=100):
    """Return axis, samples and warnings; phase is in degrees.

    Continuous mode samples [0, duration); discrete frequency is rad/sample.
    """
    if mode not in ("Continuous", "Discrete"):
        raise ValueError("Unknown signal type.")
    if not all(np.isfinite(v) for v in (amplitude, frequency, phase)):
        raise ValueError("Amplitude, frequency and phase must be finite.")
    warnings = []
    if mode == "Continuous":
        if not all(np.isfinite(v) and v > 0 for v in
                   (frequency, duration, sampling_frequency)):
            raise ValueError("Frequency, duration and sampling frequency must be positive and finite.")
        count = duration * sampling_frequency
        if not np.isfinite(count) or count > MAX_SAMPLES:
            raise ValueError(f"Use at most {MAX_SAMPLES:,} samples; reduce duration or sampling frequency.")
        count = int(np.ceil(count))
        if count < 2:
            raise ValueError("At least two samples are required.")
        axis = np.arange(count) / sampling_frequency
        cycles = frequency * axis + (phase % 360) / 360
        if sampling_frequency <= 2 * frequency:
            warnings.append("Sampling at or below twice the fundamental frequency can lose information. Increase the sampling frequency above twice the fundamental.")
        if waveform in ("Square", "Sawtooth"):
            warnings.append("Ideal square and sawtooth waves contain infinitely many harmonics. Any finite sampling rate aliases some harmonics; sampling above twice the fundamental alone is insufficient.")
    else:
        if not np.isfinite(samples) or int(samples) != samples or not 2 <= samples <= MAX_SAMPLES:
            raise ValueError(f"Sample count must be an integer from 2 to {MAX_SAMPLES:,}.")
        axis = np.arange(int(samples))
        cycles = (frequency / (2 * np.pi)) * axis + (phase % 360) / 360
        waveform = "Sine"
        if abs(frequency) >= np.pi:
            warnings.append("Discrete angular frequencies repeat every 2π rad/sample. This frequency folds into the principal interval [-π, π].")
    angle = 2 * np.pi * cycles
    if waveform == "Sine":
        values = np.sin(angle)
    elif waveform == "Cosine":
        values = np.cos(angle)
    elif waveform == "Square":
        values = np.where(cycles % 1 < 0.5, 1.0, -1.0)
    elif waveform == "Sawtooth":
        values = 2 * (cycles % 1) - 1
    else:
        raise ValueError("Unknown waveform.")
    return axis, amplitude * values, warnings


def amplitude_spectrum(values, sampling_frequency=1.0, angular=False):
    """Rectangular-window rFFT; double interior bins, never DC or Nyquist."""
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or values.size < 2 or not np.all(np.isfinite(values)):
        raise ValueError("Provide at least two finite, real samples.")
    if not np.isfinite(sampling_frequency) or sampling_frequency <= 0:
        raise ValueError("Sampling frequency must be positive and finite.")
    magnitude = np.abs(np.fft.rfft(values)) / values.size
    magnitude[1:-1 if values.size % 2 == 0 else None] *= 2
    frequency = np.fft.rfftfreq(values.size, d=1 / sampling_frequency)
    return frequency * (2 * np.pi if angular else 1), magnitude


def signal_csv(axis, values, discrete=False):
    """Export all generated samples, independently of plot display limits."""
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["sample_index" if discrete else "time_s", "amplitude_V"])
    writer.writerows(zip(axis, values))
    return output.getvalue().encode("utf-8")


def combine_signals(signals, operation="Add", denominator_tolerance=1e-10):
    """Apply pointwise arithmetic left to right; invalid results become NaN."""
    arrays = [np.asarray(signal, dtype=float) for signal in signals]
    if not arrays or any(a.ndim != 1 or a.size < 2 or not np.all(np.isfinite(a)) for a in arrays):
        raise ValueError("Provide at least one signal with two or more finite samples.")
    if any(a.shape != arrays[0].shape for a in arrays):
        raise ValueError("Signals must share the same sample grid and length.")
    if operation not in ("Add", "Subtract", "Multiply", "Divide"):
        raise ValueError("Unknown operation.")
    if not np.isfinite(denominator_tolerance) or denominator_tolerance < 0:
        raise ValueError("Denominator tolerance must be finite and nonnegative.")
    result = arrays[0].copy()
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        for signal in arrays[1:]:
            if operation == "Add":
                result += signal
            elif operation == "Subtract":
                result -= signal
            elif operation == "Multiply":
                result *= signal
            else:
                result = np.divide(result, signal, out=np.full_like(result, np.nan),
                                   where=np.abs(signal) > denominator_tolerance)
            result[~np.isfinite(result)] = np.nan
    return result


def signals_csv(axis, signals, names, result, discrete=False):
    """Export aligned inputs and result, with blank undefined-value cells."""
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["sample_index" if discrete else "time_s", *names, "result"])
    for row in zip(axis, *signals, result):
        writer.writerow([v if np.isfinite(v) else "" for v in row])
    return output.getvalue().encode("utf-8")
