"""Reusable, web-independent OpenHFTA analysis library."""

from .analysis import analyze
from .aoa import frequency_to_band, parse_aoa_file, parse_prn_multiband
from .exceptions import AnalysisError, LibraryError, ProfileError, ValidationError
from .metrics import compute_fom
from .interpretation import interpret_pattern
from .profiles import parse_height_and_phase, parse_profile

__all__ = ["analyze", "compute_fom", "parse_profile", "parse_height_and_phase",
           "parse_aoa_file", "parse_prn_multiband", "frequency_to_band",
           "AnalysisError", "LibraryError", "ProfileError", "ValidationError"]
