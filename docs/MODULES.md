# NITK-UsoundSim — Module Documentation

One section per pipeline module, in pipeline order, each with the eight items the
plan's Definition of Done requires: (1) explanation, (2) inputs, (3) outputs,
(4) equations actually used, (5) algorithm, (6) assumptions, (7) limitations,
(8) test result. Every number below comes from running the code; the command that
produces it is given with each test result. Units are SI (m, s, Hz) unless stated.

**Probe: Philips L12-4 (FUS4103) reference model** — 128 elements and a 4–12 MHz range
(published by Philips); 0.30 mm pitch and 8 MHz centre frequency (not published — T2's
documented assumptions, `teams/T2_TX_Beamforming/Usound/config/transducer_interface.json`).
The project was first built with T3's 64-element / 5 MHz / λ/2 array; `docs/README.md`
keeps that history.

Code layout: `simulator/` holds the integration (`config.py`, `main.py`); each team's folder in `teams/` (`T1_Transducer` … `T7_Image_Recon_Post_Processing`) holds the team's original code plus the pipeline-stage module written for it during integration (T4 `tissue_phantoms.py`, T5 `receive_beamforming.py` + `mock_data.py`, T6 `bmode_formation.py`, T7 `post_processing.py`); `parameter_tests.py` is in `tests/`. Run everything from the project root:

```bash
python3 simulator/main.py
```

```bash
PYTHONPATH=simulator python3 teams/T5_RX_Beamforming/verify_beamformer.py
```

```bash
python3 tests/parameter_tests.py
```

Pipeline: `config` → transducer geometry → (TX beamforming: broadcast) → acoustic
propagation ⇄ tissue interaction (with element directivity) → receive DAS (dynamic
aperture) → B-mode formation → scan conversion + post-processing → final image.
See README Sections 2 and 5 for why it differs from the plan.

---

## 1. Configuration — `simulator/config.py` (integration)

1. **Explanation.** Single source of truth. Imports T3's medium and display constants
   (`nitk_usoundsim/config.py`) instead of copying them, and defines the probe (Philips
   L12-4), which overrides T3's 64-element / 5 MHz defaults. T3's code is not modified:
   its functions receive `f0 = config.F0` explicitly.
2. **Inputs.** None (module constants).
3. **Outputs.** From T3: `C` = 1540 m/s, `FS` = 40 MHz, `ALPHA_0` = 0.5 dB/MHz/cm,
   `Z_MIN/Z_MAX` = 0–40 mm (displayed depth), `DYNAMIC_RANGE_DB` = 50, `OUTPUT_SIZE` =
   (512, 512). Probe: `PROBE_NAME`, `N_ELEMENTS` = 128, `PITCH` = 0.30 mm, `F0` = 8 MHz,
   `F_MIN/F_MAX` = 4/12 MHz, `LAMBDA` = 0.1925 mm (pitch = 1.56 λ), `APERTURE` = 38.4 mm.
   Imaging: `SCANLINE_X_MIN/MAX` = ±10 mm, `N_SCANLINES` = 256 (0.078 mm apart);
   `Z_RF_MAX` = 60 mm; `get_t_axis()` (3574 samples from −0.75 µs);
   `get_depth_axis()` (3118 points, dz = c/2fs = 0.019 mm). Transmit: `TX_FOCUS_Z = None`,
   `get_tx_delays()` (zeros, broadcast). Receive: `RX_APODIZATION = "hann"`,
   `RX_F_NUMBER` = 1.0. `ELEMENT_WIDTH` = pitch, `ELEMENT_DIRECTIVITY = True`.
   Phantom: density 1×10⁸ m⁻², x ±12 mm, z 0–40 mm, seed 2026; lesion at (0, 30) mm,
   radius 6 mm, scattering scale 0.0 (anechoic). Also recorded: `ELEMENT_HEIGHT` = None
   (2-D), `BACKGROUND_IMPEDANCE_MRAYL` = 1.63 (T4's default), `DENSITY` = Z/c ≈ 1058 kg/m³.
4. **Equations.** λ = C/F0; dz = C/(2·FS); t_axis from −T_p to 2·d_far/C + T_p, with T_p
   the pulse half-width at F0 (4σ = 0.75 µs) and d_far = √((x_phantom + N·pitch/2)² + Z_RF_MAX²).
5. **Algorithm.** Put T3's package and every team folder on `sys.path`, re-export T3's
   medium constants, define the probe, axes and wrappers.
6. **Assumptions.** t = 0 is the TX pulse centre (T3 convention). The RF is recorded to
   60 mm because T5's test 4 checks a target at 55 mm; only 0–40 mm is displayed.
   FS stays 40 MHz (5 samples per 8 MHz cycle): positions are exact (time-axis rule);
   linear interpolation lowers all levels by ≈2–3 dB uniformly (Section 11), which the
   per-frame normalisation of the B-mode removes.
7. **Limitations.** Pitch and centre frequency are assumptions (Philips does not publish
   them). The page's "4 mm aperture" cannot be the lateral width (128 elements would need
   a 0.03 mm pitch); it is probably the element height and is not used (2-D model).
8. **Test result.** Used by every module; T5's `verify_beamformer.py` (which imports it
   directly) passes 4/4 with this probe.

## 2. Transducer geometry — T3's `create_linear_array()` (T1 bypassed)

1. **Explanation.** Element x-positions of the 128-element linear array. T1's code
   (`teams/T1_Transducer/`) implements a piezo-material registry, not array geometry,
   so T3's function is used (README Section 4).
2. **Inputs.** `N_ELEMENTS` = 128, `PITCH` = 0.30 mm.
3. **Outputs.** (128,) x-positions [m], centred on 0, all at z = 0.
4. **Equations.** x_n = (n − (N−1)/2)·pitch, n = 0…127 → element centres ±19.05 mm
   (aperture 38.4 mm).
5. **Algorithm.** One `np.arange`.
6. **Assumptions.** Elements of width w = pitch (no kerf); their directivity is modelled
   in the RF simulation (Section 5).
7. **Limitations.** No element height, impulse response or electrical model.
8. **Test result.** Part of T3's suite (22/22 pass).

## 3. Transmit beamforming — T2 (`teams/T2_TX_Beamforming/Usound/`), broadcast in the imaging chain

1. **Explanation.** Per-element TX delays for one fixed focus or a linear steer, plus
   Hann/Hamming/rectangular apodization and a Gaussian pulse. T2 designed its code for
   exactly this probe (128 elements, 0.30 mm, 8 MHz). The imaging chain uses one
   broadcast (zero-delay) transmit, for practical reasons only (README Section 4).
2. **Inputs.** Element positions, focus (x_f, z_f) or steering angle, c.
3. **Outputs.** (128,) TX delays [s] and apodization weights.
4. **Equations.** d_n = √((x_n − x_f)² + z_f²); τ_n = (max_n d_n − d_n)/c.
5. **Algorithm.** Evaluate the delay law once per transmit.
6. **Assumptions.** Single focus, fixed apodization per shot.
7. **Limitations.** Per-line focusing needs one full simulation per line (256 lines x
   ≈4 min). A transmit window (Tukey, Hann) was tested on the broadcast and changed no
   artefact level, so none is applied.
8. **Test result.** T2's own 2 tests pass. Its delays focused at 20 mm raise the incident
   wave at a (0, 20) mm target by **+18.36 dB** over broadcast (Section 11).

## 4. Acoustic propagation — T3 (`nitk_usoundsim/acoustic_propagation.py`), used unmodified

1. **Explanation.** Forward (array → scatterer) and return (scatterer → array)
   propagation of the pressure pulse, in a homogeneous attenuating medium.
2. **Inputs.** Scatterer {x, z}, element x-positions, `t_axis`, TX delays `tau_tx`
   (zeros), `f0` = 8 MHz (passed explicitly), reflected waveform (return path).
3. **Outputs.** `forward_propagation`: incident wave at the scatterer (len(t_axis),).
   `return_propagation`: pressure at every element (128, len(t_axis)).
4. **Equations.**
   p(t) = sin(2π f0 t)·exp(−t²/2σ²), σ = N_cycles/(2 f0), N_cycles = 3;
   d_n = √((x_s − x_n)² + z_s²), t_n = d_n / C;
   A(d) = 10^(−α0·f0[MHz]·d[cm]/20);
   incident(t) = Σ_n A(d_n)·p(t − τ_TX,n − t_n);
   p_RX,m(t) = A(d_m)·reflected(t − t_m) (shift by `np.interp` on `t_axis`).
5. **Algorithm.** Closed-form pulse evaluated at delayed times (forward); linear
   interpolation of the sampled reflected wave (return).
6. **Assumptions.** Straight rays, constant c, linear superposition, no geometric
   spreading (1/r), point elements (directivity is added in Section 5).
7. **Limitations.** No per-element weights; `simulate_acoustic_propagation()` sizes
   `t_axis` from the phantom and hard-wires T3's mock tissue model, so the integration
   calls `forward_propagation` / `return_propagation` directly.
8. **Test result.** 22/22 T3 tests pass (T3's own configuration; its code is unchanged).

## 5. Tissue interaction + RF generation — T4 (`teams/T4_Tissue_Interaction/`: `tissue_interaction.py`, `phantom.py`, + `tissue_phantoms.py`)

1. **Explanation.** T4 scales the incident wave at each scatterer and generates the
   speckle/cyst phantoms; `tissue_phantoms.py` builds the three required phantoms and
   runs the per-scatterer chain, summing the echoes. It also adds **element
   directivity**, which T3's point elements lack.
2. **Inputs.** `build_phantom(kind, seed)`, kind ∈ {point_targets, scatterers,
   cyst_lesion}; `simulate_rf(scatterers, t_axis=None, workers=None)`;
   `incident_wave(s, t_axis, f0, alpha0, tau_tx)`, `point_echo(s, t_axis, …)`.
3. **Outputs.** Scatterer list [{x, z, amp, …}]; `(rf, t_axis)`, rf (128, 3574).
4. **Equations.** Directivity of element n towards scatterer s (rectangular element of
   width w, far field, at f0): D_n = sinc(w·sin θ_n / λ), sinc(u) = sin(πu)/(πu).
   incident = Σ_n D_n · T3forward(element n); reflected = G·incident,
   G = amp·(1 + |R|)·scale, R = (Z2 − Z1)/(Z2 + Z1) (G = amp when no impedances are
   given); echo_m = D_m · T3return(reflected)_m; rf_m(t) = Σ_s echo_m,s(t).
   Phantom: x, z ~ Uniform, amp ~ N(0, σ); inside the lesion amp ×= 0.0.
5. **Algorithm.** For each scatterer: T3 `forward_propagation` per element weighted by
   D_n → T4 `tissue_interaction` → T3 `return_propagation` → × D_m; accumulate. Phantoms
   with ≥ 2000 scatterers are split into interleaved chunks simulated in parallel
   processes (all CPU cores) and the chunk RFs are summed (a serial fallback is used if
   processes cannot start).
6. **Assumptions.** Point targets at (−5, 10), (0, 20), (+5, 30) mm, amp 1. Scatterers:
   96,000 over x ±12 mm, z 0–40 mm (1×10⁸ m⁻²; the speckle is fully developed, Section 10).
   Cyst: same field (same seed), anechoic circle r = 6 mm at (0, 30) mm, 11,169
   scatterers inside.
7. **Limitations.** Directivity uses the single-frequency far-field formula at f0. Without
   it the coarse pitch (1.56 λ) produced late "grating" ghosts only −11 to −13 dB below
   each point target; with it they are −21 to −34 dB. ≈9 ms per scatterer serial; a
   96,000-scatterer frame takes ≈3.6–4.4 min on 8 cores. The parallel sum equals the
   serial sum up to floating-point rounding. `1 + |R|` is sign-less (irrelevant: lesion
   impedance is not set). No scatterers deeper than 40 mm.
8. **Test result.** With directivity switched off `point_echo` is bit-identical to calling
   T3 directly; T3 called per element with unit weights equals T3's all-element sum
   (max difference 0.0). T4's own tests: 13/13 (25 Sep audit; `pytest` is not installed
   on this Mac, T4's code is unchanged).

## 6. Receive beamforming — `teams/T5_RX_Beamforming/receive_beamforming.py` (T5)

1. **Explanation.** Delay-and-sum with dynamic receive focus and a **dynamic receive
   aperture** (F-number) at every depth of every scan line, for one broadcast frame
   reused across lines.
2. **Inputs.** `rf` (128, n_samples) or (128, n_samples, n_lines); element positions;
   scan-line positions; config; `apply_focus`; `t_axis`; `apodization` ("hann" |
   "hamming" | "rect", default `config.RX_APODIZATION`); `f_number` (default
   `config.RX_F_NUMBER` = 1.0; None = fixed full aperture).
3. **Outputs.** `(beamformed (3118, 256), z_axis (3118,))` — RF, not envelope.
4. **Equations.** τ_TX(z) = min_n √((x_l − x_n)² + z²)/C;
   τ_RX,m(z) = √((x_l − x_m)² + z²)/C; active half-aperture a(z) = max(z/(2F#), 2·pitch);
   w_m(z) = cos²(π·|x_m − x_l| / (2a)) for |x_m − x_l| < a (Hann), else 0;
   s_l(z) = Σ_m w_m(z)·rf_m(τ_TX + τ_RX,m) / Σ_m w_m(z).
5. **Algorithm.** Per line and element, sample the channel RF at τ with
   `np.interp(τ, t_axis, rf_m)` on the **real** `t_axis` (time-axis rule, README
   Section 6: never τ·FS as an index — `t_axis` starts at −0.75 µs).
6. **Assumptions.** Straight rays, constant C; the broadcast wavefront first reaches
   (x_l, z) from the nearest element.
7. **Limitations.** F# = 1 limits the receive angle to 26.6°: with the fixed full aperture
   the coarse pitch gave a grating-lobe streak from the shallow target at −17 dB; with
   F# = 1 it is below −100 dB, at the cost of lateral −6 dB width 0.31 → 0.47 mm. The
   aperture edge is hard (softened by the window). A −25 dB diagonal arc remains next to
   the shallow (−5, 10) mm point target; it is not changed by transmit windows and was not
   further root-caused (Section 10).
8. **Test result.** T5's `verify_beamformer.py`, unmodified, with this probe: **4/4 pass** —
   test 1 error 0.008 mm (tol 0.096), test 2 peak 0.327 vs 0.066 unfocused, test 3 peak
   (−3.96, 24.99) mm, test 4 errors 0.034 / 0.040 / 0.036 mm at 15 / 40 / 55 mm.
   `f_number=None` reproduces the earlier fixed-aperture beamformer bit for bit.
   Apodization and sampling-rate behaviour: Section 11.

## 7. B-mode formation — `teams/T6_B_mode/bmode_formation.py` (T6)

1. **Explanation.** Envelope detection + log compression. Same algorithm as T6's
   real-carotid notebook (`teams/T6_B_mode/B_mode_real_carotid_final/B_mode.ipynb`).
2. **Inputs.** `beamformed_rf` (n_depths, n_lines); `dynamic_range_db` (default 50).
3. **Outputs.** B-mode brightness (n_depths, n_lines) = (3118, 256) in [0, 1].
4. **Equations.** E = |s + j·H{s}| (Hilbert along depth);
   L = 20·log10(max(E/max E, 10⁻¹²)); B = (clip(L, −DR, 0) + DR)/DR.
5. **Algorithm.** `scipy.signal.hilbert(axis=0)`, normalise to frame peak, log,
   clip, rescale.
6. **Assumptions.** Input already on the physical depth axis, so no time lookup
   (the time-axis rule does not apply). Relative (per-frame) brightness.
7. **Limitations.** No TGC, band-pass or attenuation correction: at 8 MHz the speckle is
   17 dB darker at 36–40 mm than at 8–12 mm. Unwindowed Hilbert. DR = 50 dB kept (T6
   used 60 dB unsourced; the EPFL source displays these carotids at 40 dB).
8. **Test result.** On T6's real carotid_1 RF at 60 dB it matches T6's saved output
   to 5.1×10⁻⁶ (float32 round-off). Rejects non-2-D input and DR ≤ 0.

## 8. Scan conversion + post-processing — `teams/T7_Image_Recon_Post_Processing/post_processing.py` (T7)

1. **Explanation.** `scan_convert()` resamples the (depth × line) B-mode to display
   pixels — a straight rectangular resample, since linear-array lines are parallel
   (no fan). `postprocess()` despeckles with the guided filter selected in the
   Post-Image Processing notebook `262SP009_Post_Image_Processing_v2.ipynb`.
2. **Inputs.** `scan_convert(bmode, x_axis, z_axis, output_size=OUTPUT_SIZE,
   z_range=(Z_MIN, Z_MAX), keep_aspect=True)`; `postprocess(image, method="guided",
   r=4, eps=0.001, gamma=1.0)`.
3. **Outputs.** `(image, x_out, z_out)`: 512 × 256 px at 0.078 mm/px (square pixels for
   the 40 × 20 mm FOV); `postprocess` → same shape, float [0, 1].
4. **Equations.** Bilinear interpolation on (z, x). Guided filter (self-guided, window
   radius r): a_k = cov_k(I, I)/(var_k(I) + eps), b_k = μ_k − a_k μ_k,
   q = mean_w(a)·I + mean_w(b). Grey-level mapping: out = q^γ (γ = 1 by default).
5. **Algorithm.** Crop depth to 0–40 mm → `RegularGridInterpolator` onto a square-pixel
   grid → quantise to uint8 → notebook's `guided` (unchanged) → float [0, 1] →
   optional gamma.
6. **Assumptions.** Square pixels (`keep_aspect=True`) so the filter window is isotropic
   in mm; `keep_aspect=False` stretches to exactly `OUTPUT_SIZE`. Filter parameters are
   the notebook's (tuned on real breast images), not re-tuned.
7. **Limitations.** With the L12-4 the speckle grain is small (autocorrelation half-width
   0.17 mm axial, 0.21 mm lateral ≈ 2–3 px), so the 9 × 9 filter now acts on it: speckle
   index −8 % on the speckle phantom (0.178 → 0.163) while the cyst edge keeps 96 % of its
   sharpness. Applying the notebook's own tuning rule (best contrast with edge ratio ≥ 0.90)
   to the simulated cyst: eps 0.001 → edge 0.96, gCNR 0.871; **eps 0.002 → edge 0.93, gCNR
   0.881** (also passes); eps 0.005 → 0.86 and eps 0.01 → 0.78 (fail). The notebook's value
   0.001 is kept; 0.002 is an option for the T7 owner to decide.
8. **Test result.** `guided` is bit-identical to the notebook's function (random
   image, eps 0.001 and 0.01); scan conversion reproduces a linear ramp to 3×10⁻¹⁶;
   bad input shapes/methods are rejected. Metrics on the phantoms: Section 10.

## 9. End-to-end driver — `simulator/main.py`

1. **Explanation.** Runs the full chain for each phantom and saves the results.
2. **Inputs.** Phantom kinds (default all three), `--out` folder (default `results/`).
3. **Outputs.** `results/final_bmode.png` (final images of all phantoms),
   `results/<kind>_final_bmode.npy` (final image array, 512 × 256, [0, 1]),
   `results/<kind>.png` (before/after post-processing), `results/<kind>.npz`
   (every intermediate array).
4. **Equations.** None beyond the modules above.
5. **Algorithm.** build_phantom → simulate_rf → das_beamform → bmode_formation →
   scan_convert → postprocess; print checks; plot.
6. **Assumptions.** Run from the project root.
7. **Limitations.** ≈8 min for all three phantoms on this Mac (8 cores); the per-scatterer
   T3 loop dominates.
8. **Test result.** See Section 10.

## 10. Results (`python3 simulator/main.py`)

All three required results, 50 dB, B-mode 3118 × 256 → image 512 × 256 px (0.078 mm/px),
x ±10 mm, z 0–40 mm. simulate_rf ≈215–266 s per 96,000-scatterer phantom; total ≈8 min.

**Point targets** — measured peak (B-mode grid, lines 0.078 mm apart) and level re frame peak:

| Target (x, z) mm | Measured peak (x, z) mm | Level | Axial / lateral −6 dB width |
|---|---|---|---|
| (−5, 10) | (−4.98, 10.01) | 0.00 dB | 0.346 / 0.471 mm |
| (0, 20) | (−0.04, 20.00) | −5.44 dB | 0.327 / 0.471 mm |
| (+5, 30) | (+4.98, 29.99) | −11.50 dB | 0.346 / 0.471 mm |

All within 0.04 mm. Artefacts (re frame peak): a −25.0 dB diagonal arc next to the shallow
(−5, 10) target, and faint copies 2 mm below the targets at −32.1 and −33.9 dB; 2.1 % of
the image outside the targets is above −40 dB.

**Scatterers (speckle)** — 96,000 scatterers. Envelope SNR (mean/std) 1.73–1.92 from 6 to
38 mm (fully developed speckle: 1.91). Speckle grain: autocorrelation half-width 0.174 mm
axial, 0.213 mm lateral. Brightness across the image uniform within 0.2 dB; with depth
−4.4 / −9.4 / −14.2 / −17.2 dB at 16–20 / 24–28 / 32–36 / 36–40 mm (re 8–12 mm; 8 MHz
attenuation, no TGC). Speckle index (notebook's 7 × 7 SI): 0.178 → 0.163 after the filter.

**Cyst** — anechoic, r = 6 mm at (0, 30) mm, lesion vs a 10 px (0.78 mm) ring around it:

| | Lesion − ring (displayed) | CNR | gCNR | Edge sharpness | SI |
|---|---|---|---|---|---|
| Before post-processing | −19.40 dB | 2.323 | 0.860 | 145.7 | 0.308 |
| After guided filter | −19.32 dB | 2.425 | 0.871 | 140.5 (ratio 0.96) | 0.241 |

Echo power inside r ≤ 5 mm: −22.4 dB vs the same region with no lesion, −28.2 dB vs the
tissue just above it (19–23 mm).

**Compared with the first (64-element, 5 MHz) build:** lateral −6 dB width ≈1.3 → 0.47 mm,
axial 0.50 → 0.33 mm, image width ±5 → ±10 mm with uniform brightness (was 14–20 dB darker
outside the aperture), cyst gCNR 0.63 (r = 3 mm) → 0.86 (r = 6 mm).

## 11. Parameter tests (`python3 tests/parameter_tests.py`, plan 24 Sep)

One point target per case, same physics as `main.py` (`tissue_phantoms.point_echo`,
`das_beamform`), only the tested parameter changed. **9/9 checks pass**; figure
`results/parameter_tests.png`.

| Parameter | Values | Measured | Prediction / expected behaviour |
|---|---|---|---|
| Centre frequency, target (0, 20) mm, fs 128 MHz | 4 / 8 / 12 MHz | axial −6 dB width 0.674 / 0.327 / 0.212 mm; lateral 0.820 / 0.460 / 0.340 mm | axial (C/2)·2.355·σ = 0.680 / 0.340 / 0.227 mm (within 10 %); lateral ∝ λ·F# |
| Attenuation, targets at 10 and 30 mm | α0 = 0 / 0.5 / 1.0 dB/MHz/cm | extra loss −16.11 / −32.21 dB vs α0 = 0 | −2·α0·f0·2 cm = −16.00 / −32.00 dB |
| TX focus (T2's delays), target (0, 20) mm | broadcast / 10 / 20 / 30 mm | incident peak 0.00 / +0.00 / **+18.36** / +4.78 dB re broadcast | strongest when focused at the target depth |
| RX apodization, target (0, 20) mm | rect / Hamming / Hann | lateral width 0.300 / 0.420 / 0.460 mm; highest sidelobe −18.2 / −33.3 / −32.7 dB | rect narrowest main lobe and highest sidelobes |
| Sampling rate, target (+2, 25) mm | 32 / 64 / 128 MHz (4 / 8 / 16 samples per cycle) | peak depth 24.987 / 25.006 / 25.006 mm (within one depth sample); level +0.00 / +2.79 / +3.39 dB | position unchanged (time-axis rule); level converges as fs rises |

Two first versions of these checks **failed** and were corrected only after the cause was
measured: (1) sampling — a constant level was expected, but linear interpolation
(`np.interp`, used twice: T3's return path and the DAS lookup) is a low-pass filter, so at
4 samples per cycle the level is ≈2.8 dB lower; the check now tests convergence.
(2) frequency — run at fs = 40 MHz with the fixed full aperture, the 12 MHz axial width was
+10 % (under-sampling: 3.3 samples per cycle; −7 % at 128 MHz) and the lateral width stayed
0.30 mm at 8 and 12 MHz (element directivity, not the array, limited the aperture); the test
now runs at 128 MHz, and with the F# = 1 aperture the lateral width scales with λ.
