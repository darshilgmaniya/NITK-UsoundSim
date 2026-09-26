# NITK-UsoundSim — Project README

**A modular, physics-based 2D ultrasound simulation pipeline using a 128-element linear array
(Philips L12-4 reference model, 8 MHz).** The project was first built with a 64-element, 5 MHz
array; see "Probe update" below.
Not a clinically accurate scanner — the goal is a reproducible, physically-interpretable
simulator: phantom in, B-mode image out.

- **Team:** 8 sub-teams, 15 members
- **Project period:** 15–26 September 2026
- **Final deadline:** 26 September 2026 (final demo/submission)
- **This document's purpose:** ground truth on what each team actually delivered
  (not what the plan assumed), the pipeline architecture, and the known
  integration issues — written so anyone can pick this project up with
  full context instead of guessing from the plan doc alone.

**Status (26 Sep): complete pipeline built and verified, now with the Philips L12-4 probe.** From the project root:

| Command | What it does | Time |
|---|---|---|
| `python3 simulator/main.py` | Full chain for all 3 phantoms → `results/final_bmode.png`, `results/<kind>_final_bmode.npy`, `results/<kind>.png`, `results/<kind>.npz` | ≈8 min (8 cores) |
| `python3 tests/parameter_tests.py` | Plan's 24-Sep parameter tests (frequency, focus, attenuation, apodization, fs) → 9/9 pass, `results/parameter_tests.png` | ≈50 s |
| `PYTHONPATH=simulator python3 teams/T5_RX_Beamforming/verify_beamformer.py` | T5's own tests → 4/4 pass | ≈9 s |

Per-module documentation (plan's 8 items per module + results): **`docs/MODULES.md`**. Stage-by-stage notebook: **`demo.ipynb`**.

## Probe update (26 Sep): Philips L12-4

The simulator now models the **Philips L12-4 (FUS4103)** linear array. Philips publishes
**128 elements** and a **4–12 MHz** range; pitch and centre frequency are not published, so
T2's documented assumptions are used: **0.30 mm pitch, 8 MHz** (aperture 38.4 mm). Everything
in the sections further below that says 64 elements, 5 MHz, λ/2 pitch, ±5 mm image, 3 mm cyst,
16,000 scatterers or 512 × 128 px describes the **first build** and is kept as history.

What changed (5 files; teammates' original code untouched):

| File | Change | Why (measured) |
|---|---|---|
| `simulator/config.py` | 128 el., 0.30 mm, 8 MHz; image ±10 mm with 256 lines (0.078 mm); phantom x ±12 mm at 1×10⁸ m⁻² (96,000 scatterers); cyst back to T4's 6 mm radius (anechoic); `RX_F_NUMBER` = 1.0; `ELEMENT_DIRECTIVITY` = True | The 38.4 mm aperture covers ±10 mm, so the ±5 mm edge-wave limit is gone (brightness uniform within 0.2 dB); the finer 8 MHz resolution cell needs ~5× the scatterer density for fully developed speckle (SNR 1.73–1.92, theory 1.91) |
| `teams/T4_Tissue_Interaction/tissue_phantoms.py` | f0 passed to T3; **element directivity** sinc(w sin θ/λ) on transmit and receive (`incident_wave`, `point_echo`); parallel simulation over all CPU cores | With point elements the coarse pitch (1.56 λ) gave late "grating" ghosts at −11 to −13 dB below every point target; with directivity −21 to −34 dB. 96,000 scatterers take ≈4 min on 8 cores instead of ≈15 min |
| `teams/T5_RX_Beamforming/receive_beamforming.py` | **Dynamic receive aperture** (F# = 1, Hann centred on the line, normalised) | Grating-lobe streak from the shallow target −17 dB → below −100 dB; lateral width 0.31 → 0.47 mm. `f_number=None` gives the old beamformer bit for bit |
| `tests/parameter_tests.py` | Frequencies 4/8/12 MHz (at fs 128 MHz), sampling 32/64/128 MHz, same physics as main.py | 9/9 pass; two first versions failed and were fixed only after measuring the cause (docs/MODULES.md Section 11) |
| `demo.ipynb` | Shapes, labels, T2/T3 cells use `incident_wave` / `point_echo`, zoom around the 6 mm cyst | Runs with 0 errors |

Tested alternatives that were **not** adopted: transmit Tukey/Hann windows (no change to any
artefact level; Hann darkens the image edge by 5.8 dB), F# 1.5 / 2 (worse lateral width,
no artefact benefit).

Verified results with this probe (details: `docs/MODULES.md` Sections 6, 10, 11):

| Check | Result |
|---|---|
| T5 `verify_beamformer.py` | 4/4 pass (depth errors 0.008–0.040 mm) |
| Parameter tests | 9/9 pass (attenuation −16.11 / −32.21 dB vs −16 / −32 predicted; T2 focus +18.36 dB) |
| Point targets | at (−4.98, 10.01), (−0.04, 20.00), (+4.98, 29.99) mm; axial 0.33–0.35 mm, lateral 0.47 mm |
| Speckle | SNR 1.73–1.92 (6–38 mm); uniform across ±10 mm; −17 dB at 36–40 mm (8 MHz attenuation, no TGC) |
| Cyst (r = 6 mm, anechoic) | −19.4 dB vs surrounding ring; CNR 2.32 → 2.43, gCNR 0.860 → 0.871 after the filter, edges kept 96 % |
| Known artefacts | −25 dB diagonal arc next to the shallow (−5, 10) target (not changed by TX windows; not further root-caused); faint copies 2 mm below targets at −32/−34 dB |

## Project layout

```
Medical Ultrasound/
├── demo.ipynb                          team-by-team notebook demo (runs the whole pipeline)
├── simulator/                          integration (shared by all teams)
│   ├── config.py                       shared parameters + project paths
│   └── main.py                         one command: phantom -> final image
├── tests/
│   └── parameter_tests.py              plan's 24-Sep parameter tests
├── teams/                              one folder per team: original code + its pipeline stage
│   ├── T1_Transducer/                  (was "Transducer")
│   ├── T2_TX_Beamforming/              (was "TX Beamforming")
│   ├── T3_Acoustic_Propagation/        (was "Acoustic Propogation")
│   ├── T4_Tissue_Interaction/          (was "Tissue interaction")      + tissue_phantoms.py
│   ├── T5_RX_Beamforming/              (was "RX beamforming")          + receive_beamforming.py, mock_data.py
│   ├── T6_B_mode/                      (was "B mode", + B_mode.zip)    + bmode_formation.py
│   └── T7_Image_Recon_Post_Processing/ (was "image recon and post processing") + post_processing.py
├── docs/
│   ├── README.md                       this file (was "README (1).md")
│   └── MODULES.md                      per-module documentation
├── results/                            outputs of main.py and parameter_tests.py
└── .vscode/                            VS Code settings + run buttons
```

**Who wrote what.** Everything in `teams/` is the team's own deliverable, unchanged, **except** the
pipeline-stage modules marked `+` above, which were written during integration and placed in the
folder of the team whose stage they implement:

| Team folder | Team's original code (unchanged) | Stage module written during integration |
|---|---|---|
| `T1_Transducer/` | piezo-material registry (not used: no array geometry) | — (geometry from T3's `create_linear_array`, via `config.py`) |
| `T2_TX_Beamforming/` | `Usound/src/beamformer.py` (delays, apodization) | — (imaging chain uses broadcast; T2 used in tests/demo) |
| `T3_Acoustic_Propagation/` | `acoustic_propagation.py` (pulse, forward/return propagation) | — (called directly) |
| `T4_Tissue_Interaction/` | `tissue_interaction.py`, `phantom.py` | `tissue_phantoms.py` — phantoms + T3 → T4 → T3 RF chain |
| `T5_RX_Beamforming/` | `verify_beamformer.py` (test file only) | `receive_beamforming.py` (`das_beamform`), `mock_data.py` |
| `T6_B_mode/` | toy + real-carotid notebooks | `bmode_formation.py` — the notebook's algorithm as a function |
| `T7_Image_Recon_Post_Processing/` | recon + post-processing notebooks | `post_processing.py` — scan conversion (new) + the notebook's `guided()` (copied unchanged) |

`simulator/config.py` puts every team folder on the Python path, so the modules import each other by name.
Older sections of this document use the original folder names (e.g. `Acoustic Propogation/`,
`RX beamforming/`) and say "project root" for these modules; see the table above for where they are now.

---

## 1. Intended pipeline (per the master plan)

```
config.py
   │
   ▼
64-Element Transducer  (T1)
   │
   ▼
TX Pulse Generation  ─┐
   │                  │
   ▼                  │
TX Beamforming  (T2)   │
   │                   │
   ▼                   │
Acoustic Propagation (T3)
   │
   ▼
Tissue / Phantom  (T4)
   │
   ▼
Reflection / Scattering  (T4)
   │
   ▼
Return Propagation  (T3)
   │
   ▼
64-Channel RF Data
   │
   ▼
Receive DAS Beamforming  (T5)
   │
   ▼
Beamformed RF
   │
   ▼
Envelope Detection  (T6)
   │
   ▼
Log Compression  (T6)
   │
   ▼
B-mode Image  (T6)
   │
   ▼
Scan Conversion / Post-Processing  (T7)
   │
   ▼
FINAL IMAGE
```

## 2. Actual pipeline (as being integrated — see Section 5 for why it differs)

```
config.py (UNIFIED — see Section 6)
   │
   ▼
element_positions          ← T3's create_linear_array() (NOT T1's actual code)
   │
   ▼
build_phantom(kind)         ← 3 required types: point_targets / scatterers / cyst_lesion.
   │                            scatterers + cyst_lesion: T4's real phantom.py
   │                            (generate_liver_phantom), called with FOV bounds and a
   │                            speckle-level density from config (T4's defaults are too
   │                            sparse — see Section 4). point_targets: trivial, built here.
   ▼
raw_rf generation            ← T3's forward_propagation + return_propagation (tested, reused as-is),
   │                            called DIRECTLY per scatterer (not simulate_acoustic_propagation(),
   │                            which hard-wires T3's mock and sizes t_axis from the phantom),
   │                            + T4's real tissue_interaction() — verified to plug into T3's
   │                            real chain (bit-identical to T3's mock for amp-only scatterers).
   │                            SINGLE BROADCAST TRANSMIT (all 64 elements fire together) —
   │                            NOT per-scan-line TX focusing. TX delays = zeros via T3's tau_tx
   │                            hook. NOTE: T3 has no per-element TX weight input, so "Hanning-
   │                            apodized" requires a wrapper/extension — see Section 8.
   │                            (Why broadcast, not T2-style per-line focusing: see Section 5
   │                            item 2 — one simulation instead of 64, and T5's tests assume it.)
   ▼
das_beamform()                ← T5 — BUILT (receive_beamforming.py, project root); T5's own
   │                             verify_beamformer.py passes 4/4, unmodified. Interface +
   │                             broadcast-transmit assumption taken from that test file.
   │                             Dynamic RX-only focus, per depth, per scan line. Round-trip
   │                             delay computed geometrically per (line, depth) and sampled
   │                             against the RF's REAL t_axis (see Section 6, "Time axis").
   ▼
bmode_formation()             ← T6 — owns envelope detection + log compression
   │                             (Hilbert envelope → 20·log10 → clip to DYNAMIC_RANGE_DB →
   │                             normalize). Same algorithm as T6's real-carotid notebook
   │                             (B mode/B_mode_real_carotid_final/), rewritten as a pipeline
   │                             function; matches T6's saved output to ~5e-6 at 60 dB.
   ▼
scan_convert()                ← T7 — BUILT (post_processing.py). Linear array, so a straight
   │                             rectangular resample (bilinear) of the (depth × scan-line) grid,
   │                             cropped to 0–40 mm, square pixels inside OUTPUT_SIZE → 512 × 128 px
   │                             (0.079 mm/px). No fan / polar geometry.
   ▼
postprocess()                 ← T7 — BUILT (post_processing.py). The guided filter chosen in the
   │                             Post-Image Processing notebook (bit-identical to the notebook's
   │                             function), r = 4, eps = 0.001, optional gamma.
   ▼
FINAL IMAGE                     main.py → results/final_bmode.png
```

---

## 3. Team responsibilities & real folder locations

| Team | Members | Responsibility | Folder in `Medical Ultrasound/` |
|---|---|---|---|
| T1 | MR, RK | Transducer | `Transducer/` |
| T2 | CAR, CA | Transmit Beamforming | `TX Beamforming/Usound/` |
| T3 | PJ, CJD | Acoustic Propagation | `Acoustic Propogation/usound_sim/nitk_usoundsim/` |
| T4 | PMS, VSP | Tissue Interaction + Echo/RF Generation | `Tissue interaction/` (extracted from `NITK_UsoundSim_tissue_module.zip`, original zip kept alongside) |
| T5 | AMN, AVK | Receive DAS Beamforming | `RX beamforming/` (only `verify_beamformer.py`) |
| T6 | AJ, SR | B-mode Formation | `B mode/` (toy notebook + `B_mode_real_carotid_final/`: real in-vivo carotid beamformed RF + notebook, extracted from `B_mode.zip`, zip kept alongside) |
| **T7** | **VHP, DGM (this student: Darshil Maniya, 262SP009)** | **Image Reconstruction & Post-Processing** | `image recon and post processing/` |
| T8 | VRS, SBR | Project Leads / Integration | — |

## 4. Real module status (audited, not assumed)

| Module | Status | Notes |
|---|---|---|
| **Config** | ✅ **Unified `config.py` at project root (25 Sep)** | Imports T3's flat constants (`C`, `F0`, `FS`, `N_ELEMENTS=64`, `PITCH`, FOV, `DYNAMIC_RANGE_DB`, …) from `nitk_usoundsim/config.py` rather than copying them, and adds: T5 aliases/wrappers (`SPEED_OF_SOUND`, `SAMPLING_FREQUENCY`, `get_element_positions()` → shape `(64,)` x-positions, `get_scanline_positions()`), `Z_RF_MAX = 60 mm` with `get_t_axis()` (T3 convention, starts at −1.175 µs, 3306 samples) and `get_depth_axis()` (3118 points, dz = c/2fs), `get_tx_delays()` (zeros, broadcast), and phantom settings (density 2×10⁷ m⁻², FOV bounds, seed 2026, lesion 30 mm depth / 6 mm radius / hypoechoic). T2's 128-element JSON is not used. **26 Sep:** imaged scan lines narrowed to `SCANLINE_X_MIN/MAX` = ±5 mm (edge-wave fix, Section 8) while the phantom stays ±10 mm; lesion now r = 3 mm, `LESION_SCATTERING_SCALE = 0.0` (anechoic); added `TX_FOCUS_Z = None`, `RX_APODIZATION = "hann"`, and the plan-§5 parameters T3 does not use (`ELEMENT_WIDTH` = pitch, `ELEMENT_HEIGHT` = None, `BACKGROUND_IMPEDANCE_MRAYL` = 1.63, `DENSITY` ≈ 1058 kg/m³). |
| **T1 Transducer** | ⚠️ Present but wrong scope | `src/main.py`, `piezo.py`, `process.py`, `registry.py` implement a generic piezoelectric-material registry (random frequency generation within a range), **not** the required `element_positions` array (shape `(64,2)`, units, coordinate system). Not usable as-is; T3's `create_linear_array()` is used instead. |
| **T2 TX Beamforming** | ⚠️ Source reviewed — small, TX-delay only | Built for **128 elements @ 8 MHz** (Philips L12-4 reference). Source read in full: there is **no delay-and-sum** — `beamformer.py` only computes TX delays for **one fixed focus point** (`τ = (max(d) − d)/c`, config focus x=0, z=40 mm) or a linear plane-wave steer (focus ignored when steering ≠ 0; a 0° plane wave is not expressible), plus Hann/Hamming/rect apodization and a Gaussian pulse (`pulse_cycles` key unused). No per-line loop, no RX, no propagation. `beamformer.py` itself is element-count-agnostic (64 el @ 0.154 mm pitch, focus 30 mm → max delay 0.943 µs); the 128 limit is **hard-coded in `TransducerConfig.validate()` and `acoustic_handoff.load_tx_package()`**, so regenerating the JSON alone will not work. Its 2 tests pass. Delays are compatible with T3's `tau_tx` hook. No dynamic aperture, no multi-zone focus; apodization is fixed per shot. `docs/` also contains copies of T1's source files. |
| ↳ **T2 decision (25 Sep, final)** | ⛔ **Bypass for the main imaging chain — practical reasons only; code kept as the TX-beamforming deliverable** | **T2 does NOT have a depth-of-field problem.** The earlier claim that focused-transmit targets ~10 mm off focus vanished came from an error in an earlier, unsaved test — not from T2's design or T3's physics. Measured 25 Sep by feeding T2's delays (64 el, λ/2 pitch) into T3's real `forward_propagation`: on the beam's own axis a focused TX is never weaker than broadcast (focus 20 mm: +12.4 dB at focus, +2.4 dB at 10 mm, −0.3 dB at 35 mm; −6 dB lateral width 0.6 mm at focus vs ~9 mm broadcast, widening back to broadcast width off-focus). **Bypass reasons (practical only):** (1) per-line focusing needs one full T3 simulation per scan line — ≈50 min per speckle-density image (64 × 46.7 s, the measured time for one 16,000-scatterer broadcast frame); (2) T5's test file assumes one broadcast RF frame reused across all lines; (3) T3's engine does not support per-element TX amplitude weighting without modification. Main chain transmit = zero delays through T3's `tau_tx`. **T2's code is kept as the transmit-beamforming deliverable in its own right** (optionally producing a focused-vs-broadcast comparison figure by calling `beamformer.py`'s functions directly, not its 128-locked JSON path). |
| **T3 Acoustic Propagation** | ✅ Most complete, tested — **baseline confirmed clean, trustworthy** | `acoustic_propagation.py` — real, documented, working code: `create_linear_array`, `forward_propagation`, `mock_tissue_interaction` (placeholder, swappable), `return_propagation`, `simulate_acoustic_propagation`. Uses the correct 64-element/5MHz config. **Verified 25 Sep:** 22/22 tests pass; fresh demo output matches all saved `.npz` references — every key present, all labels/strings identical, all numeric arrays equal to within 1.3e-15 (floating-point round-off; file hashes are therefore not byte-identical, the data is). `acoustic_propagation_outputs.npz`, not written by the demo, also matches a fresh run. Demo PNGs are content-identical but not byte-identical (refs made with matplotlib 3.10.8; re-run used 3.8.3 — the RX pressure-field `imshow` panel renders with different downsampling). **Caveats:** (a) the demo writes into its own folder and overwrites the references — run it from a copy; (b) `forward_propagation` has no per-element TX weight input; (c) `simulate_acoustic_propagation` sizes `t_axis` from the phantom (3 points → ~36 mm, not Z_MAX) and starts at −1.175 µs, and takes no `t_axis` argument. **Treat this as the trusted physics engine.** |
| **T4 Tissue Interaction** | ✅ Real, tested, now includes phantom generation | Files in `Tissue interaction/`: `tissue_interaction.py`, `phantom.py`, `validate_phantom.py`, `tests/`, `README.md`, `validation_plots/`. `tissue_interaction()` (alias `mock_tissue_interaction`) scales the 1-D incident wave by `G = amp·(1+|R|)·interaction_scale`, `R = (Z2−Z1)/(Z2+Z1)`; with no impedance fields `G = amp`. `phantom.py`'s `generate_liver_phantom()` places uniform random scatterers (seed 2026) with signed Gaussian amplitudes and an optional elliptical lesion (scale 0.35 hypo / 1.0 iso / 1.8 hyper). **Verified 25 Sep:** 13/13 tests pass; `validate_phantom.py` reproduces the shipped plots; swapped into T3's real forward→return chain it gives output bit-identical to T3's mock, and T3 accepts T4's rich scatterer dicts. No 128-element dependency in code (only in their README). **Caveats:** (a) default density 120,000 m⁻² = 0.12/mm² ≈ 0.06 scatterers per resolution cell — far too sparse for speckle (need ~≥10/cell ≈ 2×10⁷ m⁻², 16,000 scatterers over the FOV; one broadcast RF frame measured at 46.7 s through T3, 2.92 ms/scatterer); (b) default extent x ±25 mm, z 10–60 mm ≠ config FOV (±10 mm, 0–40 mm) — pass bounds via `PhantomConfig`; (c) `1+|R|` is sign-less, so any lesion impedance mismatch brightens it (irrelevant unless lesion impedance is set). |
| **T5 Receive Beamforming** | ✅ **Built 25 Sep — all 4 T5 tests pass** | `receive_beamforming.py` (project root): `das_beamform(rf, element_positions, scanline_positions, config, apply_focus=True, t_axis=None) -> (beamformed (n_depths, n_lines), z_axis)`; accepts 2-D (one broadcast frame reused) or 3-D RF. Dynamic receive focus per depth per line: τ = τ_TX + τ_RX,m, τ_TX = nearest-element path (validated against T3's broadcast field over x = −10..+10 mm, z = 5..55 mm: worst 0.055 mm, symmetric), τ_RX,m = √((x_l−x_m)²+z²)/C, Hann RX apodization, lookup via `np.interp` on the real `t_axis` (Section 6 rule). `apply_focus=False` uses one fixed delay z/C per depth. `mock_data.py` builds test RF with the real T3→T4→T3 chain (`tissue_phantoms.simulate_rf`). Tests: T5's own `verify_beamformer.py`, unmodified — run `PYTHONPATH=. python3 "RX beamforming/verify_beamformer.py"` from the project root: test 1 error 0.049 mm (tol 0.096), test 2 peak 107.0 vs 71.4 unfocused, test 3 peak (−3.97, 24.97) mm, test 4 errors 0.023/0.018/0.022 mm at 15/40/55 mm. A deliberately broken `τ·FS` lookup fails tests 1 and 4 (~0.9 mm deep), so the tests do enforce the time-axis rule. Off-axis `point_targets`: peaks within half a line spacing at 64 lines; within 0.05 mm lateral / 0.02 mm depth at 0.05 mm line spacing. Known artifact: edge-wave ghost — see Section 8. **26 Sep:** `apodization` argument added ("hann" default from `config.RX_APODIZATION` / "hamming" / "rect"; default output bit-identical to before). With the ±5 mm scan lines, test 3's peak is at (−4.05, 24.97) mm; still 4/4 pass. |
| **T6 B-mode Formation** | ✅ **Built 25 Sep — `bmode_formation.py` (project root), verified on simulated and real data** | Two deliveries in `B mode/`: (1) `B_mode_toydata (1).ipynb` — synthetic circle image (`np.random.seed(42)`), not wired to upstream data; (2) **`B_mode_real_carotid_final/`** (extracted 25 Sep from `B_mode.zip`, zip kept; `__MACOSX`/`.DS_Store` skipped) — `B_mode.ipynb` + `carotid_1_rf.npy`, `carotid_2_rf.npy` (**already-beamformed** RF, 1218 depth × 128 lines, float32; per the notebook: in-vivo carotid, 128-element L12-50 probe, 5 MHz, single plane wave, fs 31.25 MHz, depth 5–35 mm, from EPFL LTS5 `us-non-stationary-deconv`) + `bmode_carotid_1.npy` / `_axes.npz` (their output). Algorithm: Hilbert envelope → normalise to peak → 20·log10 → clip to 60 dB → [0, 1]. The 60 dB is T6's own choice: the EPFL source displays these carotids at 40 dB (`dBRange = 40` in `deconvolution_carotid.m`). Their lateral axis is offset by half a pitch (`(i − N/2)·pitch`, not centred) — minor label bug. **Decision (25 Sep): T6's stage `bmode_formation()` owns envelope detection + log compression**, rewritten from this algorithm as a pipeline function. The carotid RF cannot go through `das_beamform()` (it has no per-channel data); it feeds `bmode_formation()` directly and is kept as a real-data check for it. **`bmode_formation(beamformed_rf, dynamic_range_db=None) -> bmode`** (n_depths, n_lines) in [0, 1]; default DR = `config.DYNAMIC_RANGE_DB` = **50 dB (decision 25 Sep: kept; no evidence favours 60 — T6's 60 is unsourced and EPFL shows these carotids at 40)**. Tests: off-axis `point_targets` (build_phantom → simulate_rf → das_beamform → bmode_formation, 50 dB): 3118×64, range [0, 1]; target levels vs frame peak (0, 20) 0.00 dB, (−5, 10) −4.09 dB, (+5, 30) −8.77 dB; edge-wave ghost −25.16 dB at (−5.87, 11.93) mm. Carotid_1 at `dynamic_range_db=60` vs T6's saved `bmode_carotid_1.npy`: max |diff| 5.1e-6 (float32 round-off). At 50 dB, 4.9% (carotid_1) / 5.7% (carotid_2) of pixels clip to black vs 0.5% / 0.6% at 60 dB. Rejects non-2-D input and DR ≤ 0; all-zero input → zeros. |
| **T7 Image Recon & Post-Processing** (this student) | ✅ **Built 26 Sep — `post_processing.py`** (`scan_convert()` + `postprocess()`), notebooks reviewed | `Post-Image Processing/262SP009_Post_Image_Processing_v2.ipynb` — a rigorous classical despeckling study (median/Lee/SRAD/Wavelet/Guided/NLM/TV/BM3D filters, tuned by grid search against CNR/gCNR/ENL/SI/Edge metrics) on **real downloaded clinical datasets** (BUSI breast, TN3K thyroid, kidney, liver), not synthetic data. `Image Reconstruction/UsoundIMGRECsample (2).ipynb` — **reviewed 25 Sep**: one code cell (plus a cell holding only a ChatGPT share link). Generates its own fake beamformed RF `(3201 samples, 64 lines)` @ 40 MHz/5 MHz, then DC removal → 2nd-order Butterworth 2–8 MHz band-pass (`filtfilt`) → Hilbert envelope → `z = c·t/2` → **±30° sector (polar) scan conversion** via `griddata` to 250×200. Output is a **linear envelope (not log-compressed)**, 48% zero-fill outside the fan. Re-runs reproducibly. **Decision (25 Sep): NOT reused for reconstruction.** Reasons: (1) it scan-converts onto a ±30° fan — phased/curved-array geometry, wrong for our linear array, where scan conversion is a straight rectangular resample (`lateral_positions_mm` is computed but unused; its 0.5 mm pitch ≠ config's 0.154 mm); (2) no log compression, so its output is not a B-mode image; (3) it assumes the RF time axis starts at 0, but T3's `t_axis` starts at −1.175 µs. Its 2–8 MHz Butterworth band-pass **may** be salvaged later as an optional pre-beamforming denoise step (not a blocker). **T7's pipeline role is now: `scan_convert()` (rectangular resize to `OUTPUT_SIZE`) + `postprocess()` (classical despeckle filters).** **Built 26 Sep:** `scan_convert` = bilinear resample to square pixels (512 × 128 px, 0.079 mm/px; `keep_aspect=False` stretches to exactly 512 × 512 — not the default because the filter window is in pixels); `postprocess` = the notebook's `guided` filter, verified bit-identical to the notebook's own function, r = 4, eps = 0.001 (the notebook's tuned fixed value), optional gamma. On the simulator it reduces speckle only ≈10 % (SI 0.107 → 0.097): speckle grains here are ≈6 × 13 px, larger than the 9 × 9 window; eps = 0.01 gives SI −40 % but halves edge sharpness, so the notebook value is kept. Cyst: gCNR 0.630 → 0.635, edge ratio 0.91. |

---

## 5. Why the actual pipeline differs from the plan

1. **T1's code doesn't produce array geometry** → bypassed in favor of T3's `create_linear_array()`.
2. **Single broadcast/unfocused transmit + fully dynamic receive-side focus at every depth, instead of T2-style per-scan-line focused transmit — for practical reasons only.** T2 does **not** have a depth-of-field problem: the earlier report of off-focus targets vanishing was an error in an earlier, unsaved test, and T3's physics shows a focused transmit is never weaker than broadcast on its own axis (see the T2 decision row in Section 4). Broadcast is used because (a) per-line focusing would cost ≈50 min per speckle-density image vs 46.7 s measured for one broadcast frame, (b) T5's test file assumes one broadcast RF frame reused across all lines, and (c) T3's engine does not support per-element TX amplitude weighting without modification. T2's code remains the transmit-beamforming deliverable.
3. **T4's phantom generator (`phantom.py`, delivered 25 Sep) is used for the scatterer and cyst phantoms**, with bounds and density overridden from config (its defaults are too sparse for speckle and cover a different area). Only the point-target phantom is built separately.
4. **T5 delivered only a test file; T6 delivered its algorithm as a notebook on real (already-beamformed) carotid data** → `das_beamform()` was built from scratch with T5's test file as the spec (now built, 4/4 pass). `bmode_formation()` re-implements T6's notebook algorithm as a pipeline function (verified against T6's own saved output) and owns envelope detection + log compression.
5. **T7's Image Reconstruction notebook is not reused** (fan geometry, no log compression, assumes t starts at 0 — see Section 4). T7's pipeline role is `scan_convert()` (rectangular resize to `OUTPUT_SIZE`) + `postprocess()`. The Post-Image Processing notebook processes real clinical images, not synthetic output → its filter functions need extracting and reapplying to the synthetic B-mode array; the notebook itself isn't a pipeline stage that can be called directly. (Done 26 Sep: `post_processing.py`.)
6. **T3's `simulate_acoustic_propagation()` is not used directly** — it hard-wires T3's mock tissue model and sizes `t_axis` from the phantom. `forward_propagation` / `return_propagation` are called directly with a config-defined `t_axis` and T4's `tissue_interaction`.

## 6. Config unification (do this first)

Single source of truth should be T3's flat-constant style (most complete, tested, and what the acoustic propagation engine — the core of the whole simulator — already depends on):

```python
C, F0, FS, N_ELEMENTS(=64), PITCH, X_MIN, X_MAX, Z_MIN, Z_MAX,
N_SCANLINES, PHANTOM_POINTS, DYNAMIC_RANGE_DB, OUTPUT_SIZE, ALPHA_0
```

Add thin function-style wrappers (`get_element_positions()`, `get_scanline_positions()`,
`SPEED_OF_SOUND` as an alias for `C`, `SAMPLING_FREQUENCY` as an alias for `FS`) so T5's
test file can run against the same real values without rewriting it.

Also needed in the unified config (from the 25 Sep review):

- **Time / depth axis** defined in config, starting consistently with T3's convention and
  reaching **at least 55 mm** (T5's test 4 checks a target at z = 55 mm).
- **Phantom settings** for T4's `PhantomConfig`: bounds = imaging FOV, scatterer density
  ≈ 2×10⁷ m⁻² (≈10 per resolution cell), lesion geometry/class, seed.
- **TX settings**: broadcast, zero delays (T2 bypassed — see Section 4). No TX apodization
  (T3 has no per-element weight input — see Section 8).
- **B-mode setting**: `DYNAMIC_RANGE_DB`. The optional 2–8 MHz band-pass is not in config
  until/unless it is salvaged.

T2: regenerating its JSON for 64 elements / 5 MHz is **not sufficient** — the 128 limit is
hard-coded in `TransducerConfig.validate()` and `load_tx_package()`. For the optional
focused-vs-broadcast comparison figure, call `beamformer.py`'s functions directly with config
values instead of its JSON/dataclass path.

**HARD RULE — time-axis lookups (applies to every module from here on).**
Every delay-to-sample lookup must use `np.interp(tau, t_axis, rf)` against the **real**
`t_axis` array that came with the RF. **Never** use `tau * FS` (or `int(round(tau * FS))`) as an
index. Reason: T3's `t_axis` does not start at 0 — `t_axis[0] = −1.175 µs` — and `tau * FS`
silently assumes it does, shifting every target by ~0.90 mm in depth. That is exactly the bug the
T7 Image Reconstruction notebook had. Consequences:

- `t_axis` travels with the RF, always (`simulate_rf()` returns `(rf, t_axis)`).
- In `das_beamform()` the round-trip delay is computed geometrically per (scan line, depth,
  element), `τ = (d_TX + d_RX,m) / C`, and then sampled with `np.interp` on the real `t_axis`.
  Computing τ geometrically is not enough by itself — the lookup is where the bug lives.
  Restate this rule in `das_beamform()`'s module documentation.
- T5's test 1 (0.096 mm tolerance) catches a violation **only if** the RF it tests on also starts
  at a non-zero time, so T5's mock RF should use T3's `t_axis` convention.

Note: the phantom's lateral extent (±10 mm) is about twice the aperture width (±4.93 mm at λ/2 pitch). Since 26 Sep only ±5 mm is imaged (Section 8, edge-wave item).

## 7. Required deliverables (per the master plan, Section 9)

**Code:** `config.py`, `main.py`, transducer module, TX beamforming module, propagation
module, tissue/RF module, receive DAS module, B-mode module, post-processing module.

**Results (minimum):** Point-target B-mode, Scatterer B-mode, Cyst/lesion-like B-mode.

**Documentation, per module:** (1) module explanation, (2) inputs, (3) outputs,
(4) equations actually used, (5) algorithm, (6) assumptions, (7) limitations,
(8) test result. This is part of the plan's own "Definition of Done" — a module
isn't complete just because it runs.

**Status 26 Sep — all delivered:**

| Deliverable | Where |
|---|---|
| `config.py`, `main.py` | project root |
| Transducer module | T3's `create_linear_array()` via `config.get_element_positions()` (T1's code is out of scope, Section 4) |
| TX beamforming module | T2, `TX Beamforming/Usound/` (bypassed in the imaging chain; its delays are used in `parameter_tests.py`) |
| Propagation module | T3, `Acoustic Propogation/usound_sim/nitk_usoundsim/` |
| Tissue/RF module | T4, `Tissue interaction/` + `tissue_phantoms.py` |
| Receive DAS module | `receive_beamforming.py` |
| B-mode module | `bmode_formation.py` |
| Post-processing module | `post_processing.py` |
| Point / scatterer / cyst B-mode | `results/final_bmode.png`, `results/<kind>.png`, `results/<kind>_final_bmode.npy` |
| Per-module documentation (8 items) | `MODULES.md` |
| Parameter tests (plan 24 Sep) | `parameter_tests.py`, `results/parameter_tests.png` |

## 8. Open items before final integration

- [x] Review `Image Reconstruction/UsoundIMGRECsample (2).ipynb` in full — done 25 Sep.
      **Decision: not reused for reconstruction** (±30° fan geometry wrong for a linear array;
      no log compression; assumes t starts at 0). Its 2–8 MHz band-pass may be salvaged later
      as an optional pre-beamforming denoise step — not a blocker. T6 owns envelope + log
      compression; T7 owns scan conversion (rectangular resize) + despeckle filters.
- [x] Read T2's actual source — done 25 Sep. **Decision: bypass for the imaging chain**
      (see the T2 decision row in Section 4 and Section 5 item 2).
- [x] Run T3's test suite and diff fresh output against saved references — done 25 Sep.
      **Confirmed clean:** 22/22 pass; all saved `.npz` data reproduced (to 1.3e-15 round-off).
      Baseline is trustworthy.
- [x] Receive and review T4's updated module and T5's test file — done 25 Sep (see Section 4).
- [x] **Resolve "Hanning-apodized broadcast" vs "T3 reused as-is":** (Closed 26 Sep: TX Hann apodization was prototyped with a scratch wrapper calling T3's `forward_propagation` once per element — bit-identical to T3 with all-ones weights. It removes the edge wave (−42 to −75 dB) but leaves only a ≈±3 mm insonified strip: brightness −7.6 dB at |x| 2–4 mm, −19 dB at 4–5 mm; off-axis targets at ±5 mm drop to −26/−32 dB. **Not adopted**; no TX apodization in the chain.) T3's
      `forward_propagation` has no per-element TX weight input, only `tau_tx`. Either the
      apodization was never applied in the earlier test render, or T3 was wrapped/modified.
      The integration code described in Section 2 (earlier `das_beamform`, `build_phantom`,
      broadcast render) is not in this folder, so this could not be checked. **For the new
      build: no TX apodization** (T3 is used unmodified). Revisit only if needed.
- [x] (Done 25 Sep — all 4 pass, see Section 4 T5 row.) Write `receive_beamforming.py`, `mock_data.py` and the function-style config
      wrappers T5's test file imports, then run `verify_beamformer.py` against the newly-built
      `das_beamform()` — all 4 tests should pass (depth axis must reach 55 mm for test 4).
      Add one extra check on real T3 RF, since T5's tests only use their own mock RF.
- [x] (Done 25 Sep — peaks correct; vertical banding not reproduced; edge-wave ghost found, see its own item. **26 Sep: targets moved to (−4, 10), (0, 20), (+4, 30) mm** so they sit inside the ±5 mm imaged FOV.) **First test once `das_beamform()` exists:** run it on `build_phantom("point_targets")`
      (tissue_phantoms.py: (−5, 10), (0, 20), (+5, 30) mm, amp 1.0 — off-axis on purpose;
      ±5 mm is just outside the ±4.93 mm aperture). Check (a) each beamformed peak lands at
      its expected (x, z) — the depth/lateral accuracy check; the two off-axis points have no
      saved T3 reference, so this is their validation — and (b) whether the lateral-edge
      striping artifact (next item) reproduces on this phantom.
- [x] **Edge-wave ghost echo ("transmit-edge effect") — found 25 Sep; FIXED 26 Sep by narrowing the imaged lines to ±5 mm (option B).**
      In the off-axis `point_targets` render (build_phantom → simulate_rf → das_beamform), a ghost
      appears at about **(−6, 12) mm**, below/outside the (−5, 10) mm target: **−21.4 dB relative to
      that target** (−25.2 dB relative to the brightest target in the image). A second one sits
      just below (+5, 30) mm at −19.3 dB. Cause: the broadcast transmit fires all 64 elements at
      full amplitude, so near/beyond the aperture ends a second, late wave arrives from the far
      end of the array; T3's incident wave shows it at −20.7 dB, and its predicted image
      position (z = 11.88 mm on the x = −5.95 mm line) matches the ghost (11.92 mm). TX Hanning
      apodization would normally suppress it, but T3 has no per-element TX amplitude input.
      Unlike the faint edge fragments (−42 to −50 dB, at the display floor), **−21 dB is clearly
      visible in a 50 dB display.** **Re-check when rendering the `scatterers` and `cyst_lesion`
      phantoms:** one ghost near one point target is a curiosity, but if it recurs across many
      scatterers (e.g. a faint shifted copy of the speckle ~20 dB down, strongest near the
      lateral edges), it is a real image-quality problem to fix before final documentation
      (options: TX apodization via a wrapper around T3's `forward_propagation`, or narrowing
      the lateral FOV toward the aperture).
  **25 Sep — RE-CHECKED ON SPECKLE: IT RECURS; real problem at the lateral edges.** Measured with a scratch-only
      diagnostic (each scatterer's T3 incident wave gated to its first arrival ±1.175 µs, which removes later
      edge-wave arrivals; image is linear, so full − gated = edge-wave part; validated on `point_targets`:
      targets unchanged to 0.01 dB, (−6, 12) ghost −25.16 → −90.16 dB). Scatterer phantom, z 5–40 mm, edge-wave
      power relative to the edge-wave-free image: |x| 0–4 mm −30 to −32 dB (negligible); 4–6 mm −24 to −19 dB;
      6–8 mm **−13 dB**; 8–10 mm **−8 dB** (worst 2×2 mm patch +0.8 dB, shallow corners). 17% of the FOV is within
      10 dB. Displayed-pixel change at 50 dB: median 0.33, 95th pct 4.8, 99th pct 9.3 dB. Same numbers for
      `cyst_lesion`. The off-aperture strips are also 14–20 dB dimmer (broadcast barely insonifies them).
      Unresolved: the −28.3 dB feature just below (+5, 30) is unchanged by the gate (at 30 mm the far-end arrival
      falls inside it), so this test cannot classify it. (With TX apodization it drops to −70 dB, far more than its
      target, so it is edge-related.)
  **26 Sep — FIX: option B**, scan lines ±5 mm (`config.SCANLINE_X_MIN/MAX`), phantom still ±10 mm. Inside ±5 mm the
      edge-wave part is −24 to −32 dB, brightness falls only 4 dB at the edge (vs 19 dB at ±10 mm), and the line spacing
      halves to 0.159 mm (≈3.3 lines per lateral speckle half-width, was 1.7). **Residual:** a ghost −27.26 dB re frame
      peak at (−4.68, 11.65) mm, below the (−4, 10) target — documented as a limitation of broadcast transmit.
- [x] **Scatterer + cyst_lesion renders (25 Sep, 50 dB, 3118×64, 16,000 scatterers, 2,212 inside the lesion,
      ~46–50 s each).** Speckle: envelope SNR 1.80–1.92 at z 12–26 mm inside the aperture (Rayleigh 1.91);
      1.57 at 8–10 mm, 2.1–2.2 at 28–34 mm, 1.45 at 36–38 mm. Speckle grain matches the PSF (axial ACF FWHM
      0.50 mm = point PSF 0.50 mm; lateral ≈1.06 vs 1.27 mm) but only ~1.7 lines per lateral half-width at
      64 lines / 20 mm (0.317 mm) — borderline lateral undersampling. Cyst: lesion (r ≤ 4.5 mm) vs the same ROI
      in the lesion-free image **−9.12 dB** (= T4's 0.35 scale); vs tissue directly above, same image
      **−8.7 dB**; vs below −6.4 dB; the edge wave does not change these (−8.72 / −6.35 dB without it). A ring at
      r 7.5–9.5 mm reads +5.7 dB, only because it lies off-aperture where the image is 14–20 dB dimmer.
      Region below the phantom (z 42–50 mm) is at −57 to −61 dB, invisible at 50 dB.
- [x] (Closed 26 Sep: not reproduced; the edge region it was seen in is no longer imaged.) Investigate a grating-lobe-like striping artifact observed near the lateral FOV
      edges in an early test render of the broadcast+RX-focus beamformer — not yet
      root-caused. **25 Sep: does NOT reproduce** in the new chain (off-axis point_targets,
      64 lines × 250 depths, 50 dB): edge lines show the smallest line-to-line level jumps in the
      image (mean 0.6–0.8 dB, background ≈ −72 dB); only faint arc tails reach −42 to −50 dB.
      Most likely specific to the earlier, unsaved code (unconfirmed). Earlier lead (untested): at λ/2 pitch true grating lobes are unlikely; the FOV
      (±10 mm) extends well beyond the aperture (±4.93 mm), so edge lines are formed at
      steep receive angles with a truncated effective aperture.
- [x] **T7 built (26 Sep):** `post_processing.py` — see the T7 row in Section 4.
- [x] **`main.py` (26 Sep):** one command, all three phantoms, ≈95 s; two separate runs give bit-identical RF and
      final images. Results (50 dB, 512 × 128 px): point targets at (−4.05, 9.99) 0.00 dB, (+0.08, 19.98) −2.25 dB,
      (+4.05, 29.99) −7.28 dB; speckle SI 0.107 → 0.097; anechoic 3 mm cyst −16.01 dB vs ring, CNR 1.243,
      gCNR 0.630 (0.635 after the filter). With T4's hypoechoic default (0.35) the 3 mm cyst reads only −3.9 dB,
      gCNR 0.40 — the reason for the anechoic setting.
- [x] **Parameter tests (26 Sep, plan's 24-Sep item):** `parameter_tests.py`, 9/9 checks pass — axial width
      0.943 / 0.500 / 0.346 mm at 3 / 5 / 7.5 MHz (predicted 0.907 / 0.544 / 0.363); attenuation extra loss
      −9.99 / −19.98 dB at α0 0.5 / 1.0 (predicted −10.00 / −20.00); T2's focus at 20 mm +12.47 dB at a 20 mm
      target; rect / Hamming / Hann lateral widths 0.780 / 1.180 / 1.300 mm, sidelobes −13.9 / −37.2 / −30.1 dB;
      fs 20 / 40 / 80 MHz same peak depth (one depth sample), level converging (+2.47 then +0.67 dB — linear
      interpolation is a low-pass; the first version of the check expected a constant level and failed).
- [x] **`MODULES.md` (26 Sep):** 8-item documentation for each of 9 modules + results + parameter tests.
- [ ] The project folder is not a git repository (plan p18–19) — not initialised; ask before doing it.
- [ ] Optional: T2 focused-vs-broadcast comparison figure.
- [ ] Decide whether to keep or credit the ChatGPT share-link cell in the Image
      Reconstruction notebook before submission.
- [ ] T1's remaining files (`registry.py`, `exceptions.py`, `new_piezo.py`,
      `add_attributes.py`) haven't been individually reviewed — low priority given the
      scope mismatch is already clear from `main.py`/`piezo.py`/`process.py`.

## 9. Timeline status

| Date | Milestone |
|---|---|
| 23 Sep | First complete end-to-end B-mode image (target) |
| 24 Sep | Physical validation + debugging |
| 25 Sep | Final integration + documentation freeze |
| **26 Sep** | **FINAL DEMO / SUBMISSION** — pipeline complete: `main.py`, results, `MODULES.md`, parameter tests |

Per the plan's own rules: no new algorithms after 23 Sept — priority from here is
**debug → validate → document**, not add features. Fallback hierarchy if anything is
too hard to finish properly: a complete working pipeline beats a physically perfect
but incomplete one.
