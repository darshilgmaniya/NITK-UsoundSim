"""
config.py
=========

Unified configuration for the NITK-UsoundSim integration (single source of truth).

The medium and display constants are IMPORTED from T3's ``nitk_usoundsim/config.py``
rather than copied. The PROBE is the Philips L12-4 (FUS4103) reference model and
overrides T3's 64-element / 5 MHz defaults (see "Probe" below). This file also adds:

  - function-style wrappers / aliases expected by T5's verify_beamformer.py
  - the RF time axis and beamforming depth axis (T3 convention, deep enough
    for T5's z = 55 mm test)
  - broadcast-transmit settings (T2 bypassed, see README Section 4)
  - speckle-phantom settings passed to T4's PhantomConfig

Units: metres, seconds, Hz (same as T3).
"""

import sys
from pathlib import Path

import numpy as np

# Project layout: simulator/ (config.py + main.py, the integration), teams/
# (each team's folder: its original code plus its pipeline-stage module),
# tests/, docs/, results/.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEAMS_DIR = PROJECT_ROOT / "teams"
RESULTS_DIR = PROJECT_ROOT / "results"
T2_DIR = TEAMS_DIR / "T2_TX_Beamforming" / "Usound"
T4_DIR = TEAMS_DIR / "T4_Tissue_Interaction"
T5_DIR = TEAMS_DIR / "T5_RX_Beamforming"
T6_DIR = TEAMS_DIR / "T6_B_mode"
T7_DIR = TEAMS_DIR / "T7_Image_Recon_Post_Processing"

# Make T3's package and every team's pipeline-stage module importable:
# T4 tissue_phantoms.py, T5 receive_beamforming.py + mock_data.py,
# T6 bmode_formation.py, T7 post_processing.py.
_T3_DIR = TEAMS_DIR / "T3_Acoustic_Propagation" / "usound_sim"
for _d in (_T3_DIR, T4_DIR, T5_DIR, T6_DIR, T7_DIR):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

# ----------------------------------------------------------------------
# Source of truth: T3's flat constants (re-exported unchanged)
# ----------------------------------------------------------------------
from nitk_usoundsim.config import (  # noqa: E402
    ALPHA_0,
    C,
    DYNAMIC_RANGE_DB,
    FS,
    OUTPUT_SIZE,
    PHANTOM_POINTS,
    Z_MAX,
    Z_MIN,
)
from nitk_usoundsim.acoustic_propagation import (  # noqa: E402
    create_linear_array,
    generate_pulse,
)

# ----------------------------------------------------------------------
# Probe: Philips L12-4 (FUS4103) reference model
# ----------------------------------------------------------------------
# Philips publishes 128 elements and a 4-12 MHz operating range. Pitch and
# centre frequency are not published, so T2's documented assumptions are used
# (teams/T2_TX_Beamforming/Usound/config/transducer_interface.json:
# pitch 0.30 mm, centre 8 MHz). T3's functions default to T3's own 5 MHz, so
# every call passes f0=config.F0 explicitly (T3's code is not modified).
PROBE_NAME = "Philips L12-4 (FUS4103) reference model"
N_ELEMENTS = 128
PITCH = 0.30e-3                  # [m]; aperture 128 x 0.30 mm = 38.4 mm
F0 = 8.0e6                       # centre frequency [Hz]
F_MIN, F_MAX = 4.0e6, 12.0e6     # published operating range [Hz]
LAMBDA = C / F0                  # 0.1925 mm; the pitch is 1.56 lambda (not lambda/2)
APERTURE = N_ELEMENTS * PITCH

# ----------------------------------------------------------------------
# Aliases expected by T5's verify_beamformer.py
# ----------------------------------------------------------------------
SPEED_OF_SOUND = C
SAMPLING_FREQUENCY = FS


def get_element_positions():
    """Element x-positions [m], shape (N_ELEMENTS,), centred on 0, z = 0 implied (T3 geometry)."""
    return create_linear_array(N_ELEMENTS, PITCH)


# Imaged lateral FOV: +/-10 mm, well inside the +/-19.2 mm aperture, so every
# line is formed under the array (with the 64-element / 9.9 mm array the image
# had to be limited to +/-5 mm because of the transmit edge wave).
SCANLINE_X_MIN, SCANLINE_X_MAX = -0.010, 0.010
N_SCANLINES = 256                # 0.078 mm line spacing (lateral resolution ~0.2 mm)


def get_scanline_positions():
    """Scan-line x-positions [m], shape (N_SCANLINES,), evenly spanning SCANLINE_X_MIN..SCANLINE_X_MAX."""
    return np.linspace(SCANLINE_X_MIN, SCANLINE_X_MAX, N_SCANLINES)


# ----------------------------------------------------------------------
# RF time axis and beamforming depth axis
# ----------------------------------------------------------------------
# Z_MAX (40 mm) stays the displayed imaging depth. RF is recorded deeper,
# because T5's test 4 checks a point target at z = 55 mm.
Z_RF_MAX = 0.060

# T3 convention: t = 0 is the TX pulse centre, and the axis starts one pulse
# half-width earlier (t_axis[0] = -0.75 us at 8 MHz). Anything that looks up a
# time in the RF must use this axis, never sample_index / FS.
_PULSE_T, _ = generate_pulse(f0=F0)
T_START = -_PULSE_T[-1]

# Longest broadcast round trip: farthest element -> deepest, most lateral point -> back.
_X_FAR = 0.012                   # phantom half-width (PHANTOM_X_MAX below)
_D_FAR = np.hypot(_X_FAR + N_ELEMENTS * PITCH / 2, Z_RF_MAX)
T_END = 2 * _D_FAR / C + _PULSE_T[-1]

DZ = C / (2 * FS)  # depth step of one RF sample [m]


def get_t_axis():
    """RF time axis [s], T3 convention (starts at T_START < 0), sampled at FS."""
    return np.arange(T_START, T_END, 1.0 / FS)


def get_depth_axis():
    """Beamforming depth axis [m], Z_MIN..Z_RF_MAX in steps of DZ."""
    return np.arange(Z_MIN, Z_RF_MAX + DZ / 2, DZ)


# ----------------------------------------------------------------------
# Transmit: single broadcast shot (T2 bypassed; T3 used unmodified)
# ----------------------------------------------------------------------
TX_FOCUS_Z = None  # broadcast, no TX focus. parameter_tests.py tests T2's focused delays separately.


def get_tx_delays():
    """Per-element TX delays [s] for T3's tau_tx hook: all zero (broadcast)."""
    return np.zeros(N_ELEMENTS)


# ----------------------------------------------------------------------
# Receive beamforming
# ----------------------------------------------------------------------
RX_APODIZATION = "hann"  # das_beamform() aperture window: "hann" | "hamming" | "rect"
RX_F_NUMBER = 1.0        # dynamic receive aperture z / F#; None = fixed full aperture (see receive_beamforming.py)


# ----------------------------------------------------------------------
# Plan Section 5 parameters that T3's engine does not use, recorded here so
# they have one home and no module hard-codes a different value.
# ----------------------------------------------------------------------
ELEMENT_WIDTH = PITCH            # no kerf assumed; used by the element directivity below

# Element directivity. T3 models every element as a point that sends and
# receives equally in all directions. With the L12-4's coarse pitch
# (0.30 mm = 1.56 lambda at 8 MHz) that lets far, steep-angle elements add
# late "grating" arrivals: ghosts only -11 to -13 dB below each point target.
# A real element of width w is directional; the standard far-field factor of a
# rectangular element (as in Field II), sinc(w sin(theta) / lambda), is applied
# on transmit and on receive by tissue_phantoms.point_echo() (T3 unmodified).
# It lowers those ghosts to -21 to -34 dB.
ELEMENT_DIRECTIVITY = True
ELEMENT_HEIGHT = None            # elevation not modelled (2-D simulation)
BACKGROUND_IMPEDANCE_MRAYL = 1.63  # T4's default (tissue_interaction.py / phantom.py)
DENSITY = BACKGROUND_IMPEDANCE_MRAYL * 1e6 / C  # ~1058 kg/m^3, from Z = rho * c; informational


# ----------------------------------------------------------------------
# Speckle / cyst phantom settings (passed to T4's PhantomConfig)
# ----------------------------------------------------------------------
PHANTOM_SEED = 2026              # T4's default seed
PHANTOM_DENSITY_M2 = 1.0e8       # scatterers per m^2 (see README: chosen for fully developed speckle at 8 MHz)
PHANTOM_X_MIN, PHANTOM_X_MAX = -_X_FAR, _X_FAR   # tissue continues 2 mm beyond the imaged lines
PHANTOM_Z_MIN, PHANTOM_Z_MAX = Z_MIN, Z_MAX

# Cyst / lesion at T4's default position and size (30 mm depth, 6 mm radius),
# anechoic: scattering scale 0.0, i.e. a fluid-filled cyst (T4's hypoechoic
# default is 0.35; None -> T4's default for the echo class).
LESION_CENTER_X, LESION_CENTER_Z = 0.0, 0.030
LESION_RADIUS_X, LESION_RADIUS_Z = 0.006, 0.006
LESION_ECHO_CLASS = "hypoechoic"
LESION_SCATTERING_SCALE = 0.0
