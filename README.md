# Signal Visualizer

An interactive signal-processing demo built with Streamlit, Plotly and NumPy.

**[Open the live demo](https://signal-visualizer-yagiz-boz.streamlit.app/)**

## Quick tour

1. Open **Ready-made experiments**, choose an example and click **Load experiment**.
2. Read the guide, then change any parameter in the sidebar.
3. Use **Add signal** for another input. All inputs share one sample grid.
4. Choose an operation, or enable **Use custom expression**, e.g. `(S1 + S2) * S3`.
5. Compare time traces and FFT spectra. Click legend entries to hide/show traces.
6. Try **Hann** or **Hamming** under **FFT window** to explore spectral leakage.
7. Download samples with **Download signals CSV**, or save the setup with **Save settings JSON**.

On narrow screens, open the sidebar using the arrow in the top-left corner.

## Features

- Continuous and discrete sine, cosine, square, sawtooth, triangle, DC, unit step and rectangular pulse signals.
- Up to eight inputs with independent amplitude, frequency/phase or start/width controls.
- Shared duration and sampling frequency (continuous) or sample count (discrete).
- Pointwise addition, subtraction, multiplication and division; mixed expressions with parentheses and numeric constants.
- Interactive time plots and selectable input/result one-sided amplitude spectra.
- Rectangular, periodic Hann and periodic Hamming FFT windows with coherent-gain amplitude correction.
- Full-detail WebGL rendering or extrema-preserving overview for large records.
- Versioned JSON setup download/upload and complete CSV sample export.
- Input validation, sample limits, aliasing warnings and undefined-division handling.

## Ready-made experiments

| Experiment | Initial setup and expected observation |
| --- | --- |
| Beats | 10 + 11 Hz sines over 3 seconds: 1 Hz beat rate and two spectral peaks. |
| Phase cancellation | Equal 10 Hz sines separated by 180°: approximately zero sum. |
| Amplitude modulation | `(1 + S2) * S1`: 40 Hz carrier of amplitude 1 and sidebands of amplitude 0.25 at 35/45 Hz. |
| Aliasing | A 70 Hz cosine sampled at 100 Hz appears at 30 Hz. |
| Spectral leakage | A 10.5 Hz sine observed for 1 second falls between FFT bins; compare window choices. |

Loading a preset replaces the setup; save a JSON copy first if needed. Guides describe the initial settings, not live measurements after edits.

## Run locally

Use Python **3.12**, the runtime used for validation. From the repository root:

```bash
python -m venv .venv-web
# Windows PowerShell:
.venv-web\Scripts\Activate.ps1
# macOS / Linux: source .venv-web/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the URL printed by Streamlit, normally `http://localhost:8501`.

## Operations and waveforms

The operation picker applies one operation from left to right: `S1 - S2 - S3` means `(S1 - S2) - S3`. A single input passes through unchanged.

Custom expressions support case-sensitive signal names, finite numbers, `+ - * /`, unary signs and parentheses. Multiplication/division take precedence over addition/subtraction. Constant expressions are broadcast across the sample grid. Functions, powers, indexing and executable code are not supported. Invalid expressions show an error; removed signal names must be edited out of the expression.

- **DC:** constant at the selected amplitude.
- **Triangle:** ranges from -amplitude to +amplitude and starts at -amplitude at zero phase.
- **Unit step:** zero before the start; selected amplitude at and after the start.
- **Pulse:** selected amplitude on `[start, start + width)`, zero elsewhere. Continuous start/width use seconds; discrete values use integer sample indices/counts. A one-sample discrete pulse is an impulse. Continuous pulses are rectangular, not Dirac deltas.

Division skips denominators with absolute value at most `1e-10`. Undefined or overflowing results appear as plot gaps and empty CSV cells. Result RMS/FFT are unavailable if any result sample is undefined; input FFTs remain available. Missing samples are never silently replaced by zero.

## FFT interpretation

Continuous samples span `[0, duration)` at spacing `1 / fs`. Discrete spectra use rad/sample; continuous spectra use Hz. The FFT uses `rfft`/`rfftfreq` without mean removal.

Magnitudes are divided by the sum of window coefficients (`N × coherent gain`). Only interior positive-frequency bins are doubled: DC and the even-length Nyquist bin retain their scale; the final positive bin for odd lengths is doubled. This is an **amplitude spectrum**, not a power spectral density.

Hann/Hamming reduce distant leakage but broaden peaks. Gain correction recovers isolated bin-centered tone amplitudes away from DC/Nyquist; off-bin scalloping, overlapping peaks and boundary phase effects can remain. Windowing does not improve frequency resolution or change bin spacing. DC/slow components can spread into neighboring bins with tapered windows. Very short records give limited spectral information.

## Save and load

**Save settings JSON** stores current-mode input identifiers/parameters, sampling settings, operation/expression, input visibility, FFT trace selection, window and plot detail. Samples are regenerated on load. Hidden settings from the other mode, zoom and legend toggles are not stored.

Expand **Save / load settings**, select a JSON file and click **Load settings**. Validation is atomic: an invalid file leaves the setup unchanged. Files must use version 1, contain 1–8 signals and be at most 64 KB. Older files without window/detail selections default to Rectangular/Full detail.

CSV contains the common time/sample axis, every input and the result, including all samples regardless of plot visibility/detail.

## Limits and practical notes

- Maximum **100,000 samples per input**, eight inputs, 256 expression characters and 128 expression syntax nodes.
- Full detail sends every sample/FFT bin to the browser for exact zoom. Eight maximum-size inputs can transfer tens of MB; use **Overview** or fewer visible inputs/spectra on slower devices.
- Overview keeps per-interval minima/maxima independently for each trace. Narrow pulses and peaks are retained, but shapes can be simplified. Gap boundaries are preserved even if the nominal 20,000-point target is exceeded.
- Sampling above twice a sinusoid's frequency avoids the basic aliasing condition; exactly at Nyquist can lose phase information. Ideal square, sawtooth, triangle, step and pulse signals are not band-limited. Transitions or narrow pulses can be missed by sampling.
- Products and quotients can introduce additional frequencies; input Nyquist checks do not guarantee an alias-free result. Result units depend on the operation and can differ from the input unit V.
- The app synthesizes signals; importing recorded signal data and audio is not included in this version.

## Deploy

On [Streamlit Community Cloud](https://share.streamlit.io), select repository **yagiz-boz/Signal-Visualizer**, branch **main**, entrypoint **app.py**, Python **3.12**. Dependencies are pinned in `requirements.txt`. No application secrets or external services are required.

After deployment, pushes to `main` update the app automatically. If changing an existing deployment's repository/branch/entrypoint, follow the [official coordinate-change guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/rename-your-app).

## Verification and source layout

```bash
python -m unittest discover -s tests
```

Tests cover numerical FFT/window normalization, waveforms, arithmetic and expressions, settings validation/restore, plotting, presets and Streamlit flows.

| File | Purpose |
| --- | --- |
| `app.py` | Streamlit interface and Plotly charts |
| `signal_processing.py` | Waveforms, arithmetic, expressions, FFT and CSV |
| `settings.py` | JSON validation and session-state mapping |
| `plotting.py` | Extrema/gap-preserving overview indices |
| `presets.py` | Experiment configurations and guides |
| `tests/` | Numerical and UI tests |

Legacy `gui.py` (CustomTkinter) and `main.py` (command line) remain separate. They use optional Matplotlib/CustomTkinter dependencies and their original calculations; the web application does not import them.
