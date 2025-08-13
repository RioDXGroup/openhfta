# THEORY: Foundations for HFTA-Style Terrain-Modified HF Antenna Patterns

Audience: Physics/Engineering second-year undergraduate (vector calculus, basic E&M, complex numbers).

This document explains the physical model behind OpenHFTA and HFTA-style calculations. It connects the GO, Fresnel, GTD, and UTD formulas to the quantities actually computed by the Fortran core, with emphasis on the scalar approximations used for HFTA-compatible terrain patterns.

## How to Read This Document

The main text is a code-oriented theory map: it explains which physical ideas are being used, how they are specialized by the Fortran implementation, and where the implementation deliberately uses scalar HFTA-style approximations. A reader who wants only to understand the program flow can read Sections 1-3, 5-7, and 10 first, then return to the UTD details in Section 4. A reader who wants the diffraction theory should read Section 4.1 and 4.5 first, then Appendix A, then Sections 4.2-4.4.

Useful prerequisites:

- Complex phasors: represent a sinusoidal field as a complex number, track phase with path length, add fields coherently, and convert final magnitude to dB with `20 log10(abs(E))`.
- Vector geometry in a plane: slopes, angles, dot-product intuition, and the specular reflection rule for a locally straight terrain segment.
- Basic electromagnetic boundary conditions: tangential electric and magnetic fields are continuous at an interface; Fresnel coefficients follow from applying those conditions to plane waves.
- Wave optics intuition: shadow boundaries, interference, Fresnel zones, and why an obstacle edge produces a diffracted field.
- High-frequency asymptotics: GO/GTD/UTD are ray-based approximations that become most natural when terrain dimensions are many wavelengths across.
- Numerical bookkeeping: arrays indexed by terrain point and by 0.25-degree angle bin, plus path-family logic that decides which rays contribute to which output bins.

Important scope notes:

- Pattern type: far-field skywave elevation patterns along one azimuthal terrain cut.
- Geometry: a 2D terrain profile represented as a piecewise-linear polyline.
- Polarization: the implemented field calculation uses horizontal polarization. This matches HFTA's intended use with horizontally polarized Yagis, quads, and dipoles; vertical polarization is included here as comparison context for the validation literature.
- Surface-wave calculation: outside the skywave pattern model. Ground-wave field strength requires a different propagation formulation.
- Frequency range: HF, roughly 3-30 MHz, though many formulas are general high-frequency asymptotics.
- Angle convention: elevation angle is measured from the local horizontal. The Fortran core bins output every 0.25 degree from 0.25 to 35.0 degrees.
- Units in the core: feet, MHz, radians, and complex field phasors.
- Phasor convention: the theory below uses the common UTD convention $e^{+j\omega t}$ with propagation factors $e^{-jks}$. The Fortran code follows HFTA's phase bookkeeping; Sections 6, 7, and 10 describe how each path family forms its accumulated phasor.

---

## 1. Wave Basics and Notation

- Speed of light: $c \approx 3\times10^8\,\rm m/s$.
- Wavelength: $\lambda = c/f$. In feet, for $f$ in MHz, $\lambda_{\rm ft} \approx 984/f_{\rm MHz}$. The main ray and phase calculations use `LAMBDA_FT = 983.5712/f_MHz`; `YUTD` also contains `983.84998/f_MHz` inside a normalization factor that algebraically cancels to $1/\sqrt{L_{\rm waves}}$ for a fixed positive caller-supplied distance parameter.
- Wavenumber: $k = 2\pi/\lambda$.
- For a spherical wave in free space:
  $$E(r) \propto \frac{1}{r}e^{-jkr}.$$
- Pattern dB from field magnitude:
  $$P_{\rm dB}=20\log_{10}|E|.$$

In a complete field-strength ray model, spreading is carried by ray-tube factors such as $1/r$ or UTD square-root spreading terms. This HFTA-style code produces a relative elevation pattern: GO contributions carry antenna pattern and path phase; the main GO sweep evaluates `FRESNEL` on reflected rays and applies the returned phase while keeping the ordinary GO amplitude in `ElemPatternAmp`; helper `REFL` calls return a segment-local `ReflAmp` that diffraction paths multiply by. Common far-zone range constants cancel from the plotted pattern reference. Diffraction paths add a scalar UTD distance normalization through the distance parameter passed to `YUTD`.

---

## 2. Geometrical Optics (GO)

Geometrical Optics represents propagation as rays carrying phase and amplitude. It is used for:

1. Direct rays that clear the terrain.
2. Specularly reflected rays from locally planar terrain segments.
3. Propagation legs before and after diffraction events.

For reflection from a local terrain segment, the code uses the segment slope and the incident ray angle to form the specular outgoing angle:

$$\alpha_{\rm out} = 2\alpha_{\rm seg}-\alpha_{\rm in}.$$

GO alone predicts discontinuities at shadow and reflection boundaries: a direct ray abruptly appears or disappears. Diffraction theory supplies the transition field in and near those shadow regions.

---

## 3. Reflection From Lossy Ground

Real soil is modeled as a lossy dielectric half-space with complex relative permittivity

$$\varepsilon_c = \varepsilon_r' - j\frac{\sigma}{\omega\varepsilon_0},\qquad \omega=2\pi f,$$

where $\varepsilon_r'$ is the real relative permittivity, $\sigma$ is conductivity in S/m, and $\varepsilon_0 \approx 8.854\times10^{-12}\,\rm F/m$.

For incidence from air onto lossy ground, with $\theta_i$ measured from the local surface normal:

- Horizontal/TE polarization:
  $$\Gamma_h(\theta_i) =
  \frac{\cos\theta_i-\sqrt{\varepsilon_c-\sin^2\theta_i}}
       {\cos\theta_i+\sqrt{\varepsilon_c-\sin^2\theta_i}}.$$

- Vertical/TM polarization:
  $$\Gamma_v(\theta_i) =
  \frac{\varepsilon_c\cos\theta_i-\sqrt{\varepsilon_c-\sin^2\theta_i}}
       {\varepsilon_c\cos\theta_i+\sqrt{\varepsilon_c-\sin^2\theta_i}}.$$

HFTA and this Fortran core use the horizontal coefficient. Written in terms of a surface grazing angle $\gamma=\pi/2-\theta_i$, the horizontal coefficient is equivalently

$$\Gamma_h(\gamma) =
\frac{\sin\gamma-\sqrt{\varepsilon_c-\cos^2\gamma}}
     {\sin\gamma+\sqrt{\varepsilon_c-\cos^2\gamma}}.$$

Implementation details:

- `FRESNEL` implements this algebraic form using `ABS` of the angle passed by the ray tracer. For flat ground that angle is the surface grazing angle. On a segment with slope angle $\alpha_{\rm seg}$, the ray tracer first applies $\alpha_{\rm out}=2\alpha_{\rm seg}-\alpha_{\rm in}$. The grazing angle relative to that tilted segment is $|\alpha_{\rm out}-\alpha_{\rm seg}|$; the code passes $\alpha_{\rm out}$ to `FRESNEL`, so the lossy-ground coefficient is evaluated from the outgoing elevation angle after the slope-based reflection geometry has been applied.
- `SOIL_COND_PARAM` is expected in S/m at the Python CLI boundary. The Fortran expression `SOIL_COND_PARAM * 18000.0 / FREQ_MHZ` is the approximation to $\sigma/(\omega\varepsilon_0)$ when frequency is in MHz.
- `FRESNEL` returns `AmpOut = AmpIn|\Gamma_h|` and `PhaseOut = PhaseIn + arg(\Gamma_h)`; the ray-family code then decides whether that returned amplitude is used in the accumulated phasor.
- The executable path uses the horizontal/TE coefficient. The vertical/TM formula and Brewster-angle behavior show what changes in models for vertical monopoles.

---

## 4. Diffraction: Beyond GO Shadow Boundaries

Keller's Geometrical Theory of Diffraction (GTD) extends GO by adding diffracted rays from edges, vertices, and grazing interactions. For an edge, the diffracted ray satisfies a Fermat-principle condition: in a homogeneous medium, incident and diffracted rays make equal angles with the edge tangent. The diffracted field is proportional to the incident field at the edge, a local diffraction coefficient, a spreading factor, and a phase factor.

### 4.1 GTD Wedge Coefficients

For a perfectly conducting wedge, a common scalar GTD coefficient has the form

$$D_{s,h} =
\frac{e^{-j\pi/4}}{n\sqrt{2\pi k}\sin\beta_0}
\sin\left(\frac{\pi}{n}\right)
\left[
\frac{1}{\cos(\pi/n)-\cos((\phi^d-\phi^i)/n)}
\mp
\frac{1}{\cos(\pi/n)-\cos((\phi^d+\phi^i)/n)}
\right],$$

where:

- $D_s$ and $D_h$ are the soft and hard scalar coefficients.
- $\beta_0$ is the angle between the incident/diffracted ray and the edge tangent.
- $\phi^i,\phi^d$ are incidence and diffraction angles measured around the wedge.
- $n$ is the wedge parameter. With wedge angle $WA=(2-n)\pi$, $n=2-WA/\pi$.

This GTD coefficient is useful away from shadow and reflection boundaries. At a boundary the cotangent denominator can vanish; the singularity marks the point where the ordinary GTD asymptotic expression must be replaced by a uniform transition expression.

### 4.2 UTD Transition Functions

Kouyoumjian and Pathak's UTD replaces the singular GTD coefficient with a uniform coefficient valid in the transition regions next to shadow and reflection boundaries. For a straight perfectly conducting wedge, their Eq. (25) is a four-term cotangent expression in which the same distance parameter $L$ appears in all four transition-function arguments:

$$\begin{aligned}
D_{s,h} &=
\frac{-e^{-j\pi/4}}{2n\sqrt{2\pi k}\sin\beta_0}
\bigg[
\cot\left(\frac{\pi+(\phi^d-\phi^i)}{2n}\right)F(kL a^+(\phi^d-\phi^i))
+ \cot\left(\frac{\pi-(\phi^d-\phi^i)}{2n}\right)F(kL a^-(\phi^d-\phi^i))\\
&\qquad\mp
\cot\left(\frac{\pi+(\phi^d+\phi^i)}{2n}\right)F(kL a^+(\phi^d+\phi^i))
\mp
\cot\left(\frac{\pi-(\phi^d+\phi^i)}{2n}\right)F(kL a^-(\phi^d+\phi^i))
\bigg].
\end{aligned}$$

The code follows this four-term structure with its own terrain-angle tuple. `WD` first sets `psi_work = PHR - PhiP`, evaluates the two parity cases corresponding to cotangent arguments $(\pi+\psi)/(2n)$ and $(\pi-\psi)/(2n)$, then repeats the same two parity cases with `psi_work = PHR + PhiP`. Thus the first pair maps to the $\phi^d-\phi^i$ angular family and the second pair maps to the $\phi^d+\phi^i$ angular family. `YUTD` then combines the four returned terms as `(term1 + term2) - (term3 + term4)`. The routine carries this one scalar combination into the horizontal terrain calculation instead of carrying separate soft and hard coefficients. All four terms receive one scalar distance parameter from the caller.

For curved edges or curved wedge faces, the same local-wedge construction is retained, but the transition terms receive separate boundary distance parameters. In the lecture notes and in Kouyoumjian-Pathak Eq. (58), the incident-boundary term uses $L^i$ and the reflected-boundary terms use $L^{r0}$ and $L^{rn}$. That distinction matters here because `WD` has only one `L_waves` argument; it is organized like the straight-wedge coefficient, with terrain-specific path-length proxies supplied by its callers.

For angular separation $\psi$ from a boundary,

$$a^\pm(\psi)=2\cos^2\left(\frac{2\pi nN^\pm-\psi}{2}\right),$$

where $N^\pm$ is the integer that selects the nearest relevant shadow or reflection boundary.

The transition function is

$$F(X)=2j\sqrt{X}\,e^{jX}\int_{\sqrt{X}}^\infty e^{-j\tau^2}\,d\tau.$$

It has the limiting behavior:

- $F(X)\to0$ as $X\to0^+$, cancelling the cotangent singularity at the boundary.
- $F(X)\to1$ for large positive $X$, recovering the ordinary GTD coefficient far from a transition region.

The Fortran `FFCT` function follows the same three argument ranges shown in the UTD lecture material: a small-argument approximation for $|X|\le0.3$, a table-driven affine approximation for $0.3<|X|\le5.5$, and a large-argument asymptotic form for $|X|>5.5$. It evaluates the approximation with `ABS(X)` and then conjugates the result when `X < 0`. This is numerically sensitive because `WD` often computes products of a near-singular cotangent and a transition function tending to zero.

The Fortran routines use an angular tuple tailored to the terrain scan. `ANGIN` returns `Incl`, `PhiP`, and the starting `PHR` scan value from the two adjacent terrain-segment angles and the incident ray angle. Its mapping is explicit in the code:

- if `Slpe1 < 0`, `Incl = abs(Slpe1) + pi + Slpe2`;
- otherwise, `Incl = pi - abs(Slpe1) + Slpe2`;
- `PhiP = Slpe1 - Incidence`;
- `PHR` is initialized for a 0.25-degree observation-angle scan and later mapped back to an absolute ray angle by `ANGHORIZ`.

`YUTD` then computes the wedge parameter as

$$n = 2 - \frac{\texttt{Incl}}{\pi},$$

and `WD` evaluates its four terms first with `PHR - PhiP` and then with `PHR + PhiP`. In this coordinate tuple, `Incl` selects the wedge parameter, `PHR` is the scanned outgoing angle around the vertex, and `PhiP` is the incident-side offset used to form the two UTD angular combinations. Some callers use the local name `AInclA` for the same angular value passed as `Incl` to `YUTD`, matching the debug label `AInclA=`.

Kouyoumjian and Pathak treat grazing incidence as a geometric limiting case on a wedge face. For a straight perfectly conducting wedge, grazing occurs at $\phi'=0$ or $\phi'=n\pi$. In that limit the soft scalar coefficient is set to zero, and the hard scalar coefficient receives a factor of $1/2$ because the incident and reflected GO fields merge on the face; the total field traveling along the face is split into incident and reflected halves. For curved screens and curved wedges the situation is stricter: as grazing is approached, one of the boundary distance parameters can tend to zero, transition regions can overlap surface-diffraction regions, and the article switches to far-zone unity-transition or reciprocity arguments depending on the source and field distances.

The Fortran correction is a broader scalar rule applied later in the calculation. `YUTD` first evaluates the four `WD` terms, combines them as `(term1 + term2) - (term3 + term4)`, normalizes the result by the real factor $1/\sqrt{L_{\rm waves}}$, and extracts the magnitude. It then halves that final magnitude whenever the signed value `PhiP <= 10` degrees. Since `PhiP = Slpe1 - Incidence`, the branch covers every negative `PhiP` value along with small positive values. The program therefore implements a one-sided post-sum attenuation band tied to its terrain-angle tuple, while the Kouyoumjian-Pathak grazing prescription is applied to the soft or hard coefficient at the exact wedge-face limits before the scalar coefficient is used.

Consequences for reading the code:

- Kouyoumjian-Pathak's straight-wedge half factor applies to the hard coefficient at $\phi'=0$ or $\phi'=n\pi$; the Fortran half factor applies to the final scalar magnitude after the four terms have already been combined.
- Kouyoumjian-Pathak distinguishes soft and hard coefficients; the terrain core uses one scalar coefficient for the horizontal HFTA calculation.
- Kouyoumjian-Pathak's curved-edge treatment checks the relevant $kL$, $kL^i$, and $kL^r$ transition arguments; the Fortran rule uses the signed `PhiP <= 10` degree threshold and a single caller-supplied `L_waves`.

`WD` evaluates the scalar coefficient for `n_wedge >= 0.501`. For smaller `n_wedge`, the tangent/cotangent calculation is bypassed and all four terms are set to zero. In terrain terms, vertices whose `Incl` gives a wedge parameter at or below that cutoff contribute no `WD` diffraction field.

### 4.3 Distance Parameters

For the straight wedge in Kouyoumjian-Pathak Eq. (25), all four transition functions share one distance parameter $L$. With a spherical incident wavefront, source-edge distance $s^i$, edge-observer distance $s^d$, and $\beta_0$ measured to the edge tangent:

$$L=\frac{s^i s^d}{s^i+s^d}\sin^2\beta_0.$$

For a planar incident wavefront:

$$L=s^d\sin^2\beta_0.$$

Kouyoumjian-Pathak's curved-edge expressions assign the transition terms their own distance parameters, chosen so the sum of GO and diffracted fields is continuous at the associated shadow or reflection boundary. $L^i$ uses the incident wavefront curvatures, while $L^{r0}$ and $L^{rn}$ use the wavefront curvatures reflected from the two wedge faces. If the faces are locally planar and the incident wavefront is spherical, these reflected-boundary parameters reduce to the same simple form as the straight-wedge $L$.

In this 2D terrain code, the relevant edge is effectively out of the profile plane, so the scalar implementation uses $\sin\beta_0\approx1$. `WD` receives one value, `L_waves`, uses it for all four transition-function arguments as $kL=2\pi L_{\rm waves}$, and `YUTD` applies the real scalar distance normalization $1/\sqrt{L_{\rm waves}}$. The callers supply path-length proxies in wavelengths: single-edge diffraction uses `AntEdgeDistWaves`, the direct antenna-edge slant distance `DG(M)/cos(LaunchAngle)` divided by wavelength; `DIFFDIFF` converts the stored antenna-edge phase to `E1PhaseLengthFt = DiffPh0/k` for the first coefficient and uses the traced edge-edge length `SlantDist12_ft` for the second coefficient; `DRD` uses `L1_waves = (PhaseToE1Rad/k)/LAMBDA_FT` at edge 1 and `L2Residual_waves = SlantDist_e1e2_ft/LAMBDA_FT - L1_waves` at edge 2. In `DIFFDIFF`, the edge-to-edge `REFL` call contributes the hit test and `SlantDist12_ft`; its returned inter-edge Fresnel amplitude and phase are discarded before the second-edge coefficient is evaluated. Since `DiffPh0` is the stored antenna-edge phase, an element set to `AntPhase=-1` contributes an added $\pi/k=\lambda/2$ to the first-edge length proxy in `DIFFDIFF` and `DRD`; in `DRD` the same added half-wavelength is also subtracted from the second-edge residual distance parameter. In the single-edge case, using the antenna-edge length corresponds to the far-observer limit of the spherical-wave expression, where $s^i s^d/(s^i+s^d)$ tends to $s^i$ as $s^d$ becomes large. The code therefore keeps the straight-wedge, scalar distance bookkeeping and approximates the formal observer-distance and curvature factors through the path family being traced.

### 4.4 Finite-Conductivity Wedges

The UTD formulas above are PEC-wedge formulas. Real terrain is lossy. Luebbers' terrain-propagation work introduced finite-conductivity UTD/GTD wedge corrections by replacing PEC face behavior with terms based on Fresnel reflection coefficients for the wedge faces.

Luebbers-style finite-conductivity UTD modifies the face-related diffraction terms with local Fresnel reflection coefficients and their phases, so lossy terrain changes the reflection-boundary contributions term by term. The Fortran core evaluates soil-loss Fresnel coefficients in reflected ray traces: the main GO sweep applies the phase and preserves the ordinary GO amplitude, while diffraction helper paths multiply by the `ReflAmp` returned from `REFL`. That returned amplitude is segment-local: a clear segment sets it to 1.0, and a reflected final segment sets it to the Fresnel magnitude. Edge diffraction uses the PEC-like scalar `WD`/`YUTD` coefficient for terrain vertices.

Breakall et al. found that PEC and lossy dielectric plate models gave very similar predictions for horizontal dipoles, while lossy dielectric plates were required to match vertical monopole measurements. That is one reason the horizontal-polarization restriction is practical for Yagi, quad, and dipole terrain assessment.

### 4.5 Knife-Edge Mini-Example

A knife-edge clearance parameter is useful as a simple comparison scale for terrain blockage:

$$v=h\sqrt{\frac{2(d_1+d_2)}{\lambda d_1d_2}},$$

where $h$ is the obstacle height above the straight source-receiver line.

For $f=15$ MHz, $\lambda\approx20$ m. Suppose the path is 3 km long with ridges at 1 km and 2 km.

- Edge 1: $d_1=1000$ m, $d_2=2000$ m, $h_1=7.1$ m.
  $$\sqrt{\frac{2(3000)}{20\cdot1000\cdot2000}}\approx0.01225,\qquad v_1\approx0.09.$$
- Edge 2: $d_1=2000$ m, $d_2=1000$ m, $h_2=16.3$ m.
  $$\sqrt{\frac{2(3000)}{20\cdot2000\cdot1000}}\approx0.01225,\qquad v_2\approx0.20.$$

Single-edge curves give about 6 dB excess loss at $v=0$ and roughly 7-8 dB for $v=0.1$ to $0.2$. Cascading two such edges suggests about 14 dB as an order-of-magnitude estimate, but an actual UTD calculation tracks phase, terrain wedge angles, transition functions, and coherent interference with direct and reflected fields.

---

## 5. Terrain Modeling

The Breakall et al. validation study approximated the Cedar Valley terrain by seven connected flat plates:

- Plate lengths followed the terrain profile but were no shorter than one wavelength at the lowest frequency of interest.
- Plates were 60 km wide to suppress side-edge diffraction.
- Plate thickness was greater than one skin depth.
- Both PEC and thin lossy dielectric plates were tested.

The skin-depth formula used there was

$$\delta =
\frac{1}{\omega\sqrt{
\frac{\mu_r\mu_0\varepsilon_r'\varepsilon_0}{2}
\left(\sqrt{1+\left(\frac{\sigma}{\omega\varepsilon_r'\varepsilon_0}\right)^2}-1\right)
}},$$

with $\mu_r\approx1$ for soil.

OpenHFTA's Fortran core uses a different terrain approximation from the seven-plate MoM/GTD research model. The Python layer reads the terrain profile and converts units; the Fortran routine receives feet-valued arrays, builds the program's `Smoothed points` working profile using a $\lambda/8$ vertical threshold, identifies diffraction points from slope changes, and traces rays over the resulting piecewise-linear polyline.

The `Smoothed points` pass initializes the working profile with input points 1 and 2. It then tests `DG(LastPointIdx)` in the partly initialized working array; for ordinary profiles with more than two input points this enters the branch that appends a flat far point at 100000 ft using the previous height. The pass then scans the remaining raw points and keeps a point when its height differs from the last kept working point by at least $\lambda/8$, before appending the final working far point. Diffraction-point selection then uses adjacent segment angles and the following segment length. As implemented, those adjacent segment angles are degree-valued, while the slope-change threshold is the numeric expression `DEG2RAD*0.5`, about `0.0087` degree in the same units used by `ASlp1` and `ASlp2`. The following segment must also exceed $\lambda/100$, and the additional guard accepts the point if it is within 9999 ft, has a following segment no longer than 20 wavelengths, or has a nonzero adjacent segment angle.

---

## 6. Algorithmic Field Synthesis

For each run, the core roughly does the following:

1. Receive terrain and antenna heights in feet from the caller.
2. Compute $\lambda$ and $k$ from frequency.
3. Build the `Smoothed points` working profile from the first two points, any later point whose height differs from the last kept point by at least $\lambda/8$, and the final working far point, normally the synthetic 100000 ft point.
4. Determine active antenna elements, up to four.
5. Apply an element-pattern scale based on the selected antenna type.
6. If diffraction is enabled, find slope-change diffraction points and evaluate direct-to-edge single-edge UTD paths.
7. Call `DIFFDIFF` for two-edge paths. Its first-edge coefficient feeds the cascade without an intermediate cutoff; the edge-to-edge `REFL` call supplies acceptance and slant distance; the second-edge coefficient is compared with the `0.1` cutoff before an outgoing contribution is accumulated.
8. Sweep launch angles from -55 degrees to +35 degrees in 0.25-degree steps, tracing direct and reflected GO paths; during this sweep, reflected rays that encounter marked diffraction points can create reflection-diffraction paths.
9. Accumulate complex field contributions into angle bins.
10. Sum GO and diffracted accumulators.
11. Smooth magnitudes and convert the smoothed values to dB.

The conceptual coherent sum is

$$E_{\rm total}(\theta)=\sum_m A_m(\theta)e^{j\phi_m(\theta)},$$

where each term includes the element pattern, selected element phase, path phase, and any reflection or diffraction coefficient.

In this code, the antenna element model is simple:

$$G_i(\theta)\propto \cos\left(\theta_{\rm rad}\frac{60}{BW}\right),$$

where `BW` is the degree-valued beamwidth setting for the selected antenna type. The result is multiplied by a type-dependent gain factor and by $1/\sqrt{N}$ for an $N$-element stack. Element phasing has two states: `AntPhase=1` adds no extra phase, and `AntPhase=-1` adds $\pi$ radians.

The final post-processing is important. The core first computes magnitudes

$$M[q]=|E_{\rm goAccum}[q]+E_{\rm diffAccum}[q]|,$$

Before storing `M[q]`, bins `1:180` whose complex-field magnitude is at or below $10^{-4}$ are replaced by $10^{-4}+j10^{-4}$. This gives the later smoothing window a finite numerical floor.

It then discards phase for display smoothing and applies a moving average to scalar magnitudes:

$$P_{\rm dB}[q-1]=20\log_{10}\left(\frac{1}{5}\sum_{m=-2}^{2}M[q+m]\right)$$

for interior bins. The code also computes a three-bin average for the second output bin, but explicit assignments then force the first two output bins to -30 dB. Output indices `0:139` represent 0.25 to 35.0 degrees. The working arrays extend beyond the published output range, so the highest output bins can average internal bins above 35 degrees.

---

## 7. Modeling Choices and Limitations

- Horizontal polarization: the executable field model uses horizontal/TE ground reflection and the scalar diffraction coefficient appropriate to HFTA's horizontal-antenna workflow. Vertical-monopole results in Breakall et al. are comparison data for finite-conductivity effects.
- 2D terrain: the profile is one azimuthal cut. The model captures elevation-plane blockage, reflection, and edge diffraction along that cut; 3D focusing, lateral ridges, and off-azimuth scattering require a different geometry.
- Surface wave: the calculation targets skywave far-field takeoff patterns. Ground-wave field strength is handled by separate HF propagation models.
- Diffraction order: the GUI-accessible flow includes single-edge diffraction, reflection-diffraction interaction paths in the main ray trace, and two-edge `DIFFDIFF`.
- DRD execution status: `YTWCore1` initializes `ProcessFlag = 1`; the call condition is `ProcessFlag == 0`, so HFTA GUI runs do not execute `DRD`. The path-filter line in `DRD` contains a WARNING-marked out-of-bounds array access before the ray/UTD model is evaluated for the candidate pair.
- DRD path calculation: when the routine is entered with `ProcessFlag == 0`, an accepted path is evaluated as first-edge UTD, reflected middle-leg `REFL` search, second-edge UTD, and final `REFL` trace. The middle reflected leg supplies traced geometry and slant distance; the final `REFL` call supplies the amplitude and phase used in the accumulated phasor `CMPLX(SIN(ReflPhase), COS(ReflPhase))`.
- Finite-conductivity diffraction: soil loss enters ray tracing through horizontal Fresnel phase updates, and through `ReflAmp` in helper paths that multiply the returned amplitude. Edge diffraction uses the PEC-like scalar `WD`/`YUTD` terms.
- High-frequency assumption: UTD is asymptotic. Electrically small terrain features, dense closely spaced edges, grazing cases, and low-frequency/low-height situations can create artifacts.
- Earth curvature: `EARTH_RADIUS_FT` is defined in the common block, while the active ray equations use straight segment geometry.
- Angle sweep: Dean Straw's terrain-assessment material describes HFTA as shooting rays from +45 to -45 degrees in 0.25-degree steps. This Fortran core uses -55 to +35 degrees for the main internal GO launch sweep and returns 0.25 to 35.0 degrees.
- Diffraction cutoff: `UTD_MAG_THRESHOLD = 0.1` is a field-amplitude cutoff used before accumulating diffracted components. Single-edge and reflection-diffraction paths compare the current `YUTD` coefficient to the cutoff before tracing the outgoing ray. `DIFFDIFF` and `DRD` let the first-edge coefficient feed the cascade, compare the second-edge coefficient to the cutoff, and then apply the ordinary output-angle gates. The DRD branch also requires the final post-reflection `AmpAtE2` to exceed the cutoff and uses a 0 to 30 degree accumulation range when entered.
- Diffraction aliasing: Dean Straw's terrain-assessment material warns about spurious low-frequency, low-height, steep-upslope gain spikes from diffraction aliasing. Those cases are exactly where densely selected diffraction points and transition-function cancellation deserve extra scrutiny.
- Numerical sensitivity: `WD` and `FFCT` are delicate near transition boundaries because cotangent terms and transition functions must cancel correctly.

---

## 8. Validation Context

Breakall, Young, Hagn, Adler, Faust, and Werner measured and modeled HF antennas in Cedar Valley, Utah. Their study used helicopter-borne beacon measurements and a MoM/GTD model of the terrain as connected plates. Key results:

- Measurements were at about 8, 15, and 27 MHz.
- The test hill was about 45 m above surrounding terrain.
- Terrain placement changed low-angle gain by up to about 20 dB, especially near 3-5 degrees.
- Diffraction and blockage were strongest at the higher frequency because the terrain was electrically larger.
- Horizontal dipoles were predicted similarly by PEC and lossy dielectric plates.
- Vertical monopoles required lossy dielectric plates for good agreement.

This supports the physical class of GO/GTD/UTD terrain modeling for HF skywave elevation patterns. The HFTA/N6BV connection is supplied by later HFTA and terrain-assessment material: the Contest University material identifies Dean Straw, N6BV, as creator of HFTA and describes HFTA as computing irregular-terrain effects mainly for built-in Yagi and Yagi-stack models. For exact program behavior, the authority is the HFTA documentation together with this Fortran core.

One important comparison point is diffraction order. The Breakall et al. paper states that first-order edge diffraction was used in that study. HFTA's ray-tracing description includes reflections and diffractions over terrain, and this Fortran core executes the GUI-accessible `DIFFDIFF` pass for two-edge paths. The paper is therefore best read as the measurement-backed source for the physical approach that HFTA adapted for amateur terrain assessment, while compatibility with HFTA itself remains the behavioral target for this code.

---

## 9. Worked Conceptual Example

Consider a horizontal dipole above terrain with a ridge in the profile direction. For one output elevation angle:

1. Trace the direct ray. When terrain clearance holds, add the direct complex field.
2. If the ray intersects a terrain segment, compute the specular reflection angle from the local slope, evaluate horizontal Fresnel $\Gamma_h$, and add the reflected complex field.
3. If a ridge forms a shadow boundary, evaluate a UTD edge contribution using the local wedge geometry and transition function.
4. Repeat for active antenna elements and any accepted two-edge paths.
5. Coherently sum complex bins, convert each bin to magnitude, smooth those scalar magnitudes, and convert the smoothed result to dB.

---

## 10. Mapping to the Fortran Code

- `src/YTWCore1.f90`
  - `YTWCore1`: main driver. It initializes constants, processes terrain, counts antenna elements, detects diffraction points, traces direct/reflected rays, calls diffraction helpers, and produces `Pattern_dB`.
  - `REFL`: ray-traces a path over terrain segments and calls `FRESNEL` when the ray reflects.
  - Final synthesis: combines `E_goAccum` and `E_diffAccum`, applies the small complex-field floor, converts to magnitudes, applies smoothing, and writes the 140 output bins.

- `src/OtherProgs.f90`
  - `FRESNEL`: horizontal lossy-ground reflection coefficient using `ABS` of the angle supplied by the ray tracer; for reflected tilted segments that supplied angle is the outgoing ray elevation after the specular slope calculation.
  - `YUTD`: scalar UTD coefficient wrapper. It receives `PhiP`, `Incl`, and `PHR`, computes `n = 2 - Incl/pi`, calls `WD`, combines the four terms, applies the real distance normalization $1/\sqrt{L_{\rm waves}}$, halves the magnitude for signed `PhiP <= 10` degrees, and returns magnitude/phase.
  - `WD`: computes the four UTD cotangent/transition-function terms using the angular combinations `PHR - PhiP` and `PHR + PhiP`.
  - `FFCT`: transition-function approximation using `ABS(X)` with conjugate symmetry for negative `X`.
  - `DIFFDIFF`: active two-edge diffraction path helper. It first uses `REFL` to test the edge-to-edge trace, records accepted edge pairs in `EdgePairUsed`, converts the stored antenna-edge phase to the first `L_waves`, uses the traced edge-edge length for the second `L_waves`, and then traces the final outgoing ray. The preliminary edge-to-edge `REFL` amplitude and phase are discarded; only its hit result and slant distance feed the cascade. The first `L_waves` therefore includes the element's $\pi$ phase shift when `AntPhase=-1`.
  - `DRD` entry and pair filter: `YTWCore1` initializes `ProcessFlag = 1`; the call condition is `ProcessFlag == 0`, so HFTA GUI runs do not execute this path. When called, `DRD` uses `EdgePairUsed` from the two-edge analysis as an input to its pair filter; that filter contains the WARNING-marked out-of-bounds array access.
  - `DRD` path calculation: after a pair passes the filter, the routine searches a diffraction-reflection-diffraction path family. The middle `REFL` search supplies edge-to-edge geometry and slant distance; the second `YUTD` call uses `L2Residual_waves = SlantDist_e1e2_ft/LAMBDA_FT - L1_waves`, so the phase-derived first-edge length also changes the second-edge distance parameter. The final `REFL` call supplies the amplitude and phase, and the accepted contribution is accumulated with `CMPLX(SIN(ReflPhase), COS(ReflPhase))`.
  - `ANGIN`: computes the local angular parameters used by `YUTD`; in particular `PhiP = Slpe1 - Incidence`, and `Incl` is the value used to derive the wedge parameter. In `DIFFDIFF` and `DRD`, the local variable named `AInclA` carries this `Incl` argument.
  - `ATN4`, `ANGHORIZ`: geometry and angle-convention helpers. `ATN4` behaves as the program's quadrant-aware arctangent helper; `ANGHORIZ` maps the local post-diffraction scan angle back to the absolute ray angle used by `REFL`.

Code conventions:

- Intermediate angle arrays include extra bins such as `-220:180`; the main launch sweep is -55 to +35 degrees.
- Output has 140 bins from 0.25 to 35.0 degrees.
- Terrain and antenna heights are already in feet at the Fortran boundary.
- Soil conductivity is passed through the Python interface in S/m.

---

## 11. Glossary: HFTA-Style Inputs

- Terrain profile (`.PRO`): distance/elevation samples along one azimuth. The Python interface accepts metric or imperial profile files and converts to feet for the core.
- Soil parameters: real relative permittivity $\varepsilon_r'$ and conductivity $\sigma$. The original HFTA GUI displayed common soil values; this CLI expects S/m.
- Antenna description: one of the built-in pattern types (dipole, 2-element Yagi, etc.), up to four heights, and optional 180-degree element phase inversion.
- Angle-of-arrival statistics: optional probability histograms used for figure-of-merit calculations after the electromagnetic pattern has been computed.
- Figure of merit: the Python layer samples the 0.25-degree pattern at integer degrees from 1 to 35, weights linear power by the angle-of-arrival probabilities, and converts the weighted sum back to dB.
- Output: relative elevation pattern in dB, optionally plotted with terrain or angle-of-arrival data.

---

## References

- Breakall, J. K., Young, J. S., Hagn, G. H., Adler, R. W., Faust, D. L., & Werner, D. H. (1994). The Modeling and Measurement of HF Antenna Skywave Radiation Patterns in Irregular Terrain. IEEE Transactions on Antennas and Propagation, 42(7), 936-945.
- Breakall, J. K. Maximizing Performance of HF Antennas with Irregular Terrain. Contest University presentation material.
- Keller, J. B. (1962). Geometrical Theory of Diffraction. Journal of the Optical Society of America, 52(2), 116-130.
- Kouyoumjian, R. G., & Pathak, P. H. (1974). A Uniform Geometrical Theory of Diffraction for an Edge in a Perfectly Conducting Surface. Proceedings of the IEEE, 62(11), 1448-1461.
- Luebbers, R. J. (1984). Finite conductivity uniform GTD versus knife edge diffraction in prediction of propagation path loss. IEEE Transactions on Antennas and Propagation, AP-32(1), 70-76.
- Luebbers, R. J. (1984). Propagation prediction for hilly terrain using GTD wedge diffraction. IEEE Transactions on Antennas and Propagation, AP-32(9), 951-955.
- Whitteker, J. H. (1993). A series solution for diffraction over terrain modeled as multiple bridged knife edges. Radio Science, 28(4), 487-500.
- Wait, J. R. (1968). Diffraction and scattering of the electromagnetic ground-wave by terrain features. Radio Science, 3(10), 995-1003.
- Balanis, C. A. (1989). Advanced Engineering Electromagnetics. Wiley.
- Straw, D. (N6BV). HFTA Operating Instructions. ARRL Antenna Book supplemental resources. https://arrl.org/files/file/Product%20Notes/Antenna%20Book/hfta.pdf
- Straw, D. (N6BV). What I've Learned in Two Decades of Terrain Assessment by N6BV. World Wide Radio Operators Foundation webinar, April 26, 2013. https://youtu.be/D6nRpeVseSc
- Ellingson, S. (2016). Uniform Geometrical Theory of Diffraction. Video lecture. https://youtu.be/s5hNIOrr3G0

---

## Appendix A: Guided Derivation Path

This appendix gives a student-facing route from elementary wave ideas to the UTD coefficient used by the code. The goal is to make each symbol in the main text feel motivated before the reader opens Kouyoumjian and Pathak.

### A.1 From a Wave to a Pattern Bin

For one monochromatic field component,

$$E(t)=\Re\{\tilde E e^{j\omega t}\},$$

where the complex phasor $\tilde E$ stores magnitude and phase. A path of length $s$ changes phase by $ks$, with $k=2\pi/\lambda$. The UTD references commonly write propagation as $e^{-jks}$; the main GO, single-edge, reflection-diffraction, and `DIFFDIFF` paths form complex sums with `COS(phase)` and `SIN(phase)`, while the gated `DRD` branch uses `CMPLX(SIN(phase), COS(phase))` as described in Sections 7 and 10. The important invariant is relative phase: two paths whose lengths differ by $\lambda/2$ arrive 180 degrees apart and tend to cancel.

For one output elevation bin, the code is conceptually summing terms of the form

$$\tilde E_m = A_m C_m e^{j\phi_m},$$

where $A_m$ contains antenna pattern and scalar path amplitude, $C_m$ contains any reflection or diffraction coefficient, and $\phi_m$ contains path length, element phase, reflection phase, diffraction phase, and final height correction. Only after all phasors for the bin are added does the code take magnitude and convert to dB:

$$P_{\rm dB}=20\log_{10}\left|\sum_m \tilde E_m\right|.$$

This is why a terrain feature can increase or decrease gain at a given takeoff angle: it changes both amplitude and phase of the paths that land in that bin.

### A.2 Reflection From a Local Terrain Segment

The ray-reflection law follows from Fermat's principle. If a straight terrain segment is treated as a local mirror, the reflected path from source to field point is stationary when the incident and outgoing angles are equal with respect to the segment normal. In slope-angle form this gives the code's update

$$\alpha_{\rm out}=2\alpha_{\rm seg}-\alpha_{\rm in}.$$

The reflection coefficient then comes from applying electromagnetic boundary conditions at a planar interface. For horizontal/TE polarization, tangential $E$ and $H$ continuity at an air-to-lossy-ground boundary gives

$$\Gamma_h(\theta_i)=
\frac{\cos\theta_i-\sqrt{\varepsilon_c-\sin^2\theta_i}}
     {\cos\theta_i+\sqrt{\varepsilon_c-\sin^2\theta_i}},
$$

where $\theta_i$ is measured from the surface normal and

$$\varepsilon_c=\varepsilon_r'-j\frac{\sigma}{\omega\varepsilon_0}.$$

Using the surface grazing angle $\gamma=\pi/2-\theta_i$ changes $\cos\theta_i$ to $\sin\gamma$ and $\sin^2\theta_i$ to $\cos^2\gamma$, producing the form implemented by `FRESNEL`:

$$\Gamma_h(\gamma)=
\frac{\sin\gamma-\sqrt{\varepsilon_c-\cos^2\gamma}}
     {\sin\gamma+\sqrt{\varepsilon_c-\cos^2\gamma}}.$$

For a flat segment, the ray elevation and the surface grazing angle are the same quantity. For a tilted segment, the ray tracer computes the reflected direction from the segment slope and passes that outgoing elevation angle to `FRESNEL`, which uses its absolute value. The local surface grazing angle would subtract the segment slope first, so the code's ground coefficient follows horizontal-ground Fresnel algebra after the tilted-segment ray direction has been chosen.

### A.3 Knife-Edge Diffraction as the First Mental Model

A knife edge explains the main physical need for diffraction. GO says that a ray either clears the obstacle or enters shadow, causing an abrupt field change. Wave optics replaces that jump with a transition governed by Fresnel-zone geometry.

For a single edge between source and receiver, define the clearance parameter

$$v=h\sqrt{\frac{2(d_1+d_2)}{\lambda d_1d_2}},$$

where $h$ is obstacle height above the straight source-receiver line and $d_1,d_2$ are the source-edge and edge-receiver distances. In one common normalized representation, the field behind the edge is written with a Fresnel integral over a lower limit set by $v$:

$$\frac{E}{E_0}=\frac{1+j}{2}\int_v^\infty e^{-j\pi t^2/2}\,dt.$$

The formula says that the edge contribution depends on how many Fresnel zones are blocked. Near $v=0$, the obstruction clips the wavefront near the line of sight and produces the familiar roughly 6 dB transition value. As $v$ grows positive, more of the wavefront is blocked and the field falls. This knife-edge model is simpler than terrain UTD, but it gives the right intuition: the shadow boundary is a finite transition region, and phase matters.

### A.4 From GTD to UTD

Keller's GTD replaces a real obstacle near a point by a canonical local object, such as a perfectly conducting wedge. The diffracted field is written as the incident field at the edge times a local diffraction coefficient times a spreading and phase factor:

$$\tilde E_d \sim \tilde E_i(Q_E)\,D(\phi^d,\phi^i,n)\,S(s^d)\,e^{-jks^d}.$$

For a straight wedge, the scalar GTD coefficient contains denominators that become singular at shadow and reflection boundaries. The singularity is a signal that the local asymptotic expression and the discontinuous GO field have to be combined uniformly in that boundary region.

Kouyoumjian-Pathak UTD keeps the same local wedge idea but replaces each singular boundary term by

$$\cot(\cdots)\,F(kLa^\pm),$$

where:

- the cotangent term carries the ordinary wedge angular dependence;
- $a^\pm$ measures squared angular distance from the nearest relevant boundary;
- $L$ is the distance parameter that sets the physical width of the transition region;
- $F$ is the transition function.

The cancellation mechanism is the key idea. Let $\epsilon$ be a small angular distance from a boundary. The cotangent behaves like $1/\epsilon$. At the same boundary, $a^\pm$ behaves like a constant times $\epsilon^2$, so $X=kLa^\pm$ is also proportional to $\epsilon^2$. Since $F(X)$ behaves like a constant times $\sqrt{X}$ for small $X$, it contributes a factor proportional to $|\epsilon|$. The product $\cot(\cdots)F(kLa^\pm)$ stays finite.

Far from the boundary, $kLa^\pm$ is large and $F(kLa^\pm)\to1$, so the UTD coefficient reduces back toward the ordinary GTD coefficient. The single parameter $L$ therefore controls how quickly the transition function moves from boundary smoothing to ordinary GTD behavior. Large $kL$ gives a narrow transition; small $kL$ gives a broad transition and more numerical sensitivity.

### A.5 How the Fortran Specializes Kouyoumjian-Pathak

The full UTD expression is vector/dyadic and distinguishes soft and hard coefficients, incident and reflected boundary distance parameters, and the exact wedge-face grazing cases. The HFTA-style Fortran core specializes that machinery for a 2D horizontal-polarization terrain pattern:

- The terrain edge is treated as perpendicular to the profile plane, so the scalar code uses $\sin\beta_0\approx1$.
- `ANGIN` maps local terrain slopes and incident angle into the tuple `Incl`, `PhiP`, and `PHR`.
- `YUTD` computes `n_wedge = 2 - Incl/pi`.
- `WD` evaluates four cotangent-transition terms, two using `PHR - PhiP` and two using `PHR + PhiP`.
- Every `WD` call receives one `L_waves` value shared by all four transition-function arguments.
- `FFCT` approximates the UTD transition function in three ranges: small, table-driven middle, and large-argument asymptotic.
- `YUTD` combines the four terms as `(term1 + term2) - (term3 + term4)`, applies the real scalar distance normalization $1/\sqrt{L_{\rm waves}}$, extracts magnitude and phase, and halves the final magnitude when signed `PhiP <= 10` degrees.

The path-family routines decide what `L_waves` means for a given ray family. Single-edge diffraction uses antenna-edge slant length. `DIFFDIFF` uses the stored antenna-edge phase converted back to length for edge 1 and the traced edge-edge length for edge 2. `DRD`, when entered with `ProcessFlag == 0`, uses the same first-edge phase length and then subtracts that value from the traced edge-edge length before evaluating the second coefficient. Thus a 180-degree element phase changes both the first `DRD` distance parameter and the second residual parameter. These definitions are how the straight-wedge scalar coefficient is fitted to the terrain ray families used by HFTA.

### A.6 Where the Original Paper Fits

After this bridge, Kouyoumjian and Pathak's paper is the right source for the rigorous derivation of the UTD coefficient, especially:

- why the four cotangent terms have their exact signs and angular arguments;
- how the $N^\pm$ boundary-selection integers are chosen;
- how the straight-wedge distance parameter $L$ is obtained from wavefront curvature;
- how curved screens and curved wedges introduce $L^i$, $L^{r0}$, and $L^{rn}$;
- how grazing incidence is handled in the exact soft/hard coefficient framework.

For reading this Fortran core, the most important result from that derivation is the structure of a finite boundary transition: each GTD angular singularity is paired with a transition function argument $kLa^\pm$, and the code's `WD`/`FFCT`/`YUTD` stack is the scalar implementation of that structure.

---

## Appendix B: Symbols

- $\lambda$: wavelength; $k$: wavenumber; $\omega$: radian frequency.
- $\varepsilon_0,\mu_0$: free-space permittivity and permeability.
- $\varepsilon_r'$: real relative permittivity of soil; $\varepsilon_c$: complex relative permittivity; $\sigma$: conductivity.
- $\theta$: elevation angle; $\theta_i$: incidence angle from surface normal; $\gamma$: grazing angle from surface.
- $\phi^i,\phi^d$: wedge incidence/diffraction angles; $\beta_0$: angle to edge tangent.
- $\Gamma_h,\Gamma_v$: horizontal/TE and vertical/TM Fresnel reflection coefficients.
- $D_s,D_h$: soft and hard GTD/UTD diffraction coefficients.
- $F$: UTD transition function.
- $L,L^i,L^{r0},L^{rn}$: UTD distance parameters.
- $s^i,s^d$: source-edge and edge-observer distances.
