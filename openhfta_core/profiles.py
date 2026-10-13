from pathlib import Path
from typing import Tuple
import numpy as np
from .exceptions import ProfileError
from .models import Profile

M_TO_FT = 3.28084

def parse_height_and_phase(height_str: str, units: str) -> Tuple[float, int]:
    factor = M_TO_FT if units == "meters" else 1.0
    try:
        phase = -1 if height_str.endswith("*") else 1
        value = height_str[:-1] if phase == -1 else height_str
        return float(value) * factor, phase
    except (TypeError, ValueError) as exc:
        raise ProfileError(f"Invalid antenna height: {height_str}") from exc

def parse_profile(profile_path: str) -> tuple[np.ndarray, np.ndarray]:
    path = Path(profile_path)
    try:
        lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    except OSError as exc:
        raise ProfileError(f"Cannot read profile '{profile_path}': {exc}") from exc
    if not lines:
        raise ProfileError("Empty profile file")
    first = lines[0].lower()
    if "meter" in first:
        factor, unit = M_TO_FT, "meters"
        data_lines = lines[1:]
    elif "feet" in first or "foot" in first:
        factor, unit = 1.0, "feet"
        data_lines = lines[1:]
    else:
        # This deliberately preserves the legacy behavior: unlabeled values are feet.
        factor, unit = 1.0, "unspecified (legacy feet)"
        data_lines = lines
    distances, heights = [], []
    for line in data_lines:
        if line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            d, h = float(parts[0]) * factor, float(parts[1]) * factor
        except ValueError:
            continue
        if not np.isfinite(d) or not np.isfinite(h):
            raise ProfileError("Profile contains NaN or infinite values")
        distances.append(d); heights.append(h)
    if len(distances) < 2:
        raise ProfileError("Profile must contain at least 2 points")
    d = np.asarray(distances, dtype=np.float32)
    h = np.asarray(heights, dtype=np.float32)
    if np.any(np.diff(d) <= 0):
        raise ProfileError("Profile distances must be strictly increasing")
    return d, h

def load_profile(profile_path: str) -> Profile:
    distances, heights = parse_profile(profile_path)
    first = Path(profile_path).read_text().splitlines()[0].strip().lower()
    units = "meters" if "meter" in first else "feet" if ("feet" in first or "foot" in first) else "unspecified (legacy feet)"
    return Profile(Path(profile_path), distances, heights, units)
