"""Plot selection that preserves spikes and undefined-sample gaps."""
import numpy as np


def plot_indices(values, overview=False, target_points=20000):
    """Full data for exact zoom; optional ordered per-bucket min/max overview.

    Undefined-run boundaries are always retained, even if this exceeds the
    overview target, so disconnected regions never get joined across gaps.
    """
    values = np.asarray(values)
    if values.ndim != 1:
        raise ValueError("Plot data must be one-dimensional.")
    if not overview or values.size <= target_points:
        return np.arange(values.size)
    if target_points < 4:
        raise ValueError("Overview target must be at least four points.")
    finite = np.isfinite(values)
    boundaries = np.flatnonzero(finite[1:] != finite[:-1])
    selected = [0, len(values) - 1, *boundaries, *(boundaries + 1)]
    edges = np.linspace(0, len(values), (target_points - 2) // 2 + 1, dtype=int)
    for start, stop in zip(edges[:-1], edges[1:]):
        valid_indices = np.flatnonzero(finite[start:stop]) + start
        if valid_indices.size:
            segment = values[valid_indices]
            selected.extend((valid_indices[np.argmin(segment)], valid_indices[np.argmax(segment)]))
    return np.unique(selected)
