# Signal Visualizer

A browser-based signal processing demo built with Streamlit, Plotly and NumPy.

**[Open the live demo](https://signal-visualizer-yagiz-boz.streamlit.app/)**

Web app development uses the `main` branch on GitHub.

## Features

- Sine, cosine, square, sawtooth, triangle, DC, unit step and rectangular pulse signals.
- All waveforms available in continuous and discrete modes; periodic discrete frequencies use rad/sample.
- Add and remove up to eight signals with independent waveform, amplitude, frequency and phase.
- Shared duration and sampling rate (continuous) or sample count (discrete).
- Add, subtract, multiply or divide signals from left to right.
- Overlay inputs and result; toggle traces using the legend.
- Interactive time-domain and one-sided amplitude plots with zoom, pan and hover.
- Sampling and harmonic aliasing warnings, input validation and a 100,000-sample limit.
- CSV download containing every input signal and the result on the shared sample grid.

## Run locally

Use Python 3.12 (the locally verified runtime). From the repository root:

```bash
python -m venv .venv-web
# Windows PowerShell:
.venv-web\Scripts\Activate.ps1
# macOS / Linux: source .venv-web/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit, usually http://localhost:8501.

## Signal processing

`signal_processing.py` contains signal generation, the FFT and CSV export.
`app.py` contains only the Streamlit interface and Plotly presentation.

Continuous signals are samples in `[0, duration)` spaced by `1 / fs`.
The one-sided spectrum uses `rfft` and `rfftfreq`, normalized by the sample
count. Only interior positive-frequency bins are doubled: DC and the Nyquist
bin (for even sample counts) retain their original scale. For odd lengths,
the final positive-frequency bin is doubled. Discrete spectra use rad/sample.

The FFT uses a rectangular window without detrending. Non-integer cycles
produce spectral leakage, so a peak bin need not equal the input amplitude.
Sample above twice a sinusoid's frequency; sampling exactly at Nyquist can
lose phase-dependent information. Ideal square and sawtooth waves have
unbounded harmonics, so finite sampling always aliases some harmonics.
Plots over 20,000 points show a reduced display; FFT calculations and CSV
downloads always use the complete data.

## Deploy on Streamlit Community Cloud

1. Push the web app files and `requirements.txt` to your GitHub repository.
2. Sign in at https://share.streamlit.io and choose **Create app**.
3. Select `yagiz-boz/Signal-Visualizer`, the branch containing the web app,
   and `app.py` as the entrypoint.
4. Select a supported Python version matching local development and deploy.
5. Open and verify the generated public URL. Subsequent changes on the
   selected branch update the demo automatically.

No secrets or external services are required by this application.
See the [official deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).

## Legacy applications

`gui.py` (CustomTkinter) and `main.py` (command line) are preserved separately.
Their optional dependencies are `matplotlib` and `customtkinter`; they are
not required by the web app. Their original calculations are not used by it.

## Verification

```bash
python -m unittest discover -s tests
```

## Multiple-signal arithmetic

Operations run in displayed signal order: subtraction with three signals is (S1 - S2) - S3. One signal passes through unchanged. Signals share one time axis. Removing a signal preserves remaining identifiers and settings.

Division skips denominators with absolute value at most 1e-10. Undefined and overflowing results appear as plot gaps and empty CSV cells. FFT and RMS are unavailable if any result sample is undefined; samples are never silently zero-filled. Multiplication and division can create frequencies beyond the input bandwidth, so input Nyquist checks alone cannot guarantee an alias-free result. Result units depend on the operation.

## Custom expressions

Enable **Use custom expression** to combine signals using different operations,
for example `(S1 + S2) * S3`, `0.5 * S1 - S2`, or `S1 / (S2 + 2)`.
Available signal names are listed beside the field and are case-sensitive.
Numbers, parentheses, unary signs, and `+ - * /` are supported. Multiplication
and division take precedence over addition and subtraction; parentheses override
precedence. Constant-only expressions create a constant signal on the shared grid.

Invalid syntax and missing signals display an error instead of an outdated result.
Removing a referenced signal requires editing the expression. The same division
threshold, undefined-sample behavior, FFT rules, and CSV export apply to expressions.
Functions, indexing, attributes, powers, and executable code are not supported.
Expressions are limited to 256 characters and 128 syntax nodes. Disable custom
expression mode to return to the operation picker.
## Additional waveforms

- **DC:** constant at the selected amplitude; no frequency or phase controls.
- **Triangle:** periodic waveform from -amplitude to +amplitude, starting at
  -amplitude when phase is zero. Frequency and phase are adjustable.
- **Unit step:** zero before the start, selected amplitude at and after the start.
- **Pulse:** rectangular pulse of selected amplitude over [start, start + width).
  In continuous mode start/width use seconds; this is not a Dirac delta.
  In discrete mode they use integer sample indices/counts. A width of one sample
  gives a discrete impulse. Negative starts are allowed.

Frequency and phase are shown only for periodic signals. Empty sampled pulses
produce a warning. Continuous steps/pulses are not band-limited; finite sampling
can miss transitions or narrow pulses. Ideal triangle waves also have infinitely
many harmonics. All new waveforms work with arithmetic, expressions, FFT and CSV.
## Input and result FFT comparison

Use **Spectra to compare** to overlay any input signals and the result in one
one-sided amplitude spectrum. All traces use the same sample grid, frequency
bins and FFT normalization. Colors match the time-domain plot; click legend
entries to toggle individual curves. Selecting no traces hides the spectrum.
New signals join the comparison automatically; removing one removes its selection.
If the result contains undefined samples, its FFT is omitted while valid input
spectra remain available. Discrete spectra use rad/sample; continuous spectra
use Hz. Input amplitudes are in V, while result units depend on the operation.
## Save and load setups

Click **Save settings JSON** in the sidebar to download a versioned setup file.
It includes active signal names and parameters, shared sampling settings, operation
or custom expression, input visibility and selected FFT traces. Generated sample
arrays are not stored; they are reconstructed from the settings.

Expand **Save / load settings**, choose a JSON file and click **Load settings**.
Loading replaces the current setup only after the whole file passes validation.
Invalid files leave the current settings unchanged. Files must be version 1,
at most 64 KB, and contain 1–8 signals within the existing sample limits.
Only the current continuous/discrete mode is saved; hidden settings from the other
mode, plot zoom and legend toggles are not included. Keep a saved copy before
replacing a setup if you want to return to it later.