"""Interactive multi-signal arithmetic on a shared sample grid."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from signal_processing import generate_signal, amplitude_spectrum, combine_signals, signals_csv

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
        st.session_state.next_signal_id += 1


def remove_signal(signal_id):
    if len(st.session_state.signal_ids) > 1:
        st.session_state.signal_ids.remove(signal_id)


with st.sidebar:
    st.header("Shared sampling settings")
    mode = st.selectbox("Signal type", ["Continuous", "Discrete"], key="signal_mode")
    discrete = mode == "Discrete"
    if discrete:
        samples = st.number_input("Number of samples", min_value=2, max_value=100000, value=100, step=1)
        duration, fs = 1.0, 1.0
    else:
        duration = st.number_input("Duration [s]", min_value=0.001, value=1.0)
        fs = st.number_input("Sampling frequency [Hz]", min_value=0.001, value=1000.0)
        samples = 100
    st.caption("All signals share the same sample grid. Maximum: 100,000 samples per signal.")
    st.header("Signals")
    st.button("Add signal", on_click=add_signal, disabled=len(st.session_state.signal_ids) >= MAX_SIGNALS)
    st.caption(f"{len(st.session_state.signal_ids)} / {MAX_SIGNALS} signals")
    parameters = []
    for signal_id in st.session_state.signal_ids:
        name = f"S{signal_id}"
        with st.expander(name, expanded=True):
            waveform = "Sine" if discrete else st.selectbox("Waveform", ["Sine", "Cosine", "Square", "Sawtooth"], key=f"wave_{signal_id}")
            amplitude = st.number_input("Amplitude [V]", value=1.0, key=f"amp_{signal_id}")
            phase = st.number_input("Phase [deg]", value=0.0, key=f"phase_{signal_id}")
            if discrete:
                frequency = st.number_input("Angular frequency [rad/sample]", value=float(np.pi / 5), format="%.6f", key=f"omega_{signal_id}")
            else:
                frequency = st.number_input("Frequency [Hz]", min_value=0.001, value=10.0, key=f"freq_{signal_id}")
            st.button(f"Remove {name}", key=f"remove_{signal_id}", on_click=remove_signal,
                      args=(signal_id,), disabled=len(st.session_state.signal_ids) == 1)
            parameters.append((name, waveform, amplitude, frequency, phase))

operation = st.selectbox("Operation", ["Add", "Subtract", "Multiply", "Divide"], key="operation")
symbols = {"Add": "+", "Subtract": "−", "Multiply": "×", "Divide": "/"}
names = [p[0] for p in parameters]
expression = names[0]
for name in names[1:]:
    expression = f"({expression} {symbols[operation]} {name})"
st.subheader(f"Result = {expression}")
st.caption("Operations run from left to right in signal order. With one signal, the result is that signal.")

signals = []
try:
    for name, waveform, amplitude, frequency, phase in parameters:
        axis, values, warnings = generate_signal(mode, waveform, amplitude, frequency, phase, duration, fs, samples)
        signals.append(values)
        for warning in warnings:
            st.warning(f"{name}: {warning}")
    result = combine_signals(signals, operation)
except ValueError as error:
    st.error(str(error))
    st.stop()

valid = np.isfinite(result)
if not np.all(valid):
    st.warning(f"{np.count_nonzero(~valid):,} result samples are undefined. Division skips denominators with absolute value ≤ 1e-10. Undefined or overflowing values appear as plot gaps and empty CSV cells.")
if len(signals) > 1 and operation in ("Multiply", "Divide"):
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
    for name, values in series:
        fig.add_trace(go.Scattergl(x=x[indices], y=values[indices], name=name,
                                  mode="markers" if markers else "lines", connectgaps=False))
    fig.update_layout(title=title, xaxis_title=xlabel, yaxis_title="Amplitude",
                      height=360, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, width="stretch")


show_inputs = st.checkbox("Show input signals", value=True)
series = list(zip(names, signals)) if show_inputs else []
chart(axis, series + [("Result", result)], "Time domain",
      "Sample index [n]" if discrete else "Time [s]", discrete)
if np.all(valid):
    frequencies, magnitudes = amplitude_spectrum(result, fs, angular=discrete)
    chart(frequencies, [("Result", magnitudes)], "Result: one-sided amplitude spectrum",
          "Angular frequency [rad/sample]" if discrete else "Frequency [Hz]", True)
else:
    st.info("Result FFT is unavailable because some samples are undefined. Adjust denominator signals; missing samples are not replaced with zeros.")
st.caption("Click a legend entry to toggle a trace. Result amplitude units depend on the operation. FFT uses a rectangular window without detrending; non-integer cycles cause spectral leakage. DC and the even-length Nyquist bin are not doubled.")
st.download_button("Download signals CSV", signals_csv(axis, signals, names, result, discrete),
                   file_name="signals.csv", mime="text/csv")
