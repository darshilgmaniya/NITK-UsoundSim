"""
tissue_phantoms.py
==================

Tissue / RF module for the NITK-UsoundSim integration.

    build_phantom(kind, seed)  -> list of scatterer dicts (at least "x", "z", "amp")
    incident_wave(s, t_axis)   -> transmit wave arriving at one scatterer
    point_echo(s, t_axis)      -> (N_ELEMENTS, len(t_axis)) echo of one scatterer
    simulate_rf(scatterers, t_axis=None, workers=None)
                               -> (rf, t_axis), rf shape (N_ELEMENTS, len(t_axis))

Phantom kinds
-------------
point_targets : POINT_TARGETS below -- 3 points at 10/20/30 mm depth, one
                on-axis and two off-axis at x = -5 / +5 mm, amp 1.0, so the
                image checks lateral position as well as depth. (T3's
                config.PHANTOM_POINTS are all on-axis: a depth calibration,
                not a lateral test.) Deterministic, so ``seed`` is ignored.
scatterers    : T4's generate_liver_phantom() over x = +/-12 mm, z = 0-40 mm
                at config.PHANTOM_DENSITY_M2, signed Gaussian amplitudes,
                no lesion.
cyst_lesion   : the same scatterer field (same seed -> identical positions and
                amplitudes) plus T4's elliptical lesion (30 mm depth, 6 mm
                radius -- config.LESION_RADIUS_*). Amplitudes inside are
                scaled by config.LESION_SCATTERING_SCALE (0.0 = anechoic cyst;
                None = T4's default for the echo class, 0.35 for hypoechoic).
                Each dict carries "is_lesion".

RF generation (single broadcast transmit)
-----------------------------------------
For every scatterer, with T3 and T4 used unmodified:

    T3 forward_propagation (tau_tx = zeros: all 128 elements fire together)
      -> T4 tissue_interaction (reflection: amp * (1+|R|) * scale)
      -> T3 return_propagation
    and the per-scatterer echoes are summed (linear superposition).
T3's functions default to T3's own 5 MHz, so f0 = config.F0 (8 MHz, Philips
L12-4) is passed explicitly.

Element directivity (config.ELEMENT_DIRECTIVITY): T3's elements are points.
point_echo() weights each element by the far-field factor of a rectangular
element of width w = config.ELEMENT_WIDTH,

    D_n = sinc(w * sin(theta_n) / lambda),   sinc(u) = sin(pi u) / (pi u),

where theta_n is the angle between the element normal and the scatterer, on
transmit (T3's forward_propagation called per element, contributions weighted
by D_n and summed) and on receive (echo on element n multiplied by D_n).
With D_n = 1 for all n this is exactly T3's own sum.

Because the echoes simply add, large phantoms (>= PARALLEL_MIN scatterers) are
split into interleaved chunks simulated in parallel processes and the chunk RFs
are summed. The result equals the serial sum up to floating-point rounding
(~1e-15 relative) and is identical from run to run.

TIME-AXIS RULE (README Section 6 -- applies to every module)
-------------------------------------------------------------
Every delay-to-sample lookup must use ``np.interp(tau, t_axis, rf)`` against the
REAL ``t_axis``, never ``tau * FS`` as an index. ``t_axis`` does not start at 0
(it starts at minus one pulse half-width, -0.75 us at 8 MHz, T3's convention),
so ``tau * FS`` shifts every target in depth -- the bug the Image
Reconstruction notebook had.
This module does no such lookup itself (T3's return_propagation already shifts
with np.interp on t_axis), but it returns ``t_axis`` together with ``rf`` so
the next module, das_beamform(), can and must follow the rule.
"""

import os
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool

import numpy as np

import config  # also puts T3's package and this folder (T4) on sys.path

from nitk_usoundsim.acoustic_propagation import forward_propagation, return_propagation  # noqa: E402
from phantom import LesionProperties, PhantomConfig, generate_liver_phantom  # noqa: E402
from tissue_interaction import tissue_interaction  # noqa: E402

KINDS = ("point_targets", "scatterers", "cyst_lesion")

# Point-target phantom [m]: one on-axis and two off-axis targets inside the
# imaged FOV (+/-10 mm), so the image checks lateral position as well as depth.
POINT_TARGETS = (
    {"x": -0.005, "z": 0.010, "amp": 1.0},
    {"x": 0.000, "z": 0.020, "amp": 1.0},
    {"x": 0.005, "z": 0.030, "amp": 1.0},
)
PARALLEL_MIN = 2000  # phantoms with at least this many scatterers are simulated in parallel


def build_phantom(kind, seed=config.PHANTOM_SEED):
    """Return the scatterer list for one of KINDS (positions in metres)."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
    if kind == "point_targets":
        return [dict(p) for p in POINT_TARGETS]

    lesion = None
    if kind == "cyst_lesion":
        lesion = LesionProperties(
            center_x_m=config.LESION_CENTER_X,
            center_z_m=config.LESION_CENTER_Z,
            radius_x_m=config.LESION_RADIUS_X,
            radius_z_m=config.LESION_RADIUS_Z,
            echo_class=config.LESION_ECHO_CLASS,
            scattering_scale=config.LESION_SCATTERING_SCALE,
        )
    phantom = generate_liver_phantom(PhantomConfig(
        x_min_m=config.PHANTOM_X_MIN,
        x_max_m=config.PHANTOM_X_MAX,
        z_min_m=config.PHANTOM_Z_MIN,
        z_max_m=config.PHANTOM_Z_MAX,
        scatterer_density_m2=config.PHANTOM_DENSITY_M2,
        seed=seed,
        lesion=lesion,
    ))
    return phantom.scatterers


def element_directivity(s, f0=None):
    """Directivity D_n (N_ELEMENTS,) of every element towards scatterer s; all ones if disabled."""
    element_x = config.get_element_positions()
    if not config.ELEMENT_DIRECTIVITY:
        return np.ones(element_x.size)
    f0 = config.F0 if f0 is None else f0
    sin_theta = np.abs(s["x"] - element_x) / np.hypot(s["x"] - element_x, s["z"])
    return np.sinc(config.ELEMENT_WIDTH * sin_theta * f0 / config.C)


def incident_wave(s, t_axis, f0=None, alpha0=None, tau_tx=None):
    """Transmit wave at scatterer s: T3 forward_propagation per element, weighted by D_n."""
    f0 = config.F0 if f0 is None else f0
    alpha0 = config.ALPHA_0 if alpha0 is None else alpha0
    element_x = config.get_element_positions()
    tau_tx = config.get_tx_delays() if tau_tx is None else np.asarray(tau_tx, dtype=float)
    d = element_directivity(s, f0)
    if np.all(d == 1.0):
        return forward_propagation(s, element_x, t_axis, f0=f0, alpha0=alpha0, tau_tx=tau_tx)[0]
    wave = np.zeros_like(t_axis)
    for n in range(element_x.size):
        wave += d[n] * forward_propagation(s, element_x[n:n + 1], t_axis, f0=f0, alpha0=alpha0,
                                           tau_tx=tau_tx[n:n + 1])[0]
    return wave


def point_echo(s, t_axis, f0=None, alpha0=None, tau_tx=None):
    """Echo of scatterer s on every element: incident wave -> T4 reflection -> T3 return, x D_n on receive."""
    f0 = config.F0 if f0 is None else f0
    alpha0 = config.ALPHA_0 if alpha0 is None else alpha0
    incident = incident_wave(s, t_axis, f0, alpha0, tau_tx)
    reflected = tissue_interaction(incident, s)
    echo, _, _ = return_propagation(reflected, t_axis, s, config.get_element_positions(), f0=f0, alpha0=alpha0)
    return echo * element_directivity(s, f0)[:, None]


def _rf_sum(args):
    """Summed echoes of a list of scatterers (one broadcast transmit)."""
    scatterers, t_axis = args
    rf = np.zeros((config.N_ELEMENTS, t_axis.size))
    for s in scatterers:
        rf += point_echo(s, t_axis)
    return rf


def simulate_rf(scatterers, t_axis=None, workers=None):
    """
    Broadcast-transmit RF for all receive elements.

    Returns (rf, t_axis): rf has shape (N_ELEMENTS, len(t_axis)); t_axis is the
    real time axis [s] (starts < 0) and must be kept with rf downstream.
    workers: number of processes (default: all CPU cores for phantoms with at
    least PARALLEL_MIN scatterers, otherwise 1).
    """
    t_axis = config.get_t_axis() if t_axis is None else np.asarray(t_axis, dtype=float)
    scatterers = list(scatterers)
    if workers is None:
        workers = (os.cpu_count() or 1) if len(scatterers) >= PARALLEL_MIN else 1
    if workers <= 1:
        return _rf_sum((scatterers, t_axis)), t_axis
    n_chunks = 4 * workers
    chunks = [(scatterers[i::n_chunks], t_axis) for i in range(n_chunks)]
    try:
        with ProcessPoolExecutor(workers) as pool:
            rf = sum(pool.map(_rf_sum, chunks))
    except (BrokenProcessPool, OSError):
        # Worker processes could not start (e.g. code run from stdin): same result, one process.
        rf = sum(_rf_sum(c) for c in chunks)
    return rf, t_axis
