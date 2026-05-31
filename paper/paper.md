---
title: 'OpenHFTA: An Open-Source HF Terrain Analysis Tool Based on the Uniform Theory of Diffraction'
tags:
  - Python
  - Fortran
  - amateur radio
  - HF propagation
  - terrain analysis
  - UTD
authors:
  - name: Paulo Matias
    orcid: 0000-0002-6504-5141
    equal-contrib: true
    affiliation: 1
  - name: João Paolo Cavalcante Martins Oliveira
    orcid: 0000-0003-4117-953X
    equal-contrib: true
    affiliation: 2
affiliations:
  - name: Universidade Federal de Sao Carlos (UFSCAR), Brazil
    index: 1
  - name: Universidade Federal do Rio Grande do Norte (UFRN), Brazil
    index: 2
date: 31 May 2026
bibliography: paper.bib
---

# Summary

OpenHFTA is a Python command-line tool for computing HF antenna elevation
patterns over irregular terrain profiles.
It wraps OpenYTWCore, a Fortran numerical engine, in a cross-platform package
that preserves the behavior of HFTA [@strawHFTA], the terrain analysis tool
created by Richard Dean Straw (N6BV) and distributed as supplemental software
for *The ARRL Antenna Book*.
The electromagnetic model combines geometrical optics for direct and specular
reflected rays, Fresnel reflection coefficients for horizontally polarized
fields over a lossy dielectric ground, and a scalar specialization of the
Kouyoumjian--Pathak Uniform Theory of Diffraction (UTD) [@kouyoumjian1974]
for terrain ridge diffraction.
Elevation patterns are computed at 0.25-degree resolution from 0.25 to 35
degrees, with support for up to four stacked antenna elements, configurable
soil parameters, multiple simultaneous terrain profiles, angle-of-arrival
weighting, and figure-of-merit computation.

# Statement of Need

Terrain within a few kilometres of an HF transmitting site can shift
radiated power at low elevation angles by up to 20 dB [@breakall1994], a
range that is decisive for DX communication and amateur radio contesting.
HFTA [@strawHFTA] became the standard community tool for this assessment
over two decades but is compiled for 32-bit Windows and is no longer under
active development.
ARRL has stated there are no plans to update it, leaving users on Linux,
macOS, or 64-bit Windows without access to the physics model.
OpenHFTA fills this gap: it provides a compatible, inspectable, and buildable
implementation on modern platforms, with the original HFTA output as the
behavioral acceptance criterion for numerical contributions.

# State of the Field

General HF antenna modeling tools address antenna geometry and ground plane
effects but not multi-ridge terrain diffraction profiles.
Path-loss prediction tools designed for VHF and above apply propagation
models unsuited to HF skywave elevation patterns.
At the research level, Breakall et al. [-@breakall1994] validated a MoM/GTD
terrain model against helicopter-borne beacon measurements at 8, 15, and
27 MHz over irregular terrain in Utah, demonstrating that diffraction over
electrically large ridges is the dominant shaping mechanism for low takeoff
angles.
That code was not publicly released.
The Keller GTD framework [@keller1962] and its Kouyoumjian--Pathak UTD
extension [@kouyoumjian1974] underpin both that research and the HFTA
implementation that OpenHFTA preserves.

# Software Design

OpenHFTA uses a two-layer architecture.
The Python module `hfta.py` handles all user-facing concerns: CLI argument
parsing, terrain profile reading with metric or imperial unit conversion,
Fortran library discovery and loading via `ctypes`, angle-of-arrival file
parsing, figure-of-merit computation, and plot generation using Matplotlib
[@hunter2007] and NumPy [@harris2020].
The electromagnetic computation runs inside two Fortran source files
(`YTWCore1.f90`, `OtherProgs.f90`) compiled as a shared library
(`libopenytwcore.so` on Linux, `.dylib` on macOS, `.dll` on Windows).
Python calls the Fortran entry point `ytwcore1_` by reference, consistent
with gfortran's name-mangling and call conventions.

A significant challenge was matching the numerical behavior of the original
HFTA binary, which was compiled for the x87 floating-point unit with Compaq
Visual Fortran (CVF).
The UTD implementation contains products of near-singular cotangent terms
and transition functions that cancel at shadow boundaries; this cancellation
depends on the 80-bit intermediate precision available in x87 registers.
The adopted gfortran flags
`-O0 -mfpmath=387 -fexcess-precision=fast -ffast-math -fno-associative-math -fno-reciprocal-math`
reproduce the required arithmetic and are documented with full rationale in
the repository.

# Research Impact Statement

OpenHFTA makes two decades of terrain analysis methodology accessible on
present-day hardware and operating systems.
It also provides the first publicly documented, buildable implementation of
the HFTA computation engine, enabling study, verification, and future
development of HF terrain analysis methods.
The repository includes a Python unit test suite covering the terrain profile
parser, angle-of-arrival data parser, figure-of-merit computation, library
discovery, frequency parser, and CLI argument parser, all verified without
requiring the Fortran library.

# Mathematics

The tool computes the elevation pattern as the magnitude of a coherent sum
over all active ray families at each takeoff angle $\theta$:

$$E(\theta) = \sum_m A_m(\theta)\,C_m(\theta)\,e^{j\phi_m(\theta)},$$

where $A_m$ carries the element radiation pattern and path amplitude, $C_m$
carries any reflection or diffraction coefficient, and $\phi_m$ accumulates
path length, element phase offset, and any reflection or diffraction phase.
The output pattern in dB is $P(\theta) = 20\log_{10}|E(\theta)|$, smoothed
with a five-point running average before display.

Specular reflection from a terrain segment with slope angle $\alpha_\text{seg}$
follows $\alpha_\text{out} = 2\alpha_\text{seg} - \alpha_\text{in}$, with
amplitude and phase set by the horizontal Fresnel coefficient over lossy
ground, whose complex relative permittivity is
$\varepsilon_c = \varepsilon_r' - j\sigma/(\omega\varepsilon_0)$
[@balanis1989]:

$$\Gamma_h(\gamma) =
  \frac{\sin\gamma - \sqrt{\varepsilon_c - \cos^2\gamma}}
       {\sin\gamma + \sqrt{\varepsilon_c - \cos^2\gamma}},$$

where $\gamma$ is the ray grazing angle.

Ridge diffraction is computed via the Kouyoumjian--Pathak UTD coefficient
[@kouyoumjian1974], a four-term sum in which each near-singular cotangent
$\cot\!\bigl((\pi \pm \psi)/(2n)\bigr)$ (with $n$ the terrain wedge parameter
and $\psi$ one of $\phi^d \pm \phi^i$) is multiplied by the UTD transition
function

$$F(X) = 2j\sqrt{X}\,e^{jX}\!\int_{\sqrt{X}}^{\infty} e^{-j\tau^2}\,d\tau$$

evaluated at $X = kL\,a^\pm(\psi)$, where $L$ is a path-length distance
parameter and $a^\pm(\psi) = 2\cos^2\!\bigl((2\pi n N^\pm - \psi)/2\bigr)$
selects the nearest shadow or reflection boundary.
As $X\to 0^+$, $F(X)\to 0$ and cancels the cotangent singularity; for large
$X$, $F(X)\to 1$, recovering the ordinary GTD result [@keller1962].
Both the geometric sensitivity of this cancellation and the dependence on
intermediate floating-point precision motivate the specific gfortran flags
discussed in the Software Design section.

Finally, when angle-of-arrival data are available, the figure of merit weights
the elevation pattern by arrival probability $p(\theta)$:

$$\mathrm{FOM} = 10\log_{10}\!\!\left(
  \sum_{\theta=1}^{35} 10^{P(\theta)/10}\,p(\theta)
\right),$$

where $P(\theta)$ is the pattern in dB at integer elevation angle $\theta$.

# AI Usage Disclosure

The OpenHFTA software (Fortran numerical engine and Python interface) was
written by human authors without the use of AI code generation tools.
This manuscript was drafted by humans and validated with the assistance of an
AI writing tool (Claude, Anthropic); all technical content, equations, and
citations were reviewed and verified by the human authors prior to submission.

# Acknowledgements

This work is dedicated to Richard Dean Straw, N6BV (d. July 9, 2025), who
created HFTA and spent two decades teaching the amateur radio community how
terrain shapes HF elevation patterns.
His methodology and algorithms are the foundation of this preservation effort.

# References
