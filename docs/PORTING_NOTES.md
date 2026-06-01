# Porting Notes: Matching Legacy HFTA/YTW Numerics in OpenHFTA

This document records the numerical archaeology behind OpenHFTA's reimplementation of the legacy HFTA/YTW Fortran core. The goal is not to define a new idealized implementation, but to reproduce legacy HFTA results as closely as practical on modern compilers.

The effort moved the core Fortran numerical routines from their legacy environment (Compaq Visual Fortran on x86) to a modern one (GNU gfortran), with an emphasis on functionally equivalent numerical behavior.

The process revealed that the legacy HFTA code is highly sensitive to the specifics of the compiler and floating-point environment. Achieving a near-perfect match required a deep understanding of not just the physics algorithms, but also the behavior of the compilers themselves.

### CI Reproducibility

OpenHFTA's CI uses the Nix build as the primary compatibility gate. The purpose of CI is not broad Linux distribution coverage; it is to prove that the current implementation still matches the legacy HFTA/YTW numerical behavior under a known toolchain. Running the complete differential suite in Nix pins the relevant compiler, Wine, MinGW runtime, and Python dependency versions through `flake.lock`, making future numerical regressions easier to reproduce and bisect.

Distribution-provided toolchains are still useful for ad hoc portability checks, but they add external release and packaging variables that are not central to the compatibility claim. If a compiler or runtime update changes the numerical behavior, the Nix environment gives that change an explicit repository-level audit trail.

### 1. Key Numerical Instabilities and Sensitive Algorithms

The core of the software implements the Uniform Theory of Diffraction (UTD). While robust in theory, its implementation contains several points of extreme numerical sensitivity.

#### 1.1 The UTD Transition Function (`FFCT`) and Wedge Diffraction (`WD`)

The most critical point of instability in the entire codebase lies in the calculation of the UTD diffraction coefficient, specifically in the `WD` subroutine and its dependency, `FFCT`.

-   **The Problem:** The UTD formula involves terms of the form `cot(beta) * F(X)`, where `F(X)` is the UTD Transition Function (approximating the Fresnel integral). When a ray path aligns with a shadow or reflection boundary, the `cot(beta)` term approaches a singularity (infinity), while the argument `X` to the transition function approaches zero. The `F(X)` function must then also approach zero in a very specific way so that their product remains finite.
-   **The Sensitivity:** The calculation of the arguments to these functions, and the functions themselves, is extremely sensitive to floating-point precision. The legacy-reference "pathological" bug (refer to the unit tests), which caused a >10 dB discrepancy, was traced to the `TAN` function inside `WD` returning a value 128 times different from legacy HFTA due to its argument being femtounits closer to a pole.
-   **Conclusion:** Any work on this code must treat the `WD` and `FFCT` subroutines as highly sensitive. Standard `REAL*4` (single-precision) arithmetic is insufficient to guarantee stable results across all geometric conditions.

#### 1.2 Line-of-Sight Geometry (`REFL` and inlined checks)

The second major source of sensitivity is the ray-tracing logic used to determine line-of-sight (LOS). This logic appears in the `REFL` subroutine and is also inlined directly within `YTWCore1`'s "illumination" loop (lines 396-408).

-   **The Problem:** The algorithm determines if a ray is blocked by iteratively calculating the ray's height and comparing it to the terrain height at each segment. The formula is `HtRay = RayHeightCurrent + TAN(LaunchAngle) * delta_distance`.
-   **The Sensitivity:** When a ray path passes extremely close to a terrain vertex (a "near-miss" or "grazing" path), this iterative calculation is subject to cumulative floating-point rounding errors. A difference of `1e-6` in a calculated ray height can flip the boolean outcome of the `if (ray_height < terrain_height)` check.
-   **The Consequence:** This is not a minor error. A flipped boolean decision has a cascading effect:
    1.  In `YTWCore1`, it can incorrectly mark a diffraction point as being in shadow.
    2.  In `DIFFDIFF`, it can incorrectly discard an entire diffraction-diffraction path.
    3.  This leads to entire physical components being dropped from the final field summation, causing large, multi-decibel errors in the final output, as observed in the `CS1-163.00.PRO` test case.

### 2. Compiler Behavior: CVF vs. gfortran

The root cause of the numerical sensitivity is the difference in code generation and floating-point handling between the legacy HFTA compiler environment, Compaq Visual Fortran (CVF), and the modern GNU gfortran environment used by OpenHFTA.

-   **CVF and the x87 FPU:** The legacy HFTA binary shows classic signs of being compiled for the x87 floating-point unit. A key behavior of this environment is that **intermediate calculations are often performed using the FPU's internal 80-bit extended-precision registers.** However, the compiler may "spill" these intermediate results to memory (truncating them to 32-bit `REAL*4`) between statements or even within a single complex statement.
-   **The "Spill/Truncate" Artifact:** Our debugging proved that this was a critical, non-obvious feature of the legacy HFTA algorithm's behavior. In the line-of-sight check, the CVF-compiled code calculates `delta_distance`, stores it in a 32-bit memory location, and then reloads it for the final multiplication with `TAN(angle)`. This mid-expression truncation was a source of major divergence.
-   **gfortran and SSE/x87:** Modern gfortran defaults to using SSE registers (`xmm`) which perform strict 32-bit or 64-bit arithmetic. To replicate legacy HFTA behavior, we must force gfortran to use the x87 FPU. Even then, its optimization strategy is different. gfortran is much less prone to "spilling" intermediate values, preferring to keep the entire expression within the 80-bit FPU registers for maximum precision.

**Conclusion:** The gfortran-compiled OpenHFTA code is, from a purely mathematical standpoint, **more accurate** than the legacy HFTA binary. The "mismatches" we observed were largely due to OpenHFTA *not* replicating the precision-losing artifacts of the older compiler.

### 3. Final Recommended gfortran Compiler Flags

To achieve the best possible emulation of legacy HFTA's numerical behavior while fixing its instabilities, a very specific and unconventional set of compiler flags is required. **Do not deviate from this set without extensive regression testing.**

```bash
FFLAGS="-O0 -g -mfpmath=387 -fexcess-precision=fast -ffast-math -fno-associative-math -fno-reciprocal-math -fcheck=all"
```

#### Motivation for Each Flag:

*   **`-O0`**: Only explicitly requested optimizations must be enabled. Even `-O1` causes results to deviate too much from CVF.
*   **`-g`**: Include debugging symbols. Recommended for development, can be removed for a final release build.
*   **`-mfpmath=387`**: This forces the compiler to generate code for the x87 FPU instead of the default SSE registers. This is the only way to access the 80-bit precision and the `fptan` hardware instruction.
*   **`-fexcess-precision=fast`**: This instructs the compiler to take full advantage of the FPU's 80-bit internal registers for intermediate calculations within an expression, emulating the legacy CVF behavior that provides the necessary precision for the sensitive geometric calculations.
*   **`-ffast-math`**: This flag is used as a shortcut to enable several "unsafe" but necessary optimizations. Its most important effect for this project is that it encourages the compiler to replace library calls like `tan()` with the inlined `fptan` hardware instruction.
*   **`-fno-associative-math` / `-fno-reciprocal-math`**: These flags override and disable the most dangerous parts of `-ffast-math`. They prevent the compiler from reordering floating-point operations (e.g., `(a+b)+c` to `a+(b+c)`) or replacing division with multiplication by a reciprocal. This is essential for maintaining numerical reproducibility.
*   **`-fcheck=all`**: An invaluable debugging flag that adds runtime checks for array bounds, etc. Recommended for development, can be removed for a final release build.

This specific combination of flags creates a finely-tuned environment that forces gfortran to behave as closely as possible to the old CVF compiler, resolving the major numerical instabilities while preserving the overall logic of the program. The resulting binary is a faithful and, in many ways, superior port of the legacy HFTA code.
