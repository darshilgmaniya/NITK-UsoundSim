"""
receive_beamforming.py
======================

T5 receive delay-and-sum (DAS) beamformer for the NITK-UsoundSim integration.

    das_beamform(rf, element_positions, scanline_positions, config,
                 apply_focus=True, t_axis=None, apodization=None, f_number=None)
                 -> (beamformed, z_axis)

Inputs
------
rf                 : (n_elements, n_samples) one broadcast frame, reused for
                     every scan line, or (n_elements, n_samples, n_lines), one
                     frame per line.
element_positions  : (n_elements,) element x-positions [m], elements at z = 0.
scanline_positions : (n_lines,) scan-line x-positions [m].
config             : the project config module (depth axis, speed of sound,
                     default time axis).
t_axis             : time axis [s] the RF was sampled on. Defaults to
                     config.get_t_axis(), which is what tissue_phantoms and
                     mock_data produce.
apodization        : receive window, "hann" | "hamming" | "rect". Defaults to
                     config.RX_APODIZATION ("hann").
f_number           : receive F-number of the dynamic (growing) aperture.
                     Defaults to config.RX_F_NUMBER (1.0); None = fixed full
                     aperture with the window across the whole array.

Outputs
-------
beamformed : (n_depths, n_lines) beamformed RF -- not an envelope; envelope
             detection + log compression belong to T6's bmode_formation().
z_axis     : (n_depths,) depth [m], config.get_depth_axis() (0 to 60 mm,
             dz = C / (2 FS)).

Algorithm (dynamic receive focus, every depth of every scan line)
-----------------------------------------------------------------
For scan line x_l and depth z:

    tau_TX(z)    = min_n sqrt((x_l - x_n)^2 + z^2) / C
    tau_RX,m(z)  = sqrt((x_l - x_m)^2 + z^2) / C
    s_l(z)       = sum_m  w_m(z) * rf_m(tau_TX + tau_RX,m) / sum_m w_m(z)

tau_TX models the single broadcast transmit (all elements fire together, zero
delays): the wave reaches (x_l, z) first from the nearest element. Checked
against T3's forward_propagation: the incident envelope peak is within
0.05 mm of this for x = 0..10 mm, z = 5..55 mm. w is the receive window across
the aperture (Hann by default).

Dynamic receive aperture (F-number, default 1.0): at depth z only elements
with |x_m - x_l| < a(z) = z / (2 F#) receive (at least 2 pitches), and the
window is centred on the scan line: w_m(z) = window(|x_m - x_l| / a(z)), e.g.
Hann cos^2(pi u / 2). The sum is divided by sum_m w_m(z) so a point target
has the same amplitude at every depth. This limits the receive angle to
atan(1 / (2 F#)) = 26.6 deg: with the Philips L12-4's coarse pitch
(0.30 mm = 1.56 lambda at 8 MHz) steeper angles give grating lobes -- a
streak from the shallow point target at -17 dB with the fixed full aperture,
below -100 dB with F# = 1 (lateral -6 dB width 0.31 -> 0.47 mm).

With apply_focus=False, tau_RX,m = z / C for every element -- one
fixed delay per depth, no per-element compensation -- so the image is visibly
defocused (T5 verification test 2).

TIME-AXIS RULE (README Section 6)
---------------------------------
rf_m(tau) is read with np.interp(tau, t_axis, rf[m]) on the REAL t_axis, never
tau * FS as an index. t_axis starts at -1.175 us (T3's convention), so
tau * FS would put every target ~0.90 mm too deep. Computing tau geometrically
does not avoid this by itself -- the lookup is where the bug lives. Delays
outside t_axis read as 0.

Assumptions / limitations
-------------------------
- The dynamic aperture has a hard edge at a(z) (softened by the window).
- Element directivity is applied in the RF simulation (tissue_phantoms), not here.
- Straight-ray, constant speed of sound C.
"""

import numpy as np


_WINDOWS = {"hann": np.hanning, "hamming": np.hamming, "rect": np.ones}
# Same windows as functions of u = |x_m - x_l| / a(z) in [0, 1) (dynamic aperture)
_WINDOW_U = {"hann": lambda u: np.cos(np.pi * u / 2) ** 2,
             "hamming": lambda u: 0.54 + 0.46 * np.cos(np.pi * u),
             "rect": lambda u: np.ones_like(u)}


def das_beamform(rf, element_positions, scanline_positions, config, apply_focus=True, t_axis=None,
                 apodization=None, f_number="config"):
    """Delay-and-sum receive beamforming; see module docstring."""
    rf = np.asarray(rf, dtype=float)
    x_el = np.asarray(element_positions, dtype=float)
    x_lines = np.atleast_1d(np.asarray(scanline_positions, dtype=float))
    t_axis = config.get_t_axis() if t_axis is None else np.asarray(t_axis, dtype=float)
    z_axis = config.get_depth_axis()
    c = config.SPEED_OF_SOUND

    if rf.ndim == 2:
        rf = rf[:, :, None]  # one broadcast frame, reused for every line
    if rf.shape[0] != x_el.size or rf.shape[1] != t_axis.size:
        raise ValueError(
            f"rf shape {rf.shape[:2]} does not match (n_elements={x_el.size}, len(t_axis)={t_axis.size})"
        )
    if rf.shape[2] not in (1, x_lines.size):
        raise ValueError(f"rf has {rf.shape[2]} frames for {x_lines.size} scan lines")

    apodization = getattr(config, "RX_APODIZATION", "hann") if apodization is None else apodization
    if apodization not in _WINDOWS:
        raise ValueError(f"apodization must be one of {sorted(_WINDOWS)}, got {apodization!r}")
    f_number = getattr(config, "RX_F_NUMBER", None) if f_number == "config" else f_number
    fixed_weights = _WINDOWS[apodization](x_el.size)
    if f_number is not None:
        pitch = np.min(np.diff(np.sort(x_el))) if x_el.size > 1 else 0.0
        half_aperture = np.maximum(z_axis / (2 * f_number), 2 * pitch)
    beamformed = np.zeros((z_axis.size, x_lines.size))

    for l, x in enumerate(x_lines):
        frame = rf[:, :, l if rf.shape[2] > 1 else 0]
        tau_tx = np.hypot(x - x_el[:, None], z_axis[None, :]).min(axis=0) / c
        weight_sum = np.zeros(z_axis.size)
        for m in range(x_el.size):
            if f_number is None:
                w = fixed_weights[m]
            else:
                u = np.abs(x - x_el[m]) / half_aperture
                w = np.where(u < 1, _WINDOW_U[apodization](np.minimum(u, 1)), 0.0)
                if not w.any():
                    continue
                weight_sum += w
            tau_rx = np.hypot(x - x_el[m], z_axis) / c if apply_focus else z_axis / c
            beamformed[:, l] += w * np.interp(
                tau_tx + tau_rx, t_axis, frame[m], left=0.0, right=0.0
            )
        if f_number is not None:
            beamformed[:, l] /= np.maximum(weight_sum, 1e-12)

    return beamformed, z_axis
