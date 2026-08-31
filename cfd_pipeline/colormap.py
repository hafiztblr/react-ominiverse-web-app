from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


# High-contrast scientific blue -> white -> red palette. It remains legible in
# RTX streaming and matches conventional CFD temperature previews.
_STOPS = np.array(
    [
        [0.02, 0.05, 0.45],
        [0.12, 0.32, 0.78],
        [0.55, 0.72, 0.92],
        [0.94, 0.94, 0.88],
        [0.90, 0.38, 0.18],
        [0.58, 0.01, 0.03],
    ],
    dtype=np.float32,
)


def blue_to_red(
    values: NDArray[np.floating],
    minimum: float | None = None,
    maximum: float | None = None,
) -> NDArray[np.float32]:
    values = np.asarray(values, dtype=np.float64).reshape(-1)
    low = float(np.min(values)) if minimum is None else float(minimum)
    high = float(np.max(values)) if maximum is None else float(maximum)
    normalized = np.zeros_like(values) if high == low else np.clip((values - low) / (high - low), 0.0, 1.0)
    scaled = normalized * (_STOPS.shape[0] - 1)
    left = np.minimum(scaled.astype(np.int64), _STOPS.shape[0] - 2)
    fraction = (scaled - left)[:, None]
    return ((_STOPS[left] * (1.0 - fraction)) + (_STOPS[left + 1] * fraction)).astype(np.float32)
