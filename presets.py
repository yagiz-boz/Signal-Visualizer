"""Reproducible starting points for signal-processing experiments."""
from copy import deepcopy


def signal(i, frequency, waveform="Sine", amplitude=1., phase=0.):
    return dict(id=i, waveform=waveform, amplitude=amplitude, frequency=frequency,
                phase=phase, start=0., pulse_width=.1)


def setup(signals, duration=1., fs=200., expression="", operation="Add"):
    return dict(version=1, mode="Continuous", duration=duration,
                sampling_frequency=fs, samples=100, signals=signals,
                operation=operation, use_expression=bool(expression), expression=expression,
                view=dict(show_inputs=True, fft_traces=[f"S{s['id']}" for s in signals] + ["Result"],
                          plot_detail="Full detail", fft_window="Rectangular"))


EXPERIMENTS = {
    "Beats": {
        "settings": setup([signal(1, 10.), signal(2, 11.)], duration=3.),
        "guide": "Two equal-amplitude tones at 10 and 11 Hz produce beats at 1 Hz (the frequency difference). Observe the changing envelope in the time plot and the two peaks in the spectrum. Change one frequency to alter the beat rate.",
    },
    "Phase cancellation": {
        "settings": setup([signal(1, 10.), signal(2, 10., phase=180.)]),
        "guide": "Two equal-amplitude 10 Hz sine waves differ by 180 degrees. Their sum is approximately zero; tiny residuals come from floating-point arithmetic. Input spectra still show the tones. Change S2 phase or amplitude to break cancellation.",
    },
    "Amplitude modulation": {
        "settings": setup([signal(1, 40., waveform="Cosine"), signal(2, 5., waveform="Cosine", amplitude=.5)],
                          fs=400., expression="(1 + S2) * S1"),
        "guide": "A 40 Hz carrier is modulated by a 5 Hz tone with modulation index 0.5. The result has a carrier at 40 Hz (amplitude 1) and sidebands at 35 and 45 Hz (amplitude 0.25 each). Hide input traces to inspect the result envelope.",
    },
    "Aliasing": {
        "settings": setup([signal(1, 70., waveform="Cosine")], fs=100.),
        "guide": "A 70 Hz cosine sampled at 100 Hz appears at 30 Hz: |70 - 100|. The Nyquist limit is 50 Hz. The plot shows sampled data, so it cannot reconstruct the original 70 Hz wave. Increase sampling above 140 Hz to observe the original tone in the spectrum.",
    },
    "Spectral leakage": {
        "settings": setup([signal(1, 10.5)]),
        "guide": "A 10.5 Hz tone observed for 1 second falls between 1 Hz FFT bins. Rectangular spreads energy into distant bins. Switch FFT window to Hann or Hamming to reduce distant leakage; peaks broaden and amplitude error can remain. Try 10 Hz for an integer-cycle comparison.",
    },
}


def experiment_settings(name):
    """Return an independent settings object so editing cannot alter a preset."""
    if name not in EXPERIMENTS:
        raise ValueError("Choose an experiment first.")
    return deepcopy(EXPERIMENTS[name]["settings"])
