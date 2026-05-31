# Contributing to OpenHFTA

Thank you for your interest in contributing. OpenHFTA is a preservation project: its primary obligation is numerical compatibility with the original HFTA binary (Richard Dean Straw, N6BV). Every contribution is evaluated against that constraint first.

## Core principle

Compatibility with the original HFTA output is the acceptance criterion for all numerical contributions. If a change produces a different elevation pattern than HFTA would for the same input, it is not a bug fix — it is a behavioral change and belongs in a fork.

## Building

```sh
make
```

Requires `gcc-fortran` (gfortran) and a POSIX `make`. The Makefile builds `libopenytwcore.so` (Linux), `.dylib` (macOS), or `.dll` (Windows via MinGW).

## Running the test suite

```sh
make test                          # differential tests (requires Wine on Linux)
python3 -m unittest test_hfta -v   # unit tests (no Fortran library required)
```

The differential tests compare OpenHFTA output against the original HFTA binary running under Wine. They require access to the private legacy DLL test data (see below).

## gfortran compiler flags

The flags in the Makefile are not negotiable:

```
-O0 -mfpmath=387 -fexcess-precision=fast -ffast-math \
-fno-associative-math -fno-reciprocal-math
```

These reproduce the 80-bit x87 intermediate precision of the original Compaq Visual Fortran build. The UTD implementation relies on near-singular cotangent/transition-function cancellation at shadow boundaries; this cancellation is precision-dependent. Changing these flags will cause the differential tests to fail. Do not optimize them away.

## Private legacy test data

Differential tests require `test/YTWCore.dll` and `test/DFORRT.DLL`, which are held in a private repository (`RioDXGroup/openhfta-private-testdata`) due to redistribution constraints. Maintainers with access can configure the `HFTA_TESTDATA_SSH_KEY` repository secret in GitHub Actions to enable these tests on CI. Without the key, the differential test step is skipped and a notice is printed.

## What contributions are welcome

- Documentation improvements (README, docs/, code comments explaining *why*)
- Additional unit tests for the Python layer (`test_hfta.py`)
- Bug fixes in the terrain profile parser, AoA parser, or CLI that do not alter the numerical output
- Portability fixes for build or packaging on supported platforms
- Corrections to the paper (`paper/paper.md`, `paper/paper.bib`)

## What contributions are not accepted here

- Changes to the Fortran source that alter numerical output, even if the new output is "more correct" by some metric — correctness is defined as agreement with HFTA
- New electromagnetic models, additional propagation modes, or extended frequency ranges
- Refactoring of the Fortran engine that changes compiler-flag requirements

If you want to extend the physics, please fork the project.

## Reporting issues

Open a GitHub issue. Include the terrain profile input, the OpenHFTA command line, and the discrepancy observed (ideally alongside the HFTA reference output if available).

## Code style

Python code follows PEP 8. Fortran code preserves the style of the existing source. Comments explain *why*, not *what*.

## Licensing

Contributions are accepted under the repository's current license. By submitting a pull request you confirm that you have the right to contribute the code under those terms.
