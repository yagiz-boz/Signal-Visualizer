"""Versioned JSON settings, validated before any session state changes."""
import json
import math
from signal_processing import generate_signal, evaluate_expression

MAX_SETTINGS_BYTES = 65536


def validate_settings(data):
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("Unsupported settings file. Expected version 1.")
    mode = data.get("mode")
    if mode not in ("Continuous", "Discrete"):
        raise ValueError("Invalid signal mode.")

    def number(obj, key, minimum=None, integer=False):
        value = obj.get(key)
        if type(value) not in (int, float) or (integer and type(value) is not int):
            raise ValueError(f"Invalid numeric setting: {key}.")
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite or (minimum is not None and value < minimum):
            raise ValueError(f"Invalid numeric setting: {key}.")
        return value

    duration = number(data, "duration", .001)
    fs = number(data, "sampling_frequency", .001)
    samples = number(data, "samples", 2, integer=True)
    if samples > 100000:
        raise ValueError("Use at most 100,000 samples.")
    signals = data.get("signals")
    if not isinstance(signals, list) or not 1 <= len(signals) <= 8:
        raise ValueError("Settings must contain 1 to 8 signals.")
    normalized, ids, values = [], [], {}
    for signal in signals:
        if not isinstance(signal, dict):
            raise ValueError("Invalid signal settings.")
        signal_id = number(signal, "id", 1, integer=True)
        if signal_id > 1000000 or signal_id in ids:
            raise ValueError("Signal identifiers must be unique positive integers up to 1,000,000.")
        waveform = signal.get("waveform")
        if waveform not in ("Sine", "Cosine", "Square", "Sawtooth", "DC", "Triangle", "Unit step", "Pulse"):
            raise ValueError("Unknown waveform.")
        amplitude = number(signal, "amplitude")
        frequency = number(signal, "frequency")
        phase = number(signal, "phase")
        start = number(signal, "start", integer=mode == "Discrete")
        width = number(signal, "pulse_width", 1 if mode == "Discrete" else .000001, integer=mode == "Discrete")
        if waveform in ("Sine", "Cosine", "Square", "Sawtooth", "Triangle") and mode == "Continuous" and frequency < .001:
            raise ValueError("Continuous frequency must be at least 0.001 Hz.")
        _, generated, _ = generate_signal(mode, waveform, amplitude, frequency, phase, duration, fs, samples, start, width)
        values[f"S{signal_id}"] = generated
        ids.append(signal_id)
        normalized.append(dict(id=signal_id, waveform=waveform, amplitude=amplitude,
                               frequency=frequency, phase=phase, start=start, pulse_width=width))
    operation = data.get("operation")
    if operation not in ("Add", "Subtract", "Multiply", "Divide"):
        raise ValueError("Unknown operation.")
    use_expression, expression = data.get("use_expression"), data.get("expression")
    if type(use_expression) is not bool or not isinstance(expression, str) or len(expression) > 256:
        raise ValueError("Invalid expression settings.")
    if use_expression:
        evaluate_expression(expression, values)
    view = data.get("view", {})
    if not isinstance(view, dict) or type(view.get("show_inputs", True)) is not bool:
        raise ValueError("Invalid plot settings.")
    plot_detail = view.get("plot_detail", "Full detail")
    if plot_detail not in ("Full detail", "Overview"):
        raise ValueError("Invalid plot detail setting.")
    fft_window = view.get("fft_window", "Rectangular")
    if fft_window not in ("Rectangular", "Hann", "Hamming"):
        raise ValueError("Invalid FFT window setting.")
    traces = view.get("fft_traces", list(values) + ["Result"])
    if not isinstance(traces, list) or any(not isinstance(t, str) or t not in [*values, "Result"] for t in traces):
        raise ValueError("Invalid spectrum selection.")
    return dict(version=1, mode=mode, duration=float(duration), sampling_frequency=float(fs),
                samples=samples, signals=normalized, operation=operation,
                use_expression=use_expression, expression=expression,
                view=dict(show_inputs=view.get("show_inputs", True), fft_traces=list(dict.fromkeys(traces)), plot_detail=plot_detail, fft_window=fft_window))


def load_settings(content):
    if len(content) > MAX_SETTINGS_BYTES:
        raise ValueError("Settings file must be at most 64 KB.")
    try:
        data = json.loads(content)
        return validate_settings(data)
    except (UnicodeError, json.JSONDecodeError, RecursionError, TypeError, OverflowError) as error:
        raise ValueError("Invalid settings JSON file.") from error


def dump_settings(data):
    return json.dumps(validate_settings(data), indent=2, allow_nan=False).encode("utf-8")


def settings_state(data):
    """Build state atomically after validation; caller applies returned mapping."""
    config = validate_settings(data)
    state = dict(signal_ids=[s["id"] for s in config["signals"]],
                 next_signal_id=max(s["id"] for s in config["signals"]) + 1,
                 signal_mode=config["mode"], shared_duration=config["duration"],
                 shared_fs=config["sampling_frequency"], shared_samples=config["samples"],
                 operation=config["operation"], use_expression=config["use_expression"],
                 custom_expression=config["expression"], show_inputs=config["view"]["show_inputs"],
                 fft_traces=config["view"]["fft_traces"], plot_detail=config["view"]["plot_detail"], fft_window=config["view"]["fft_window"])
    discrete = config["mode"] == "Discrete"
    for signal in config["signals"]:
        i = signal["id"]
        state.update({f"wave_{i}": signal["waveform"], f"amp_{i}": float(signal["amplitude"]),
                      f"phase_{i}": float(signal["phase"]),
                      f"{'omega' if discrete else 'freq'}_{i}": float(signal["frequency"]) if signal["waveform"] in ("Sine", "Cosine", "Square", "Sawtooth", "Triangle") else (0.6283185307179586 if discrete else 10.0),
                      f"start_{'n' if discrete else 't'}_{i}": int(signal["start"]) if discrete else float(signal["start"]),
                      f"width_{'n' if discrete else 't'}_{i}": int(signal["pulse_width"]) if discrete else float(signal["pulse_width"])})
    return state
