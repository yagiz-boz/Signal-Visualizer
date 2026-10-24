"""Interactive multi-signal arithmetic on a shared sample grid."""
import re
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from settings import load_settings, dump_settings, settings_state
from signal_processing import generate_signal, amplitude_spectrum, combine_signals, signals_csv, evaluate_expression

st.set_page_config(page_title="Signal Visualizer", page_icon="〰️", layout="wide")
st.title("Signal Visualizer")
st.caption("Build signals on a shared sample grid and explore their combined spectrum.")
MAX_SIGNALS = 8
if "signal_ids" not in st.session_state:
    st.session_state.signal_ids = [1]
    st.session_state.next_signal_id = 2


def add_signal():
    if len(st.session_state.signal_ids) < MAX_SIGNALS:
        st.session_state.signal_ids.append(st.session_state.next_signal_id)
        if "fft_traces" in st.session_state:
            traces = list(st.session_state.fft_traces)
            new_name = f"S{st.session_state.next_signal_id}"
            traces.insert(traces.index("Result") if "Result" in traces else len(traces), new_name)
            st.session_state.fft_traces = traces
        st.session_state.next_signal_id += 1


def remove_signal(signal_id):
    if len(st.session_state.signal_ids) > 1:
        st.session_state.signal_ids.remove(signal_id)
        if "fft_traces" in st.session_state:
            st.session_state.fft_traces = [name for name in st.session_state.fft_traces if name != f"S{signal_id}"]




def restore_settings():
    uploaded = st.session_state.get("settings_upload")
    if uploaded is None:
        st.session_state.settings_message = (False, "Choose a JSON settings file first.")
        return
    try:
        restored = settings_state(load_settings(uploaded.getvalue()))
    except ValueError as error:
        st.session_state.settings_message = (False, str(error))
        return
    for key in list(st.session_state):
        if re.fullmatch(r"(?:wave|amp|phase|freq|omega|start_t|start_n|width_t|width_n)_\d+", key):
            del st.session_state[key]
    st.session_state.update(restored)
    st.session_state.settings_message = (True, "Settings loaded.")


with st.sidebar:
    with st.expander("Save / load settings"):
        st.file_uploader("Settings JSON", type=["json"], key="settings_upload")
        st.button("Load settings", key="load_settings", on_click=restore_settings)
        st.caption("Loading replaces the current setup. Maximum file size: 64 KB.")
        if "settings_message" in st.session_state:
            success, message = st.session_state.settings_message
            (st.success if success else st.error)(message)


with st.sidebar:
    st.header("Shared sampling settings")
    mode = st.selectbox("Signal type", ["Continuous", "Discrete"], key="signal_mode")
    discrete = mode == "Discrete"
    if discrete:
        samples = st.number_input("Number of samples", min_value=2, max_value=100000, value=100, step=1, key="shared_samples")
        duration, fs = 1.0, 1.0
    else:
        duration = st.number_input("Duration [s]", min_value=0.001, value=1.0, key="shared_duration")
        fs = st.number_input("Sampling frequency [Hz]", min_value=0.001, value=1000.0, key="shared_fs")
        samples = 100
    st.caption("All signals share the same sample grid. Maximum: 100,000 samples per signal.")
    st.header("Signals")
    st.button("Add signal", key="add_signal", on_click=add_signal, disabled=len(st.session_state.signal_ids) >= MAX_SIGNALS)
    st.caption(f"{len(st.session_state.signal_ids)} / {MAX_SIGNALS} signals")
    parameters = []
    for signal_id in st.session_state.signal_ids:
        name = f"S{signal_id}"
        with st.expander(name, expanded=True):
            waveform = st.selectbox("Waveform", ["Sine", "Cosine", "Square", "Sawtooth", "DC", "Triangle", "Unit step", "Pulse"], key=f"wave_{signal_id}")
            amplitude = st.number_input("Amplitude [V]", value=1.0, key=f"amp_{signal_id}")
            phase, frequency, start, pulse_width = 0.0, 0.0, 0.0, 1 if discrete else 0.1
            if waveform in ("Sine", "Cosine", "Square", "Sawtooth", "Triangle"):
                phase = st.number_input("Phase [deg]", value=0.0, key=f"phase_{signal_id}")
                if discrete:
                    frequency = st.number_input("Angular frequency [rad/sample]", value=float(np.pi / 5), format="%.6f", key=f"omega_{signal_id}")
                else:
                    frequency = st.number_input("Frequency [Hz]", min_value=0.001, value=10.0, key=f"freq_{signal_id}")
            elif waveform in ("Unit step", "Pulse"):
                if discrete:
                    start = st.number_input("Start sample [n]", value=0, step=1, key=f"start_n_{signal_id}")
                    if waveform == "Pulse":
                        pulse_width = st.number_input("Pulse width [samples]", min_value=1, value=1, step=1, key=f"width_n_{signal_id}")
                else:
                    start = st.number_input("Start time [s]", value=0.25, key=f"start_t_{signal_id}")
                    if waveform == "Pulse":
                        pulse_width = st.number_input("Pulse width [s]", min_value=0.000001, value=0.1, format="%.6f", key=f"width_t_{signal_id}")
                st.caption("Step includes its start sample. Pulse includes its start and excludes its end; a one-sample discrete pulse is an impulse.")
            else:
                st.caption("DC is constant at the selected amplitude.")

            st.button(f"Remove {name}", key=f"remove_{signal_id}", on_click=remove_signal,
                      args=(signal_id,), disabled=len(st.session_state.signal_ids) == 1)
            parameters.append((name, waveform, amplitude, frequency, phase, start, pulse_width))

operation = st.selectbox("Operation", ["Add", "Subtract", "Multiply", "Divide"], key="operation", disabled=st.session_state.get("use_expression", False))
symbols = {"Add": "+", "Subtract": "−", "Multiply": "×", "Divide": "/"}
names = [p[0] for p in parameters]
expression = names[0]
for name in names[1:]:
    expression = f"({expression} {symbols[operation]} {name})"
use_expression = st.checkbox("Use custom expression", key="use_expression")
if use_expression:
    expression = st.text_input("Expression", value=expression.replace("−", "-").replace("×", "*"), key="custom_expression", max_chars=256)
    st.caption(f"Available signals: {', '.join(names)}. Use + - * / and parentheses, for example (S1 + S2) * 0.5. Multiplication and division take precedence over addition and subtraction.")
st.subheader(f"Result = {expression}")
if not use_expression:
    st.caption("Operations run from left to right in signal order. With one signal, the result is that signal.")

signals = []
try:
    for name, waveform, amplitude, frequency, phase, start, pulse_width in parameters:
        axis, values, warnings = generate_signal(mode, waveform, amplitude, frequency, phase, duration, fs, samples, start, pulse_width)
        signals.append(values)
        for warning in warnings:
            st.warning(f"{name}: {warning}")
    result = evaluate_expression(expression, dict(zip(names, signals))) if use_expression else combine_signals(signals, operation)
except ValueError as error:
    st.error(str(error))
    st.stop()

valid = np.isfinite(result)
if not np.all(valid):
    st.warning(f"{np.count_nonzero(~valid):,} result samples are undefined. Division skips denominators with absolute value ≤ 1e-10. Undefined or overflowing values appear as plot gaps and empty CSV cells.")
if (use_expression and any(symbol in expression for symbol in "*/")) or (not use_expression and len(signals) > 1 and operation in ("Multiply", "Divide")):
    st.info("Multiplication and division can introduce additional frequency components. Input sampling warnings alone do not guarantee an alias-free result.")
cols = st.columns(3)
cols[0].metric("Samples", f"{len(result):,}")
if np.all(valid):
    scale = np.max(np.abs(result))
    rms = scale * np.sqrt(np.mean((result / scale) ** 2)) if scale else 0.0
    cols[1].metric("Result RMS", f"{rms:.4g}")
else:
    cols[1].metric("Result RMS", "Unavailable")
cols[2].metric("FFT bin spacing", f"{(2 * np.pi if discrete else fs) / len(result):.4g} {'rad/sample' if discrete else 'Hz'}")


def chart(x, series, title, xlabel, markers=False):
    indices = np.arange(len(x))
    if len(x) > 20000:
        indices = np.linspace(0, len(x) - 1, 20000, dtype=int)
        st.caption(f"{title}: displaying 20,000 evenly spaced points. FFT and CSV use all samples.")
    fig = go.Figure()
    palette = ["#38bdf8", "#a78bfa", "#34d399", "#fb7185", "#facc15", "#22d3ee", "#e879f9", "#94a3b8"]
    for name, values in series:
        color = "#f97316" if name == "Result" else palette[(int(name[1:]) - 1) % len(palette)]
        fig.add_trace(go.Scattergl(x=x[indices], y=values[indices], name=name,
                                  mode="markers" if markers else "lines", connectgaps=False,
                                  marker=dict(color=color), line=dict(color=color)))
    fig.update_layout(title=title, xaxis_title=xlabel, yaxis_title="Amplitude",
                      height=360, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, width="stretch")


show_inputs = st.checkbox("Show input signals", value=True, key="show_inputs")
series = list(zip(names, signals)) if show_inputs else []
chart(axis, series + [("Result", result)], "Time domain",
      "Sample index [n]" if discrete else "Time [s]", discrete)
st.subheader("Frequency comparison")
selected_spectra = st.multiselect("Spectra to compare", names + ["Result"],
                                  default=names + ["Result"], key="fft_traces")
spectra = []
for name, values in list(zip(names, signals)) + [("Result", result)]:
    if name in selected_spectra and (name != "Result" or np.all(valid)):
        frequencies, magnitudes = amplitude_spectrum(values, fs, angular=discrete)
        spectra.append((name, magnitudes))
if spectra:
    chart(frequencies, spectra, "One-sided amplitude spectra",
          "Angular frequency [rad/sample]" if discrete else "Frequency [Hz]", True)
elif not selected_spectra:
    st.info("Select at least one signal to display its spectrum.")
if not np.all(valid):
    st.info("Result FFT is unavailable because some samples are undefined. Adjust denominator signals; missing samples are not replaced with zeros.")
st.caption("Input and result spectra share the same frequency bins and normalization. Trace colors match the time plot. Inputs are in V; result units depend on the operation, so numerical amplitudes may represent different units.")
st.caption("Click a legend entry to toggle a trace. Result amplitude units depend on the operation. FFT uses a rectangular window without detrending; non-integer cycles cause spectral leakage. DC and the even-length Nyquist bin are not doubled.")
st.download_button("Download signals CSV", signals_csv(axis, signals, names, result, discrete),
                   file_name="signals.csv", mime="text/csv")


configuration = dict(
    version=1, mode=mode, duration=duration, sampling_frequency=fs, samples=int(samples),
    signals=[dict(id=int(name[1:]), waveform=waveform, amplitude=amplitude,
                  frequency=frequency, phase=phase,
                  start=int(start) if discrete else start,
                  pulse_width=int(width) if discrete else width)
             for name, waveform, amplitude, frequency, phase, start, width in parameters],
    operation=operation, use_expression=use_expression,
    expression=expression.replace("−", "-").replace("×", "*"),
    view=dict(show_inputs=show_inputs, fft_traces=selected_spectra))
with st.sidebar:
    st.download_button("Save settings JSON", dump_settings(configuration),
                       file_name="signal-settings.json", mime="application/json")
