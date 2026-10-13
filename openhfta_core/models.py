from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import numpy as np

@dataclass(frozen=True)
class Profile:
    path: Optional[Path]
    distances_ft: np.ndarray
    heights_ft: np.ndarray
    source_units: str

@dataclass(frozen=True)
class AnalysisConfig:
    profile_path: str
    frequency_mhz: float
    antenna_heights_ft: tuple[float, ...] = (10.0,)
    antenna_phases: tuple[int, ...] = (1,)
    soil_epsr: float = 13.0
    soil_sigma: float = 0.005
    diffraction_disable: bool = False
    debug_enable: bool = False
    debug_angle: float = 0.0
    lib_path: Optional[str] = None
    move_tower_ft: float = 0.0
    antenna_pattern_type: int = 1
    polarization: str = "horizontal"

@dataclass
class AnalysisResult:
    angles_deg: np.ndarray
    pattern_db: np.ndarray
    profile: Profile
    config: AnalysisConfig
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    trace_paths: list[dict[str, Any]] = field(default_factory=list)
