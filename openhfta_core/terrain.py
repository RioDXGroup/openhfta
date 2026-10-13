"""Deterministic summaries of the input terrain profile.

These are geometric diagnostics for interpretation. They do not replace the
Fortran propagation calculation or claim a full Fresnel-zone clearance.
"""
import numpy as np


def summarize_terrain(distances_ft: np.ndarray, heights_ft: np.ndarray,
                      antenna_height_ft: float = 0.0) -> dict:
    distances = np.asarray(distances_ft, dtype=float)
    heights = np.asarray(heights_ft, dtype=float)
    if distances.ndim != 1 or heights.ndim != 1 or len(distances) != len(heights) or len(distances) < 2:
        raise ValueError("terrain distances and heights must be one-dimensional arrays of equal length")
    if not np.all(np.isfinite(distances)) or not np.all(np.isfinite(heights)):
        raise ValueError("terrain values must be finite")
    span = float(distances[-1] - distances[0])
    elevation_change = np.diff(heights)
    segment_distance = np.diff(distances)
    slopes = elevation_change / segment_distance
    endpoint_line = np.linspace(heights[0] + antenna_height_ft, heights[-1], len(heights))
    clearance = endpoint_line - heights
    obstruction_index = int(np.argmin(clearance))
    return {
        "points": int(len(distances)),
        "distance_start_ft": float(distances[0]),
        "distance_end_ft": float(distances[-1]),
        "distance_span_ft": span,
        "distance_span_m": span / 3.28084,
        "elevation_min_ft": float(heights.min()),
        "elevation_max_ft": float(heights.max()),
        "elevation_min_m": float(heights.min() / 3.28084),
        "elevation_max_m": float(heights.max() / 3.28084),
        "relief_ft": float(heights.max() - heights.min()),
        "relief_m": float((heights.max() - heights.min()) / 3.28084),
        "mean_slope_percent": float(np.mean(slopes) * 100),
        "max_uphill_slope_percent": float(np.max(slopes) * 100),
        "max_downhill_slope_percent": float(np.min(slopes) * 100),
        "highest_point": {
            "distance_ft": float(distances[int(np.argmax(heights))]),
            "distance_m": float(distances[int(np.argmax(heights))] / 3.28084),
            "elevation_ft": float(heights.max()),
            "elevation_m": float(heights.max() / 3.28084),
        },
        "lowest_point": {
            "distance_ft": float(distances[int(np.argmin(heights))]),
            "distance_m": float(distances[int(np.argmin(heights))] / 3.28084),
            "elevation_ft": float(heights.min()),
            "elevation_m": float(heights.min() / 3.28084),
        },
        "approximate_los": {
            "antenna_height_ft": float(antenna_height_ft),
            "minimum_clearance_ft": float(clearance[obstruction_index]),
            "minimum_clearance_m": float(clearance[obstruction_index] / 3.28084),
            "obstruction_distance_ft": float(distances[obstruction_index]),
            "blocked_by_terrain": bool(np.any(clearance[1:-1] < 0)),
            "method": "reta entre a antena no primeiro ponto e o último ponto; não inclui zona de Fresnel",
        },
    }
