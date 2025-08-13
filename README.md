# OpenHFTA - HF Terrain Analysis

OpenHFTA is a preservation-oriented Python CLI tool for computing elevation
patterns of HF antennas over terrain profiles using the Uniform Theory of
Diffraction (UTD) and Fresnel reflection modeling. It provides a modern
interface to the OpenYTWCore Fortran numerical engine while aiming to reproduce
the behavior of the original HFTA program as closely as possible on modern
systems.

## Dedication and Preservation Goal

This project is dedicated to Richard Dean Straw, N6BV, author of HFTA and a
major contributor to amateur radio antenna and propagation work. Dean served on
the ARRL staff for 15 years, retired as Senior Assistant Technical Editor in
2008, edited multiple editions of *The ARRL Antenna Book*, and wrote tools
including HFTA, TLW, and Yagi for Windows. ARRL's remembrance notes that Dean
died on July 9, 2025, after an extended battle with Parkinson's disease:
[Richard Dean Straw, N6BV, ARRL "Antenna Expert," Silent Key](https://www.arrl.org/news/richard-dean-straw-n6bv-arrl-antenna-expert-silent-key).
ARRL also continues to list HFTA among the supplemental software for *The ARRL
Antenna Book*, while noting that HFTA, TLW, and YW were developed for 32-bit
Windows and that there are no plans to update them:
[ARRL Antenna Book Reference](https://www.arrl.org/arrl-antenna-book-reference).

OpenHFTA exists to preserve the practical behavior of HFTA for present-day
users and systems. Its primary goal is not to replace Dean's work with a new
terrain-analysis model, but to make a close, inspectable, and maintainable
reimplementation available for study, validation, and continued use.

## Features

- **Terrain Analysis**: Compute antenna elevation patterns over complex terrain profiles
- **Diffraction Modeling**: UTD-based diffraction analysis (enabled by default, can be disabled with `--no-diffraction`)
- **Fresnel Reflection**: Accurate ground reflection calculations with complex soil parameters
- **Multi-Element Support**: Analyze antenna arrays with customizable heights, phases, and patterns
- **Antenna Types**: Dipole, 2-Ele, 3-Ele, 4-Ele, 5-Ele, 6-Ele, 8-Ele (no 7-Ele; 8-Ele maps to core type 7)
- **Phase Control**: Simple asterisk notation (e.g., `10*`) for 180° out-of-phase elements
- **Move Tower**: Shift antenna position relative to terrain profile
- **Multiple Profile Comparison**: Analyze and compare multiple terrain files simultaneously
- **Dual Plot Modes**: Terrain profile visualization or elevation pattern analysis
- **Angle of Arrival (AoA)**: Support for AoA probability data and Figure of Merit computation
- **Flexible Units**: Support for both metric and imperial units for CLI inputs
- **Professional Graphics**: Publication-quality plots with multiple output formats (PNG, SVG, PDF)
- **HFTA Compatibility Focus**: Implements the major behavior of the original
  HFTA GUI with compatibility as the guiding constraint

## Project Scope and Contributions

OpenHFTA treats the original HFTA output as the compatibility target. Pull
requests that intentionally improve or modernize the numerical engine in ways
that break compatibility with original HFTA behavior will not be accepted here,
even when the change is technically defensible as a better model. Users who want
to explore a new terrain-analysis engine are encouraged to fork the project and
experiment there.

Compatibility-preserving contributions are welcome. In particular, pull
requests improving documentation, tests, code comments, variable names, or the
accuracy of existing explanations are encouraged. Numerical changes should be
framed as compatibility fixes and, where possible, backed by comparisons against
the original HFTA behavior.

## Installation

### Option 1: System Installation

1. **Install Python dependencies**:

   On Debian or Ubuntu:
   ```bash
   sudo apt install python3-numpy python3-matplotlib
   ```
   On Arch Linux:
   ```bash
   sudo pacman -S python-numpy python-matplotlib
   ```

2. **Build and install OpenHFTA**:
   ```bash
   make && sudo make install
   ```

3. **Run the tool**:
   ```bash
   hfta --help
   ```

4. **Uninstall** (if needed):
   ```bash
   sudo make uninstall
   ```

### Option 2: Local Development

1. **Build the Fortran core**:
   ```bash
   make
   ```

2. **Run the tool from the working tree**:
   ```bash
   ./hfta.py --help
   ```

## Usage

The examples below assume `hfta` is installed or available in the active shell.
For local development from the working tree, use `./hfta.py` in place of
`hfta`.

### Basic Analysis

```bash
# Analyze 20m antenna pattern over terrain
hfta --profile terrain.pro --freq 14.2

# Disable diffraction analysis
hfta --profile terrain.pro --freq 14.2 --no-diffraction
```

### Antenna Stacks

```bash
# Two-element stack at 20m and 40m heights
hfta --profile terrain.pro --freq 14.2 \
  --heights 20 40 --antenna-type 2-Ele

# Phased array with 180° phase difference using asterisk notation
hfta --profile terrain.pro --freq 14.2 \
  --heights 15 '30*' --antenna-type 2-Ele
```

### Soil Parameters

```bash
# Custom soil parameters
hfta --profile terrain.pro --freq 14.2 \
  --soil-epsr 15.0 --soil-sigma 0.01

# Use predefined soil types (see Common Soil Parameters section)
hfta --profile terrain.pro --freq 14.2 \
  --soil-epsr 13.0 --soil-sigma 0.002  # Poor soil
```

### Move Tower Feature

```bash
# Move tower back 100 meters from current position
hfta --profile terrain.pro --freq 14.2 \
  --move-tower 100
```

### Multiple Terrain Files for Comparison

```bash
# Compare two terrain profiles with different antenna types
hfta --profile terrain1.pro --antenna-type 2-Ele --heights 10 20 \
  --profile terrain2.pro --antenna-type Dipole --heights 15 \
  --freq 14.2

# Advanced comparison with phase notation and tower movement
hfta --profile profile1.pro --antenna-type 3-Ele --heights 10 '15*' 20 --move-tower 50 \
  --profile profile2.pro --antenna-type Dipole --heights 12 \
  --freq 14.2

# Terrain profile comparison (no elevation analysis)
hfta --profile terrain1.pro --profile terrain2.pro --plot-mode terrain
```

**Multiple Profile Syntax**: Each terrain file is specified with its own `--profile` option followed by its specific antenna configuration options (`--antenna-type`, `--heights`, `--move-tower`) before the next `--profile` option.

**Profile-Specific Options** (apply to the preceding `--profile`):
- `--antenna-type`: Dipole, 2-Ele, 3-Ele, ..., 8-Ele (default: Dipole)
- `--heights`: Space-separated heights with optional `*` for out-of-phase (e.g., `10 '15*' 20`)
- `--move-tower`: Distance to move tower back (default: 0)

### Plot Options

```bash
# Plot terrain profile instead of elevation pattern
hfta --profile terrain.pro --plot-mode terrain

# Save plot to file (supports svg, pdf, png formats)  
hfta --profile terrain.pro --freq 14.2 --output pattern.pdf
```

### Angle of Arrival Analysis

```bash
# Multi-band AoA data (ARRL format, band auto-detected from frequency)
hfta --profile terrain.pro --freq 14.2 \
  --aoa 3Y-EU.PRN
```

## Common Soil Parameters

The following table lists common soil conductivity and dielectric constant values as used in the original HFTA GUI. These values can be used with the `--soil-sigma` and `--soil-epsr` options:

| Soil Type | Conductivity (S/m) | Dielectric Constant | Usage |
|-----------|-------------------|-------------------|-------|
| Very Poor Soil | 0.001 | 5 | `--soil-sigma 0.001 --soil-epsr 5` |
| Sandy, Dry Soil | 0.002 | 10 | `--soil-sigma 0.002 --soil-epsr 10` |
| Poor Soil | 0.002 | 13 | `--soil-sigma 0.002 --soil-epsr 13` |
| Average Soil | 0.005 | 13 | `--soil-sigma 0.005 --soil-epsr 13` (default) |
| Good Soil | 0.010 | 14 | `--soil-sigma 0.010 --soil-epsr 14` |
| Very Good Soil | 0.030 | 20 | `--soil-sigma 0.030 --soil-epsr 20` |
| Fresh Water | 0.001 | 81 | `--soil-sigma 0.001 --soil-epsr 81` |
| Salt Water | 5.000 | 80 | `--soil-sigma 5.000 --soil-epsr 80` |

**Note**: The original HFTA GUI displayed conductivity values in mS/m, but the Fortran core expects values in S/m. The values in the table above are already converted to S/m for direct use with this CLI tool.

## File Formats

### Terrain Profiles (.PRO)

Terrain profile files contain distance and height pairs:

```
meters
0      187.1
30     187.8
60     191.2
90     195.0
...
```

The first line specifies units (`meters` or `feet`). Distances and heights are in the specified units. The Python interface automatically converts all terrain data to feet as required by the Fortran core.

**Important**: The units specified in terrain profile files are independent of the `--units` CLI option. The terrain file units control how the profile data is interpreted, while the `--units` option only affects CLI-provided antenna heights and move-tower distances.

### AoA Data Files

Multi-column files containing Angle of Arrival probability data (in percentage) for various bands:

```
# Example AoA file (ARRL format)
Elev      80m    40m    30m    20m    17m    15m    12m    10m
 1        9.1    8.7   10.8    9.9    5.3    6.5   11.1   10.5
 2        5.3    4.0    6.4    8.9    7.4    7.3    7.8   11.5
 3        1.1    2.9    4.0    7.5    9.0    9.6    9.0    9.3
```

## Technical Details

### Diffraction Control

- **Default behavior**: Diffraction enabled (more accurate for HF frequencies)
- **To disable**: Use `--no-diffraction` flag
- **ABI details**: The Fortran core expects `DiffractionDisable` where 1=disable, 0=enable

### Core Implementation

OpenHFTA uses the OpenYTWCore Fortran implementation accessed via ctypes:

- **Symbol**: `ytwcore1_` (note the trailing underscore)
- **ABI**: All scalar parameters passed by reference (POINTER types in ctypes)
- **Arrays**: Passed as pointers to contiguous memory
- **Units**: Terrain profile automatically converted to feet for Fortran core, antenna heights converted to feet internally, angles in degrees

### Angle Grid

The elevation pattern is computed at 140 angle samples from 0.25° to 35.0° in 0.25° steps, matching the original HFTA specification.

## Theory and Background

For detailed information about the theoretical foundations:

- [docs/THEORY.md](docs/THEORY.md): Comprehensive overview of UTD theory, Fresnel reflection, terrain modeling, and the mathematical foundations underlying the elevation pattern calculations
- [docs/PORTING_NOTES.md](docs/PORTING_NOTES.md): Technical details about the Fortran core implementation, numerical sensitivity, and compiler considerations

## Examples

See the `test/pro/` directory for sample terrain profiles that can be used for testing and validation.

## Troubleshooting

### Library Not Found

If you get "Cannot find OpenYTWCore library":

```bash
# Build the shared library first
make

# Or specify explicit path
./hfta.py --lib ./libopenytwcore.so --profile terrain.pro --freq 14.2
```

### Python Dependencies

Install required packages from your distribution, for example:

```bash
sudo apt install python3-numpy python3-matplotlib
```

### Symbol Errors

If you get "Symbol ytwcore1_ not found", ensure you're using the correct Fortran library built from this repository. The symbol name includes the trailing underscore as per gfortran conventions.


## Legacy DLL Test Data

The original HFTA DLLs are not distributed with this repository. Differential
tests against the legacy implementation are enabled only when `YTWCore.dll` and
`DFORRT.DLL` are present in `test/`; those files are ignored by git. Without
them, `make test-core` skips the legacy comparison but the rest of the test
suite still runs.
