"""Tissue interaction model for NITK-UsoundSim.

This module is intentionally a drop-in replacement for the existing
Acoustic Propagation placeholder::

    reflected_wave = mock_tissue_interaction(incident_wave, scatterer)

The propagation contract is preserved: one scatterer dictionary is supplied,
and a 1-D scattered pressure waveform with the same shape is returned.

The model is linear and point-scatterer based. It does not calculate TX/RX
travel time, attenuation, beamforming, RF demodulation, or B-mode formation.
Those responsibilities remain with the existing propagation/receive pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np


@dataclass(frozen=True)
class TissueProperties:
    """Acoustic properties used by the interaction model.

    Units
    -----
    impedance_mrayl : MRayl (10^6 kg m^-2 s^-1)
    background_impedance_mrayl : MRayl
    scatterer_amplitude : dimensionless signed local scattering strength
    """

    impedance_mrayl: float = 1.63
    background_impedance_mrayl: float = 1.63
    scatterer_amplitude: float = 1.0


def pressure_reflection_coefficient(z1_mrayl: float, z2_mrayl: float) -> float:
    """Return the normal-incidence pressure reflection coefficient.

    R = (Z2 - Z1) / (Z2 + Z1)

    The sign is retained because a negative pressure reflection coefficient
    represents phase inversion for a lower-impedance transition.
    """
    z1 = float(z1_mrayl)
    z2 = float(z2_mrayl)
    if not np.isfinite(z1) or not np.isfinite(z2) or z1 <= 0.0 or z2 <= 0.0:
        raise ValueError("Acoustic impedances must be finite and positive.")
    return float((z2 - z1) / (z2 + z1))


def _validate_amplitude(amp: float) -> float:
    value = float(amp)
    if not np.isfinite(value):
        raise ValueError("scatterer['amp'] must be finite.")
    return value


def interaction_gain(scatterer: Mapping[str, float]) -> float:
    """Return the dimensionless gain applied to the incident waveform.

    Required legacy field
    ---------------------
    ``amp`` is the local point-scatterer strength. If it is omitted, 1.0 is
    used, matching the preliminary module.

    Optional fields
    ---------------
    ``impedance_mrayl`` and ``background_impedance_mrayl`` can be supplied to
    modestly modulate the magnitude using ``1 + |R|``. This preserves the
    original test/interface behaviour and avoids treating every distributed
    scatterer as a macroscopic tissue boundary.

    ``interaction_scale`` is an optional dimensionless multiplier useful for
    lesion/background calibration. It changes the acoustic scatterer response,
    not the final image brightness.
    """
    amp = _validate_amplitude(scatterer.get("amp", 1.0))

    z_local = scatterer.get("impedance_mrayl")
    z_bg = scatterer.get("background_impedance_mrayl")
    impedance_factor = 1.0
    if z_local is not None:
        if z_bg is None:
            raise ValueError(
                "background_impedance_mrayl is required when impedance_mrayl is supplied."
            )
        r = pressure_reflection_coefficient(float(z_bg), float(z_local))
        impedance_factor = 1.0 + abs(r)

    scale = float(scatterer.get("interaction_scale", 1.0))
    if not np.isfinite(scale) or scale < 0.0:
        raise ValueError("scatterer['interaction_scale'] must be finite and non-negative.")

    return amp * impedance_factor * scale


def tissue_interaction(
    incident_wave: np.ndarray,
    scatterer: Mapping[str, float],
) -> np.ndarray:
    """Convert one incident pressure waveform into a scattered waveform.

    Interface contract
    ------------------
    input  : 1-D mechanical-pressure waveform, shape ``(n_samples,)``
    output : 1-D mechanical-pressure waveform, exactly the same shape

    No time shift, TX delay, RX delay, attenuation, beamforming, or image
    processing is applied here. The existing return-propagation module should
    continue to handle the scatterer-to-receiver path.
    """
    wave = np.asarray(incident_wave, dtype=float)
    if wave.ndim != 1:
        raise ValueError("incident_wave must be a 1-D waveform.")
    if not np.all(np.isfinite(wave)):
        raise ValueError("incident_wave must contain only finite values.")

    gain = interaction_gain(scatterer)
    out = gain * wave
    if not np.all(np.isfinite(out)):
        raise FloatingPointError("Tissue interaction produced non-finite values.")
    return out


# Exact legacy name expected by the current propagation code.
mock_tissue_interaction = tissue_interaction


__all__ = [
    "TissueProperties",
    "pressure_reflection_coefficient",
    "interaction_gain",
    "tissue_interaction",
    "mock_tissue_interaction",
]
