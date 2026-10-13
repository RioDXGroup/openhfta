import numpy as np


def compute_fom(pattern_db: np.ndarray, aoa_data: dict[int, float]) -> float:
    if not aoa_data: return -np.inf
    linear = 10 ** (np.asarray(pattern_db) / 10.0)
    total = sum(x * aoa_data[angle] for angle, x in enumerate(linear[3::4], start=1) if angle in aoa_data)
    return float(10 * np.log10(total)) if total > 0 else -np.inf


def _validate_pattern(angles_deg: np.ndarray, pattern_db: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    angles = np.asarray(angles_deg, dtype=float)
    pattern = np.asarray(pattern_db, dtype=float)
    if angles.ndim != 1 or pattern.ndim != 1 or len(angles) != len(pattern) or len(pattern) < 3:
        raise ValueError("angles and pattern must be one-dimensional arrays of equal length")
    if not np.all(np.isfinite(angles)) or not np.all(np.isfinite(pattern)):
        raise ValueError("angles and pattern must contain only finite values")
    if np.any(np.diff(angles) <= 0):
        raise ValueError("angles must be strictly increasing")
    return angles, pattern


def _local_extrema(angles: np.ndarray, pattern: np.ndarray, kind: str) -> list[dict[str, float]]:
    sign = 1 if kind == "peaks" else -1
    candidates = np.flatnonzero((sign * pattern[1:-1] >= sign * pattern[:-2]) &
                                (sign * pattern[1:-1] >= sign * pattern[2:])) + 1
    candidates = candidates[np.argsort(pattern[candidates])[::-1] if kind == "peaks" else np.argsort(pattern[candidates])]
    return [{"angle_deg": float(angles[i]), "value_db": float(pattern[i])} for i in candidates]


def _crossing_angle(left_angle: float, left_value: float, right_angle: float,
                    right_value: float, threshold: float) -> float:
    if right_value == left_value:
        return float((left_angle + right_angle) / 2)
    ratio = (threshold - left_value) / (right_value - left_value)
    return float(left_angle + ratio * (right_angle - left_angle))


def beamwidth_3db(angles_deg: np.ndarray, pattern_db: np.ndarray) -> dict[str, float | None]:
    angles, pattern = _validate_pattern(angles_deg, pattern_db)
    peak_index = int(np.argmax(pattern))
    threshold = float(pattern[peak_index] - 3.0)
    left = next((i for i in range(peak_index - 1, -1, -1) if pattern[i] < threshold), None)
    right = next((i for i in range(peak_index + 1, len(pattern)) if pattern[i] < threshold), None)
    left_angle = None if left is None else _crossing_angle(angles[left], pattern[left], angles[left + 1], pattern[left + 1], threshold)
    right_angle = None if right is None else _crossing_angle(angles[right - 1], pattern[right - 1], angles[right], pattern[right], threshold)
    width = None if left_angle is None or right_angle is None else float(right_angle - left_angle)
    return {"threshold_db": threshold, "left_angle_deg": left_angle, "right_angle_deg": right_angle, "width_deg": width}


def integrated_average_gain(angles_deg: np.ndarray, pattern_db: np.ndarray) -> dict[str, float]:
    """Return the trapezoidal area and angular mean of the pattern in dB."""
    angles, pattern = _validate_pattern(angles_deg, pattern_db)
    angular_span = float(angles[-1] - angles[0])
    # NumPy 2.x renamed trapz to trapezoid and removed the old alias.
    integrate = getattr(np, "trapezoid", None) or getattr(np, "trapz")
    area_db_deg = float(integrate(pattern, angles))
    return {
        "area_db_deg": area_db_deg,
        "average_db": float(area_db_deg / angular_span),
        "angle_span_deg": angular_span,
    }


def summarize_pattern(angles_deg: np.ndarray, pattern_db: np.ndarray, max_extrema: int = 5) -> dict:
    angles, pattern = _validate_pattern(angles_deg, pattern_db)
    peak_index = int(np.argmax(pattern))
    # The core forces indices 0 and 1 (0.25 deg and 0.50 deg) to a fixed
    # -30 dB display floor near the horizon (see YTWCore1.f90); it is not a
    # computed pattern value, so it must not be reported or counted as a
    # genuine local minimum ("null") of the antenna pattern.
    floor_skip = 2 if len(pattern) > 2 else 0
    null_angles, null_pattern = angles[floor_skip:], pattern[floor_skip:]
    null_index = floor_skip + int(np.argmin(null_pattern))
    bands = {}
    for name, low, high in (("0-5", 0, 5), ("5-10", 5, 10), ("10-20", 10, 20), ("20-35", 20, 35)):
        values = pattern[(angles >= low) & (angles <= high)]
        if len(values):
            bands[name] = {"samples": int(len(values)), "min_db": float(values.min()), "max_db": float(values.max()), "mean_db": float(values.mean())}
    return {
        "peak": {"angle_deg": float(angles[peak_index]), "value_db": float(pattern[peak_index])},
        "lowest_null": {"angle_deg": float(angles[null_index]), "value_db": float(pattern[null_index])},
        "peaks": _local_extrema(angles, pattern, "peaks")[:max_extrema],
        "nulls": _local_extrema(null_angles, null_pattern, "nulls")[:max_extrema],
        "beamwidth_3db": beamwidth_3db(angles, pattern),
        "integrated_average_gain": integrated_average_gain(angles, pattern),
        "angular_bands": bands,
    }


def compare_patterns(angles_a: np.ndarray, pattern_a: np.ndarray,
                     angles_b: np.ndarray, pattern_b: np.ndarray) -> dict[str, float]:
    first_angles, first = _validate_pattern(angles_a, pattern_a)
    second_angles, second = _validate_pattern(angles_b, pattern_b)
    if not np.allclose(first_angles, second_angles, rtol=0, atol=1e-9):
        raise ValueError("patterns must use the same angle grid")
    delta = second - first
    return {
        "rmse_db": float(np.sqrt(np.mean(delta ** 2))),
        "max_absolute_delta_db": float(np.max(np.abs(delta))),
        "mean_delta_db": float(np.mean(delta)),
        "integrated_average_delta_db": float(
            integrated_average_gain(first_angles, second)["average_db"] -
            integrated_average_gain(first_angles, first)["average_db"]
        ),
        "peak_delta_db": float(np.max(second) - np.max(first)),
    }
