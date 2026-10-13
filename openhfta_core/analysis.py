import ctypes
import numpy as np
from .exceptions import AnalysisError, ValidationError
from .library import FortranInt16, FortranInt32, FortranReal, load_ytw_core
from .models import AnalysisConfig, AnalysisResult
from .profiles import load_profile

MAX_PROFILE_POINTS = 149
MAX_TRACE_PATHS = 4096
MAX_TRACE_POINTS = 151

def analyze(config: AnalysisConfig) -> AnalysisResult:
    if config.polarization not in ("horizontal", "vertical"):
        raise ValidationError("polarization must be 'horizontal' or 'vertical'")
    if len(config.antenna_heights_ft) > 4 or len(config.antenna_phases) > 4:
        raise ValidationError("The Fortran core supports at most four antenna elements")
    if len(config.antenna_heights_ft) != len(config.antenna_phases):
        raise ValidationError("Antenna heights and phases must have the same length")
    profile = load_profile(config.profile_path)
    distances, heights = profile.distances_ft.copy(), profile.heights_ft.copy()
    if config.move_tower_ft > 0:
        distances = np.concatenate(([0.0], distances + config.move_tower_ft)).astype(np.float32)
        heights = np.concatenate(([heights[0]], heights)).astype(np.float32)
    # Keep one ABI slot available for the far endpoint that the Fortran core
    # may append at index 149/150. The UI and API expose this same effective
    # profile, so the point count cannot diverge between cards and plots.
    if len(distances) > MAX_PROFILE_POINTS:
        distances, heights = distances[:MAX_PROFILE_POINTS], heights[:MAX_PROFILE_POINTS]
    dg0 = np.zeros(151, dtype=np.float32); hg0 = np.zeros(151, dtype=np.float32)
    dg0[1:len(distances)+1] = distances; hg0[1:len(heights)+1] = heights
    hant = np.zeros(4, dtype=np.float32); hant[:len(config.antenna_heights_ft)] = config.antenna_heights_ft
    phases = np.ones(4, dtype=np.int16); phases[:len(config.antenna_phases)] = config.antenna_phases
    pattern = np.zeros(140, dtype=np.float32)
    freq = FortranReal(config.frequency_mhz); epsr = FortranReal(config.soil_epsr); sigma = FortranReal(config.soil_sigma)
    pattern_type = FortranInt16(config.antenna_pattern_type)
    polarization = FortranInt16(1 if config.polarization == "vertical" else 0)
    diffraction = FortranInt16(int(config.diffraction_disable))
    debug = FortranInt16(int(config.debug_enable)); debug_angle = FortranReal(config.debug_angle)
    try:
        lib = load_ytw_core(config.lib_path)
        lib.ytwcore1_(dg0.ctypes.data_as(ctypes.POINTER(FortranReal)), hg0.ctypes.data_as(ctypes.POINTER(FortranReal)), hant.ctypes.data_as(ctypes.POINTER(FortranReal)), ctypes.byref(freq), ctypes.byref(epsr), ctypes.byref(sigma), ctypes.byref(pattern_type), ctypes.byref(polarization), ctypes.byref(diffraction), ctypes.byref(debug), ctypes.byref(debug_angle), pattern.ctypes.data_as(ctypes.POINTER(FortranReal)), phases.ctypes.data_as(ctypes.POINTER(FortranInt16)))
    except Exception as exc:
        if isinstance(exc, AnalysisError): raise
        raise AnalysisError(str(exc)) from exc
    trace_paths: list[dict[str, object]] = []
    trace_func = getattr(lib, "ytwcore1_gettrace_", None)
    if trace_func is not None:
        trace_count = FortranInt32(0)
        trace_kind = np.zeros(MAX_TRACE_PATHS, dtype=np.int16)
        trace_points = np.zeros(MAX_TRACE_PATHS, dtype=np.int16)
        trace_angles = np.zeros(MAX_TRACE_PATHS, dtype=np.float32)
        trace_x = np.zeros((MAX_TRACE_PATHS, MAX_TRACE_POINTS), dtype=np.float32, order="F")
        trace_y = np.zeros((MAX_TRACE_PATHS, MAX_TRACE_POINTS), dtype=np.float32, order="F")
        trace_func(
            ctypes.byref(trace_count),
            trace_kind.ctypes.data_as(ctypes.POINTER(FortranInt16)),
            trace_points.ctypes.data_as(ctypes.POINTER(FortranInt16)),
            trace_angles.ctypes.data_as(ctypes.POINTER(FortranReal)),
            trace_x.ctypes.data_as(ctypes.POINTER(FortranReal)),
            trace_y.ctypes.data_as(ctypes.POINTER(FortranReal)),
        )
        kind_names = {
            1: "direct",
            2: "reflected",
            4: "diffracted",
            6: "reflected_diffracted",
            8: "double_diffracted",
            10: "reflected_double_diffracted",
            12: "reflected_double_diffracted",
        }
        for index in range(min(int(trace_count.value), MAX_TRACE_PATHS)):
            point_count = min(int(trace_points[index]), MAX_TRACE_POINTS)
            if point_count < 2:
                continue
            trace_paths.append({
                "kind": kind_names.get(int(trace_kind[index]), "other"),
                "angle_deg": float(trace_angles[index]),
                "distances_ft": trace_x[index, :point_count].astype(float).tolist(),
                "heights_ft": trace_y[index, :point_count].astype(float).tolist(),
            })
    angles = np.arange(0.25, 35.25, 0.25, dtype=np.float64)
    effective = AnalysisConfig(**{**config.__dict__, "antenna_heights_ft": tuple(float(x) for x in hant), "antenna_phases": tuple(int(x) for x in phases)})
    return AnalysisResult(
        angles, pattern, profile, effective,
        metadata={
            "profile_points": len(distances),
            "max_profile_points": MAX_PROFILE_POINTS,
            "angle_start_deg": 0.25,
            "angle_end_deg": 35.0,
            "angle_step_deg": 0.25,
            "trace_paths": len(trace_paths),
        },
        trace_paths=trace_paths,
    )
