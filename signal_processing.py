"""Signal generation and correctly normalized one-sided amplitude spectra."""
import csv
import io
import numpy as np

MAX_SAMPLES = 100_000


def generate_signal(mode="Continuous", waveform="Sine", amplitude=1.0,
                    frequency=10.0, phase=0.0, duration=1.0,
                    sampling_frequency=1000.0, samples=100,
                    start=0.0, pulse_width=None):
    """Return axis, sampled waveform and warnings; phase is in degrees.

    Start/width use seconds in continuous mode and integer sample counts in
    discrete mode. Pulse is rectangular, not a continuous Dirac impulse.
    """
    periodic = waveform in ("Sine", "Cosine", "Square", "Sawtooth", "Triangle")
    if mode not in ("Continuous", "Discrete"):
        raise ValueError("Unknown signal type.")
    if not periodic and waveform not in ("DC", "Unit step", "Pulse"):
        raise ValueError("Unknown waveform.")
    if not np.isfinite(amplitude):
        raise ValueError("Amplitude must be finite.")
    if periodic and not all(np.isfinite(v) for v in (frequency, phase)):
        raise ValueError("Frequency and phase must be finite.")
    warnings = []
    if mode == "Continuous":
        if not all(np.isfinite(v) and v > 0 for v in (duration, sampling_frequency)):
            raise ValueError("Duration and sampling frequency must be positive and finite.")
        if periodic and frequency <= 0:
            raise ValueError("Frequency must be positive.")
        count = duration * sampling_frequency
        if not np.isfinite(count) or count > MAX_SAMPLES:
            raise ValueError(f"Use at most {MAX_SAMPLES:,} samples; reduce duration or sampling frequency.")
        count = int(np.ceil(count))
        if count < 2:
            raise ValueError("At least two samples are required.")
        axis = np.arange(count) / sampling_frequency
        if periodic:
            cycles = frequency * axis + (phase % 360) / 360
            if sampling_frequency <= 2 * frequency:
                warnings.append("Sampling at or below twice the fundamental frequency can lose information. Increase the sampling frequency above twice the fundamental.")
            if waveform in ("Square", "Sawtooth", "Triangle"):
                warnings.append("Ideal square, sawtooth and triangle waves contain infinitely many harmonics. Any finite sampling rate aliases some harmonics; sampling above twice the fundamental alone is insufficient.")
    else:
        if not np.isfinite(samples) or int(samples) != samples or not 2 <= samples <= MAX_SAMPLES:
            raise ValueError(f"Sample count must be an integer from 2 to {MAX_SAMPLES:,}.")
        axis = np.arange(int(samples))
        if periodic:
            cycles = (frequency / (2 * np.pi)) * axis + (phase % 360) / 360
            if abs(frequency) >= np.pi:
                warnings.append("Discrete angular frequencies repeat every 2π rad/sample. This frequency folds into the principal interval [-π, π].")

    if waveform in ("Unit step", "Pulse"):
        if not np.isfinite(start) or (mode == "Discrete" and int(start) != start):
            raise ValueError("Start must be finite; discrete start must be an integer sample index.")
        if waveform == "Pulse":
            if pulse_width is None:
                pulse_width = 1 if mode == "Discrete" else 0.1
            if not np.isfinite(pulse_width) or pulse_width <= 0 or (mode == "Discrete" and int(pulse_width) != pulse_width):
                raise ValueError("Pulse width must be positive and finite; discrete width must be an integer.")
            values = ((axis >= start) & (axis < start + pulse_width)).astype(float)
            if not np.any(values):
                warnings.append("The pulse contains no sampled points. Adjust its start or width, or increase the sampling rate or observation length.")
        else:
            values = (axis >= start).astype(float)
        if mode == "Continuous":
            warnings.append("Ideal steps and rectangular pulses are not band-limited. Sampling can miss transitions or narrow pulses.")
    elif waveform == "DC":
        values = np.ones(len(axis))
    elif waveform == "Sine":
        values = np.sin(2 * np.pi * cycles)
    elif waveform == "Cosine":
        values = np.cos(2 * np.pi * cycles)
    elif waveform == "Square":
        values = np.where(cycles % 1 < 0.5, 1.0, -1.0)
    elif waveform == "Sawtooth":
        values = 2 * (cycles % 1) - 1
    else:
        values = 1 - 4 * np.abs((cycles % 1) - 0.5)
    return axis, amplitude * values, warnings



def amplitude_spectrum(values, sampling_frequency=1.0, angular=False, window="Rectangular"):
    """One-sided rFFT amplitude, normalized by window sum (coherent gain).

    Hann/Hamming are periodic FFT windows. Interior bins are doubled, never
    DC or even-length Nyquist. This is an amplitude spectrum, not a PSD.
    """
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or values.size < 2 or not np.all(np.isfinite(values)):
        raise ValueError("Provide at least two finite, real samples.")
    if not np.isfinite(sampling_frequency) or sampling_frequency <= 0:
        raise ValueError("Sampling frequency must be positive and finite.")
    if window == "Rectangular":
        weights = np.ones(values.size)
    elif window == "Hann":
        weights = np.hanning(values.size + 1)[:-1]
    elif window == "Hamming":
        weights = np.hamming(values.size + 1)[:-1]
    else:
        raise ValueError("Unknown FFT window. Choose Rectangular, Hann or Hamming.")
    magnitude = np.abs(np.fft.rfft(values * weights)) / weights.sum()
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


def evaluate_expression(expression, signals, denominator_tolerance=1e-10):
    """Evaluate only names, finite numbers, + - * /, unary signs and parentheses.

    No Python evaluation or function calls are allowed. Division and overflow
    use the same undefined-sample policy as the operation picker.
    """
    import ast

    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("Enter an expression, for example S1 + S2.")
    if len(expression) > 256:
        raise ValueError("Keep expressions within 256 characters.")
    if not signals:
        raise ValueError("Add at least one signal.")
    arrays = {name: np.asarray(values, dtype=float) for name, values in signals.items()}
    shape = next(iter(arrays.values())).shape
    if len(shape) != 1 or shape[0] < 2 or any(a.shape != shape or not np.all(np.isfinite(a)) for a in arrays.values()):
        raise ValueError("Signals must contain finite samples on the same sample grid.")
    if not np.isfinite(denominator_tolerance) or denominator_tolerance < 0:
        raise ValueError("Denominator tolerance must be finite and nonnegative.")
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except (SyntaxError, RecursionError) as error:
        raise ValueError("Invalid expression. Use signal names, numbers, + - * / and parentheses.") from error
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Load,
               ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.UAdd, ast.USub)
    nodes = list(ast.walk(tree))
    if len(nodes) > 128:
        raise ValueError("Expression is too complex; use fewer operations.")
    for node in nodes:
        if not isinstance(node, allowed):
            raise ValueError("Only signal names, numbers, + - * / and parentheses are supported.")
        if isinstance(node, ast.Name) and node.id not in arrays:
            raise ValueError(f"Unknown signal '{node.id}'. Available signals: {', '.join(arrays)}.")
        if isinstance(node, ast.Constant):
            try:
                valid = type(node.value) in (int, float) and np.isfinite(float(node.value))
            except (ValueError, OverflowError):
                valid = False
            if not valid:
                raise ValueError("Use finite numeric constants only.")

    def visit(node):
        if isinstance(node, ast.Name):
            return arrays[node.id].copy()
        if isinstance(node, ast.Constant):
            return np.full(shape, float(node.value))
        if isinstance(node, ast.UnaryOp):
            value = visit(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        left, right = visit(node.left), visit(node.right)
        if isinstance(node.op, ast.Add):
            result = left + right
        elif isinstance(node.op, ast.Sub):
            result = left - right
        elif isinstance(node.op, ast.Mult):
            result = left * right
        else:
            result = np.divide(left, right, out=np.full(shape, np.nan),
                               where=np.abs(right) > denominator_tolerance)
        result[~np.isfinite(result)] = np.nan
        return result

    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        return visit(tree.body)
