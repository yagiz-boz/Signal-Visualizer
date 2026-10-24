"""Browser-based Signal Visualizer. Run with streamlit run app.py."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from signal_processing import generate_signal, amplitude_spectrum, signal_csv

st.set_page_config(page_title="Signal Visualizer", page_icon="〰️", layout="wide")
st.title("Signal Visualizer")
st.caption("Explore signals, sampling and frequency spectra.")

with st.sidebar:
    st.header("Signal settings")
    mode = st.selectbox("Signal type", ["Continuous", "Discrete"])
    discrete = mode == "Discrete"
    waveform = "Sine" if discrete else st.selectbox("Waveform", ["Sine", "Cosine", "Square", "Sawtooth"])
    amplitude = st.number_input("Amplitude [V]", value=1.0)
    phase = st.number_input("Phase [deg]", value=0.0)
    if discrete:
        frequency = st.number_input("Angular frequency [rad/sample]", value=float(np.pi / 5), format="%.6f")
        samples = st.number_input("Number of samples", min_value=2, max_value=100000, value=100, step=1)
        duration, fs = 1.0, 1.0
    else:
        frequency = st.number_input("Frequency [Hz]", min_value=0.001, value=10.0)
        duration = st.number_input("Duration [s]", min_value=0.001, value=1.0)
        fs = st.number_input("Sampling frequency [Hz]", min_value=0.001, value=1000.0)
        samples = 100
    st.caption("Changes update the plots automatically. Maximum: 100,000 samples.")

try:
    axis, values, warnings = generate_signal(mode, waveform, amplitude, frequency, phase, duration, fs, samples)
    frequencies, magnitudes = amplitude_spectrum(values, fs, angular=discrete)
except ValueError as error:
    st.error(str(error))
    st.stop()

for warning in warnings:
    st.warning(warning)
cols = st.columns(3)
cols[0].metric("Samples", f"{len(values):,}")
cols[1].metric("RMS amplitude", f"{np.sqrt(np.mean(values**2)):.4g} V")
cols[2].metric("FFT bin spacing", f"{(frequencies[1] - frequencies[0]):.4g} {'rad/sample' if discrete else 'Hz'}")


def chart(x, y, title, xlabel, ylabel, markers=False):
    indices = np.arange(len(x))
    if len(x) > 20000:
        indices = np.linspace(0, len(x) - 1, 20000, dtype=int)
        st.caption(f"{title}: displaying 20,000 evenly spaced points. FFT and CSV use all samples.")
    fig = go.Figure(go.Scattergl(x=x[indices], y=y[indices],
                    mode="markers" if markers else "lines",
                    line=dict(color="#38bdf8"), marker=dict(color="#38bdf8", size=5)))
    fig.update_layout(title=title, xaxis_title=xlabel, yaxis_title=ylabel,
                      height=360, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, width="stretch")


chart(axis, values, "Time domain", "Sample index [n]" if discrete else "Time [s]", "Amplitude [V]", discrete)
chart(frequencies, magnitudes, "One-sided amplitude spectrum",
      "Angular frequency [rad/sample]" if discrete else "Frequency [Hz]", "Amplitude [V]", True)
st.caption("Rectangular window, no detrending. Non-integer cycles cause spectral leakage; peak-bin amplitude may be below the signal amplitude. DC and the even-length Nyquist bin are not doubled.")
st.download_button("Download signal CSV", signal_csv(axis, values, discrete),
                   file_name="signal.csv", mime="text/csv")
