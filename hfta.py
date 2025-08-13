#!/usr/bin/env python3
"""
OpenHFTA - HF Terrain Analysis using OpenYTWCore

This tool computes elevation pattern for HF antennas over terrain profiles
using Uniform Theory of Diffraction (UTD) and Fresnel reflection modeling.

The core analysis is performed by the YTWCore1 Fortran subroutine, accessed
via ctypes with proper ABI handling for pass-by-reference parameters.
"""

import ctypes
import ctypes.util
import numpy as np
import os
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import matplotlib.pyplot as plt

# Fortran INTEGER*2 is 16-bit, INTEGER*4 is 32-bit  
class FortranInt16(ctypes.c_int16):
    pass

class FortranInt32(ctypes.c_int32):
    pass

class FortranReal(ctypes.c_float):
    pass

def find_ytw_core_library() -> Optional[str]:
    """Find the OpenYTWCore library."""
    env_path = os.environ.get("OPENHFTA_LIB")
    if env_path:
        path = Path(env_path).expanduser()
        return str(path if path.is_absolute() else Path.cwd() / path)

    script_dir = Path(__file__).resolve().parent
    lib_names = ("libopenytwcore.so", "OpenYTWCore.dll", "libOpenYTWCore.dylib")
    for lib_dir in (script_dir, script_dir.parent / "lib"):
        for lib_name in lib_names:
            candidate = lib_dir / lib_name
            if candidate.exists():
                return str(candidate)

    return ctypes.util.find_library("openytwcore")


def load_ytw_core(lib_path: Optional[str] = None) -> ctypes.CDLL:
    """Load the OpenYTWCore shared library and set up function prototypes."""
    if lib_path is None:
        lib_path = find_ytw_core_library()
        if lib_path is None:
            raise FileNotFoundError("Cannot find OpenYTWCore library. Use --lib or OPENHFTA_LIB to specify path.")
    
    try:
        lib = ctypes.CDLL(lib_path)
    except OSError as e:
        raise RuntimeError(f"Failed to load {lib_path}: {e}")
    
    # Set up YTWCore1 function prototype
    # Based on Fortran signature:
    # subroutine YTWCore1 (DG0_in, HG0_in, HantFeetIn, FREQ_MHZ_in, SOIL_EPSR_in, 
    #                      SOIL_COND_PARAM_in, AntPatternType, DiffractionDisable, 
    #                      DebugEnable_in, DebugExitAngle_in, Pattern_dB, AntPhase)
    #
    # All scalars passed by reference, arrays as pointers to contiguous memory
    try:
        ytw_func = lib.ytwcore1_
    except AttributeError:
        raise RuntimeError("Symbol ytwcore1_ not found in library. Check library version.")
    
    ytw_func.argtypes = [
        ctypes.POINTER(FortranReal),    # DG0_in(0:150) - distances (feet)
        ctypes.POINTER(FortranReal),    # HG0_in(0:150) - heights (feet)  
        ctypes.POINTER(FortranReal),    # HantFeetIn(0:3) - antenna heights (feet, but converted)
        ctypes.POINTER(FortranReal),    # FREQ_MHZ_in - frequency (MHz)
        ctypes.POINTER(FortranReal),    # SOIL_EPSR_in - soil relative permittivity
        ctypes.POINTER(FortranReal),    # SOIL_COND_PARAM_in - soil conductivity parameter
        ctypes.POINTER(FortranInt16),   # AntPatternType - antenna pattern type
        ctypes.POINTER(FortranInt16),   # DiffractionDisable - 1=disable diffraction, 0=enable 
        ctypes.POINTER(FortranInt16),   # DebugEnable_in - debug output enable
        ctypes.POINTER(FortranReal),    # DebugExitAngle_in - debug exit angle (degrees)
        ctypes.POINTER(FortranReal),    # Pattern_dB(0:139) - output elevation pattern (dB)
        ctypes.POINTER(FortranInt16),   # AntPhase(0:3) - antenna element phases
    ]
    ytw_func.restype = None
    
    return lib

def parse_height_and_phase(height_str: str, units: str) -> Tuple[float, int]:
    """
    Parse height string that may include phase notation.
    
    Args:
        height_str: Height string, e.g., "10" or "10*" (asterisk means out-of-phase)
        
    Returns:
        Tuple of (height, phase) where phase is 1 for in-phase, -1 for out-of-phase
    """
    if units == "meters":
        unit_factor = 3.28084  # meters to feet
    else:
        unit_factor = 1.0  # feet to feet
    if height_str.endswith('*'):
        return float(height_str[:-1]) * unit_factor, -1
    else:
        return float(height_str) * unit_factor, 1

def parse_profile(profile_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Parse terrain profile file in legacy HFTA .PRO format.
    
    Returns:
        distances (np.ndarray): Distance points in feet (converted for Fortran core)
        heights (np.ndarray): Height points in feet (converted for Fortran core) 
    """
    with open(profile_path, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    if not lines:
        raise ValueError("Empty profile file")
    
    # First line should contain units
    first_line = lines[0].lower()
    if 'meter' in first_line:
        unit_factor = 3.28084  # meters to feet
        skip_first_line = True
    elif 'feet' in first_line or 'foot' in first_line:
        unit_factor = 1.0  # already in feet
        skip_first_line = True
    else:
        # Default to feet if no units specified
        unit_factor = 1.0  # meters to feet
        skip_first_line = False
    
    distances = []
    heights = []
    
    for line in lines[1:] if skip_first_line else lines:
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) >= 2:
            try:
                dist = float(parts[0]) * unit_factor  # Convert to feet
                height = float(parts[1]) * unit_factor  # Convert to feet
                distances.append(dist)
                heights.append(height) 
            except ValueError:
                continue
    
    if len(distances) < 2:
        raise ValueError("Profile must contain at least 2 points")
    
    return np.array(distances, dtype=np.float32), np.array(heights, dtype=np.float32)

def parse_aoa_file(aoa_path: str, frequency_mhz: float) -> Dict[int, float]:
    """
    Parse Angle of Arrival (AoA) file in ARRL .PRN format.
    
    Args:
        aoa_path: Path to AoA file
        frequency_mhz: Operating frequency in MHz (used to auto-detect band for .PRN files)
        
    Returns:
        Dict mapping elevation angles (degrees) to probabilities (0-1)
    """
    with open(aoa_path, 'r') as f:
        content = f.read()
    # ARRL .PRN multi-band format - auto-detect band from frequency
    band = frequency_to_band(frequency_mhz)
    return parse_prn_multiband(content, band)

def parse_prn_multiband(content: str, band: Optional[str] = None) -> Dict[int, float]:
    """
    Parse ARRL .PRN multi-band format.
    
    Format:
    - Line 1: Description/title (ignored)
    - Line 2: Column headers starting with "Elev" followed by band names (e.g., "80m", "40m", etc.)
    - Lines 3+: Elevation angle (integer) followed by probability percentages for each band
    
    Args:
        content: Raw file content
        band: Target band (e.g., "20m"). If None, uses first available band.
        
    Returns:
        Dict mapping elevation angles (degrees) to probabilities (0-1)
    """
    lines = content.strip().split('\n')
    if len(lines) < 3:
        return {}
    
    # Skip title line, parse header
    header_line = lines[1].strip()
    if not header_line.startswith('Elev'):
        return {}
    
    # Extract band names from header
    header_parts = header_line.split()
    if len(header_parts) < 2:
        return {}
    
    band_names = header_parts[1:]  # Skip "Elev" column
    
    # Find target band column index
    band_index = None
    if band is not None:
        for i, band_name in enumerate(band_names):
            if band_name == band:
                band_index = i
                break
    
    if band_index is None:
        print(f"Warning: Band '{band}' not found in PRN file")
        return {}

    # Parse data rows
    aoa_data = {}
    for line in lines[2:]:
        line = line.strip()
        if not line:
            continue
            
        parts = line.split()
        if len(parts) < 2:
            continue
            
        try:
            elevation = int(parts[0])
            if band_index + 1 < len(parts):
                percentage = float(parts[band_index + 1])
                # Convert percentage to probability and validate range
                probability = percentage / 100.0
                if 0 <= probability <= 1 and 0 <= elevation <= 90:
                    aoa_data[elevation] = probability
        except (ValueError, IndexError):
            continue
    
    return aoa_data

def parse_frequency(freq_str: str) -> float:
    """
    Parse frequency specification - either MHz value or ham band notation.
    
    Args:
        freq_str: Frequency as string - either "14.2" (MHz) or "20m" (band)
        
    Returns:
        Frequency in MHz
    """
    # Ham band to frequency mapping (approximate center frequencies for HF)
    ham_bands = {
        '160m': 1.85,   # 1.8-2.0 MHz
        '80m': 3.75,    # 3.5-4.0 MHz  
        '60m': 5.35,    # 5.3-5.4 MHz
        '40m': 7.15,    # 7.0-7.3 MHz
        '30m': 10.12,   # 10.1-10.15 MHz
        '20m': 14.2,    # 14.0-14.35 MHz
        '17m': 18.1,    # 18.068-18.168 MHz
        '15m': 21.2,    # 21.0-21.45 MHz
        '12m': 24.9,    # 24.89-24.99 MHz
        '10m': 28.5,    # 28.0-29.7 MHz
        '6m': 50.1,     # 50.0-54.0 MHz
    }
    
    freq_str = freq_str.strip().lower()
    
    # Check if it's a ham band notation
    if freq_str in ham_bands:
        return ham_bands[freq_str]
    
    # Try to parse as numeric MHz value
    try:
        return float(freq_str)
    except ValueError:
        raise ValueError(f"Invalid frequency specification: {freq_str}. Use MHz value or ham band like '20m'.")

def frequency_to_band(freq_mhz: float) -> Optional[str]:
    """Convert frequency in MHz to ham band string for AoA band detection."""
    # Ham band frequency ranges
    if 1.8 <= freq_mhz <= 2.0:
        return "160m"
    elif 3.5 <= freq_mhz <= 4.0:
        return "80m"
    elif 5.3 <= freq_mhz <= 5.4:
        return "60m"
    elif 7.0 <= freq_mhz <= 7.3:
        return "40m"
    elif 10.1 <= freq_mhz <= 10.15:
        return "30m"
    elif 14.0 <= freq_mhz <= 14.35:
        return "20m"
    elif 18.068 <= freq_mhz <= 18.168:
        return "17m"
    elif 21.0 <= freq_mhz <= 21.45:
        return "15m"
    elif 24.89 <= freq_mhz <= 24.99:
        return "12m"
    elif 28.0 <= freq_mhz <= 29.7:
        return "10m"
    elif 50.0 <= freq_mhz <= 54.0:
        return "6m"
    else:
        return None

def compute_fom(pattern_db: np.ndarray, aoa_data: Dict[int, float]) -> float:
    """
    Computes the Figure of Merit (FOM) based on the reverse-engineered and validated formula.
    
    The formula is the dB value of the weighted sum of linear power values.
    S = sum( (10**(pattern_db[i]/10)) * aoa_probability[i] )
    FOM = 10 * log10(S)
    """
    if not aoa_data:
        return -np.inf
    
    # Convert pattern from dB to linear scale
    pattern_linear = 10 ** (np.array(pattern_db) / 10.0)
    
    # Initialize the sum 'S' at 0.0 and calculate the weighted sum.
    weighted_sum_s = 0.0
    
    for angle, x in enumerate(pattern_linear[3::4], start=1):  # pattern_linear[0] is at 0.25°; start at 1° and step by 1°
        if angle in aoa_data:
            weighted_sum_s += x * aoa_data[angle]

    # Handle cases where the sum is zero or negative to avoid math errors.
    if weighted_sum_s <= 0:
        return -np.inf

    # 3. Apply the final 10 * log10() transformation.
    fom_db = 10 * np.log10(weighted_sum_s)
    
    return fom_db

def analyze(profile_path: str, 
           frequency_mhz: float,
           antenna_heights: List[float] = [10.0],
           antenna_phases: List[int] = [1],
           soil_epsr: float = 13.0,
           soil_sigma: float = 0.005,
           diffraction_disable: bool = False,
           debug_enable: bool = False,
           debug_angle: float = 0.0,
           lib_path: Optional[str] = None,
           move_tower: float = 0.0,
           antenna_pattern_type: int = 1) -> Tuple[np.ndarray, np.ndarray]:
    """
    Analyze antenna pattern over terrain using OpenYTWCore.
    
    Args:
        profile_path: Path to terrain profile file
        frequency_mhz: Operating frequency in MHz
        antenna_heights: List of antenna element heights
        antenna_phases: List of phase settings (1=0°, -1=180°)
        soil_epsr: Soil relative permittivity
        soil_sigma: Soil conductivity in S/m
        diffraction_disable: If True, disable diffraction analysis
        debug_enable: Enable debug output
        debug_angle: Debug exit angle in degrees
        lib_path: Path to libopenytwcore.so
        move_tower: Distance to move tower back
        antenna_pattern_type: Antenna pattern type (1=Dipole, 2=2-Ele, etc.)
        
    Returns:
        Tuple of (elevation_angles, pattern_db)
    """
    # Load library
    lib = load_ytw_core(lib_path)
    
    # Parse terrain profile  
    distances, heights = parse_profile(profile_path)
    
    # Apply move tower transformation if requested
    if move_tower > 0:
        # Move tower back by specified distance on flat ground
        tower_height = heights[0]  # Original tower base height
        
        # Shift all distances forward by move_tower amount
        distances = distances + move_tower
        
        # Insert new point at distance 0 with same height as original tower base
        distances = np.concatenate([[0.0], distances])
        heights = np.concatenate([[tower_height], heights])
    
    # Prepare arrays for Fortran (0-indexed arrays become 0:150)
    dg0 = np.zeros(151, dtype=np.float32)  # 0:150
    hg0 = np.zeros(151, dtype=np.float32)  # 0:150
    
    # Copy profile data (ensuring we don't exceed array bounds and keep a zero ending marker)
    n_points = min(len(distances), 148)
    dg0[1:n_points+1] = distances[:n_points]
    hg0[1:n_points+1] = heights[:n_points]
    
    # Copy antenna heights
    hant_feet = np.zeros(4, dtype=np.float32)  # 0:3
    for i in range(min(len(antenna_heights), 4)):
        hant_feet[i] = antenna_heights[i]
    
    # Prepare other parameters
    freq_mhz = FortranReal(frequency_mhz)
    soil_epsr_val = FortranReal(soil_epsr)
    soil_cond = FortranReal(soil_sigma)
    ant_pattern_type = FortranInt16(antenna_pattern_type)
    diffraction_disable_val = FortranInt16(1 if diffraction_disable else 0)
    debug_enable_val = FortranInt16(1 if debug_enable else 0)
    debug_exit_angle = FortranReal(debug_angle)
    
    # Prepare antenna phases
    ant_phases = np.ones(4, dtype=np.int16)  # 0:3, default to 0°
    for i in range(min(len(antenna_phases), 4)):
        ant_phases[i] = antenna_phases[i]
    
    # Output array for elevation pattern
    pattern_db = np.zeros(140, dtype=np.float32)  # 0:139
    
    # Call YTWCore1
    lib.ytwcore1_(
        dg0.ctypes.data_as(ctypes.POINTER(FortranReal)),
        hg0.ctypes.data_as(ctypes.POINTER(FortranReal)),
        hant_feet.ctypes.data_as(ctypes.POINTER(FortranReal)),
        ctypes.byref(freq_mhz),
        ctypes.byref(soil_epsr_val),
        ctypes.byref(soil_cond),
        ctypes.byref(ant_pattern_type),
        ctypes.byref(diffraction_disable_val),
        ctypes.byref(debug_enable_val),
        ctypes.byref(debug_exit_angle),
        pattern_db.ctypes.data_as(ctypes.POINTER(FortranReal)),
        ant_phases.ctypes.data_as(ctypes.POINTER(FortranInt16))
    )
    
    # Generate elevation angle array (0.25° steps from 0.25° to 35.0°, 140 samples)
    angles = np.arange(0.25, 35.25, 0.25)
    
    return angles, pattern_db

def plot_multiple_terrain_profiles(profile_configs: List[Dict[str, Any]], global_args: Dict[str, Any], output_path: Optional[str] = None):
    """Plot multiple terrain profiles with antenna positions marked."""
    plt.figure(figsize=(12, 8))
    colors = plt.cm.tab10(np.linspace(0, 1, len(profile_configs)))
    units = global_args['units'].lower()
    if units == "meters":
        unit_factor = 1/3.28084  # feet to meters
    else:
        unit_factor = 1.0  # feet to feet
    
    for i, config in enumerate(profile_configs):
        distances, heights = parse_profile(config['profile'])
        
        # Apply move tower transformation if requested
        if config['move_tower'] > 0:
            tower_height = heights[0]
            distances = distances + config['move_tower']
            distances = np.concatenate([[0.0], distances])
            heights = np.concatenate([[tower_height], heights])
        
        # Plot terrain profile
        label = f"{Path(config['profile']).name} ({config['antenna_type']})"
        plt.plot(distances * unit_factor, heights * unit_factor, '-', linewidth=2, color=colors[i], label=label)
        
        # Mark antenna positions
        tower_base_height = heights[0]
        for j, height in enumerate(config['processed_heights']):
            total_height = tower_base_height + height
            marker_label = f'Ant {j+1}' if j == 0 else None
            plt.plot(0, total_height * unit_factor, 'o', markersize=6, color=colors[i], 
                    label=marker_label, alpha=0.8)
    
    plt.xlabel(f"Distance ({units})")
    plt.ylabel(f"Height ({units})")
    plt.title('Terrain Profile')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Multi-terrain plot saved to {output_path}")
    else:
        plt.show()

def plot_multiple_patterns(results: List[Dict[str, Any]], frequency_mhz: float, 
                          diffraction_enabled: bool, aoa_data: Optional[Dict[int, float]], 
                          global_args: Dict[str, Any], output_path: Optional[str] = None):
    """Plot multiple elevation patterns for comparison."""
    plt.figure(figsize=(12, 8))
    colors = plt.cm.tab10(np.linspace(0, 1, len(results)))
    units = global_args['units'].lower()
    if units == "meters":
        unit_factor = 1/3.28084  # feet to meters
        unit_symbol = "m"
    else:
        unit_factor = 1.0  # feet to feet
        unit_symbol = "ft"
    
    max_gain_overall = -999
    best_fom = None
    
    for i, result in enumerate(results):
        config = result['config']
        angles = result['angles']
        pattern_db = result['pattern_db']
        fom = result['fom']
        
        # Create label with key info
        label_parts = [Path(config['profile']).name, config['antenna_type']]
        if len(config['processed_heights']) > 1:
            heights_str = ','.join([f"{h*unit_factor:.0f}" + ("*" if p == -1 else "") 
                                  for h, p in zip(config['processed_heights'], config['processed_phases'])])
            label_parts.append(f"[{heights_str}]")
        else:
            height = config['processed_heights'][0]
            phase = config['processed_phases'][0]
            label_parts.append(f"{height*unit_factor:.0f}{unit_symbol}" + ("*" if phase == -1 else ""))
        
        if fom is not None:
            label_parts.append(f"FOM:{fom:.1f}")
            if best_fom is None or fom > best_fom:
                best_fom = fom
        
        label = ' • '.join(label_parts)
        
        plt.plot(angles, pattern_db, '-', linewidth=2, color=colors[i], label=label)
        
        # Track overall maximum
        max_gain = np.max(pattern_db)
        if max_gain > max_gain_overall:
            max_gain_overall = max_gain
    
    plt.xlabel('Elevation angle (degrees)')
    plt.ylabel('Gain (dBi)')
    plt.grid(True, alpha=0.3)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Build title
    title_parts = [f'{frequency_mhz:.1f} MHz']
    title_parts.append(f'Diffraction: {"On" if diffraction_enabled else "Off"}')
    if best_fom is not None:
        title_parts.append(f'Best FOM: {best_fom:.1f}')
    
    plt.title(' • '.join(title_parts))
    plt.xlim(0, 35)

    min_pattern_db = min(min(result['pattern_db'][2:]) for result in results)  # exclude first two points (always -30 dB)
    _, ymax = plt.ylim()
    plt.ylim(min_pattern_db - 0.1*abs(min_pattern_db), ymax)

    # Add AoA probability overlay if available
    if aoa_data:
        aoa_angles = np.array(list(aoa_data.keys()))
        aoa_percent = 100.*np.array(list(aoa_data.values()))
        ax2 = plt.twinx()
        ax2.bar(aoa_angles, aoa_percent, color='purple', width=0.25, alpha=0.7)
        if max(aoa_percent) < 20:
            ax2.set_ylim(0, 20)
        ax2.set_ylabel('AoA probability (%)')

    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Multi-pattern plot saved to {output_path}")
    else:
        plt.show()

def parse_profile_blocks(args: List[str]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parse command line arguments into profile blocks with their configurations.
    
    Each --profile starts a new configuration block that inherits defaults
    and can be overridden by subsequent arguments until the next --profile.
    
    Returns:
        Tuple of (profile_configs, global_args) where profile_configs is a list
        of dictionaries with profile-specific settings, and global_args contains
        arguments that apply to all profiles.
    """
    # Default configuration for profiles
    default_config = {
        'heights': ['10.0'],
        'antenna_type': 'Dipole',
        'move_tower': 0.0
    }
    
    # Global arguments (not profile-specific)
    global_args = {
        'freq': None,
        'soil_sigma': 0.005,
        'soil_epsr': 13.0,
        'units': 'meters',
        'no_diffraction': False,
        'plot_mode': 'elevation',
        'lib': None,
        'aoa': None,
        'output': None,
        'debug': False,
        'debug_angle': 0.0
    }
    
    profile_configs = []
    current_config = None
    i = 0
    
    while i < len(args):
        arg = args[i]
        
        if arg == '--profile':
            # Start new profile configuration
            if i + 1 >= len(args):
                raise ValueError("--profile requires a filename argument")
            
            # Save previous profile if it exists
            if current_config is not None:
                profile_configs.append(current_config.copy())
            
            # Start new profile with defaults
            current_config = default_config.copy()
            current_config['profile'] = args[i + 1]
            i += 2
            
        elif arg == '--freq':
            if i + 1 >= len(args):
                raise ValueError("--freq requires a value")
            global_args['freq'] = args[i + 1]
            i += 2
            
        elif arg in ['--heights']:
            if current_config is None:
                raise ValueError(f"{arg} must come after --profile")
            if i + 1 >= len(args):
                raise ValueError(f"{arg} requires at least one value")
            # Collect all height values until next option
            heights = []
            i += 1
            while i < len(args) and not args[i].startswith('--'):
                heights.append(args[i])
                i += 1
            current_config['heights'] = heights
            
        elif arg == '--antenna-type':
            if current_config is None:
                raise ValueError("--antenna-type must come after --profile")
            if i + 1 >= len(args):
                raise ValueError("--antenna-type requires a value")
            antenna_type = args[i + 1]
            if antenna_type not in ['Dipole', '2-Ele', '3-Ele', '4-Ele', '5-Ele', '6-Ele', '8-Ele']:
                raise ValueError(f"Invalid antenna type: {antenna_type}")
            current_config['antenna_type'] = antenna_type
            i += 2
            
        elif arg == '--move-tower':
            if current_config is None:
                raise ValueError("--move-tower must come after --profile")
            if i + 1 >= len(args):
                raise ValueError("--move-tower requires a value")
            current_config['move_tower'] = float(args[i + 1])
            i += 2
            
        # Global arguments
        elif arg == '--units':
            if i + 1 >= len(args):
                raise ValueError("--units requires a value")
            units = args[i + 1]
            if units not in ['meters', 'feet']:
                raise ValueError(f"Invalid units: {units}")
            global_args['units'] = units
            i += 2
            
        elif arg == '--soil-sigma':
            if i + 1 >= len(args):
                raise ValueError("--soil-sigma requires a value")
            global_args['soil_sigma'] = float(args[i + 1])
            i += 2
            
        elif arg == '--soil-epsr':
            if i + 1 >= len(args):
                raise ValueError("--soil-epsr requires a value")
            global_args['soil_epsr'] = float(args[i + 1])
            i += 2
            
        elif arg == '--no-diffraction':
            global_args['no_diffraction'] = True
            i += 1
            
        elif arg == '--plot-mode':
            if i + 1 >= len(args):
                raise ValueError("--plot-mode requires a value")
            plot_mode = args[i + 1]
            if plot_mode not in ['elevation', 'terrain']:
                raise ValueError(f"Invalid plot mode: {plot_mode}")
            global_args['plot_mode'] = plot_mode
            i += 2
            
        elif arg == '--lib':
            if i + 1 >= len(args):
                raise ValueError("--lib requires a value")
            global_args['lib'] = args[i + 1]
            i += 2
            
        elif arg == '--aoa':
            if i + 1 >= len(args):
                raise ValueError("--aoa requires a value")
            global_args['aoa'] = args[i + 1]
            i += 2
            
        elif arg == '--output':
            if i + 1 >= len(args):
                raise ValueError("--output requires a value")
            global_args['output'] = args[i + 1]
            i += 2
            
        elif arg == '--debug':
            global_args['debug'] = True
            i += 1
            
        elif arg == '--debug-angle':
            if i + 1 >= len(args):
                raise ValueError("--debug-angle requires a value")
            global_args['debug_angle'] = float(args[i + 1])
            i += 2
            
        elif arg in ['-h', '--help']:
            print_help()
            sys.exit(0)
            
        else:
            raise ValueError(f"Unknown argument: {arg}")
    
    # Add the last profile if it exists
    if current_config is not None:
        profile_configs.append(current_config)
    
    # Validate required arguments
    if not profile_configs:
        raise ValueError("At least one --profile must be specified")
    if global_args['plot_mode'] == 'elevation' and global_args['freq'] is None:
        raise ValueError("--freq is required")
    
    return profile_configs, global_args

def print_help():
    """Print help message for the custom parser."""
    help_text = """
OpenHFTA - HF Terrain Analysis using OpenYTWCore

Usage: hfta --profile terrain.pro [profile-options] --freq frequency [global-options]
       hfta --profile terrain1.pro [options] --profile terrain2.pro [options] --freq frequency

Profile Options (apply to the preceding --profile):
  --profile FILE               Terrain profile file (.PRO format)
  --heights H1 [H2 ...]        Antenna heights with optional phase (*=out-of-phase, e.g., 10*)
  --antenna-type TYPE          Antenna type: Dipole, 2-Ele, 3-Ele, 4-Ele, 5-Ele, 6-Ele, 8-Ele
  --move-tower DISTANCE        Move tower back by distance (in units specified by --units)

Required Global Options:
  --freq FREQUENCY             Operating frequency in MHz or ham band (e.g., "14.2" or "20m")

Optional Global Options:
  --units {meters,feet}        Units for heights/distances (default: meters)
  --soil-sigma SIGMA           Soil conductivity in S/m (default: 0.005)
  --soil-epsr EPSR             Soil relative permittivity (default: 13.0)
  --no-diffraction             Disable diffraction analysis (default: enabled)
  --plot-mode {elevation,terrain}  Plot mode (default: elevation)
  --lib PATH                   Path to OpenYTWCore library (or set OPENHFTA_LIB)
  --aoa FILE                   Angle of Arrival data file (band auto-detected from frequency)
  --output FILE                Save plot to file (supports svg, pdf, png, etc.)
  --debug                      Enable debug output
  --debug-angle ANGLE          Debug exit angle in degrees (default: 0.0)

Examples:
  # Single terrain file
  hfta --profile terrain.pro --freq 20m --antenna-type 2-Ele --heights 10 20\\*
  
  # Multiple terrain files with different antenna settings  
  hfta --profile north.pro --antenna-type 2-Ele --heights 10 20\\* \\
          --profile south.pro --antenna-type Dipole --heights 15 \\
          --freq 14.2
  
  # Terrain visualization
  hfta --profile terrain1.pro --profile terrain2.pro --plot-mode terrain
"""
    print(help_text)

def main():
    # Parse command line arguments using custom parser
    try:
        profile_configs, global_args = parse_profile_blocks(sys.argv[1:])
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Use --help for usage information", file=sys.stderr)
        return 1
    
    # Process each profile configuration
    processed_configs = []
    antenna_type_map = {
        'Dipole': 1, '2-Ele': 2, '3-Ele': 3, '4-Ele': 4,
        '5-Ele': 5, '6-Ele': 6, '8-Ele': 7
    }
    
    for config in profile_configs:
        # Parse height and phase information
        antenna_heights = []
        antenna_phases = []
        
        for height_str in config['heights']:
            height, phase = parse_height_and_phase(height_str, global_args['units'])
            antenna_heights.append(height)
            antenna_phases.append(phase)
        
        # Override with explicit phases if provided - REMOVED since --phases option was removed
        
        config['processed_heights'] = antenna_heights
        config['processed_phases'] = antenna_phases
        config['antenna_pattern_type'] = antenna_type_map[config['antenna_type']]
        
        # Validate profile file exists
        if not os.path.exists(config['profile']):
            print(f"Error: Profile file '{config['profile']}' not found", file=sys.stderr)
            return 1
        
        processed_configs.append(config)
    
    # Validate AoA file if specified
    if global_args['aoa'] and not os.path.exists(global_args['aoa']):
        print(f"Error: AoA file '{global_args['aoa']}' not found", file=sys.stderr)
        return 1
    
    try:
        # Handle terrain plot mode
        if global_args['plot_mode'] == 'terrain':
            plot_multiple_terrain_profiles(processed_configs, global_args, global_args['output'])
            return 0

        # Parse frequency specification
        try:
            frequency_mhz = parse_frequency(global_args['freq'])
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        # Load AoA data if specified
        aoa_data = None
        if global_args['aoa']:
            aoa_data = parse_aoa_file(global_args['aoa'], frequency_mhz)
            if aoa_data:
                print(f"Loaded AoA data: {len(aoa_data)} angle points")
            else:
                print("Warning: No valid AoA data found")
        
        # Analyze patterns for all profiles
        all_results = []
        
        for i, config in enumerate(processed_configs):
            print(f"Analyzing profile {i+1}/{len(processed_configs)}: {Path(config['profile']).name}")
            print(f"  {frequency_mhz:.1f} MHz with {config['antenna_type']} antenna")
            print(f"  Heights: {config['heights']} {global_args['units']}")
            if config['move_tower'] > 0:
                print(f"  Tower moved back: {config['move_tower']} {global_args['units']}")
        
        print(f"Diffraction: {'Disabled' if global_args['no_diffraction'] else 'Enabled'}")
        
        for config in processed_configs:
            angles, pattern_db = analyze(
                profile_path=config['profile'],
                frequency_mhz=frequency_mhz,
                antenna_heights=config['processed_heights'],
                antenna_phases=config['processed_phases'],
                soil_epsr=global_args['soil_epsr'],
                soil_sigma=global_args['soil_sigma'],
                diffraction_disable=global_args['no_diffraction'],
                debug_enable=global_args['debug'],
                debug_angle=global_args['debug_angle'],
                lib_path=global_args['lib'],
                move_tower=config['move_tower'],
                antenna_pattern_type=config['antenna_pattern_type']
            )
            
            # Compute FOM if AoA data available
            fom = None
            if aoa_data:
                fom = compute_fom(pattern_db, aoa_data)
            
            all_results.append({
                'config': config,
                'angles': angles,
                'pattern_db': pattern_db,
                'fom': fom
            })
        
        # Print summary statistics for each profile
        for i, result in enumerate(all_results):
            config = result['config']
            pattern_db = result['pattern_db']
            fom = result['fom']
            
            max_gain = np.max(pattern_db)
            max_angle = result['angles'][np.argmax(pattern_db)]
            
            print(f"\nProfile {i+1} ({Path(config['profile']).name}):")
            print(f"  Maximum gain: {max_gain:.1f} dB at {max_angle:.2f}°")
            if fom is not None:
                print(f"  Figure of Merit (FOM): {fom:.1f}")
        
        # Plot results
        plot_multiple_patterns(all_results, frequency_mhz, not global_args['no_diffraction'], 
                              aoa_data, global_args, global_args['output'])
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if global_args['debug']:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
