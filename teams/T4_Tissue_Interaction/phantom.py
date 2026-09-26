"""Deterministic 2-D liver-like acoustic phantom generation for NITK-UsoundSim.

The phantom is an acoustic-domain representation. It contains distributed
point scatterers and an optional geometrical lesion. It does not create or
modify a B-mode image.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np


LesionEchoClass = Literal["hypoechoic", "isoechoic", "hyperechoic"]


@dataclass(frozen=True)
class LesionProperties:
    """Geometrical and acoustic/scattering properties of a focal lesion."""

    center_x_m: float = 0.0
    center_z_m: float = 0.030
    radius_x_m: float = 0.006
    radius_z_m: float = 0.006
    echo_class: LesionEchoClass = "hypoechoic"
    scattering_scale: float | None = None
    impedance_mrayl: float | None = None

    def __post_init__(self) -> None:
        if self.radius_x_m <= 0 or self.radius_z_m <= 0:
            raise ValueError("Lesion radii must be positive.")
        if self.echo_class not in {"hypoechoic", "isoechoic", "hyperechoic"}:
            raise ValueError("echo_class must be hypoechoic, isoechoic, or hyperechoic.")
        if self.scattering_scale is not None and self.scattering_scale < 0:
            raise ValueError("scattering_scale must be non-negative.")
        if self.impedance_mrayl is not None and self.impedance_mrayl <= 0:
            raise ValueError("impedance_mrayl must be positive.")


@dataclass(frozen=True)
class PhantomConfig:
    """Configuration for the 2-D synthetic liver phantom.

    All spatial quantities are SI metres. ``scatterer_density_m2`` is an
    intentionally synthetic simulation parameter, not a claim about human
    liver microstructure.
    """

    x_min_m: float = -0.025
    x_max_m: float = 0.025
    z_min_m: float = 0.010
    z_max_m: float = 0.060
    scatterer_density_m2: float = 120_000.0
    background_impedance_mrayl: float = 1.63
    background_scatter_std: float = 1.0
    seed: int = 2026
    lesion: LesionProperties | None = None

    def __post_init__(self) -> None:
        if self.x_max_m <= self.x_min_m or self.z_max_m <= self.z_min_m:
            raise ValueError("Phantom bounds must have positive extent.")
        if self.scatterer_density_m2 < 0:
            raise ValueError("scatterer_density_m2 must be non-negative.")
        if self.background_impedance_mrayl <= 0:
            raise ValueError("background_impedance_mrayl must be positive.")
        if self.background_scatter_std < 0:
            raise ValueError("background_scatter_std must be non-negative.")


@dataclass
class Phantom2D:
    """Generated acoustic phantom and propagation-facing scatterer list."""

    x_min_m: float
    x_max_m: float
    z_min_m: float
    z_max_m: float
    background_impedance_mrayl: float
    seed: int
    scatterers: list[dict[str, float | str | bool]]
    lesion: LesionProperties | None

    @property
    def num_scatterers(self) -> int:
        return len(self.scatterers)

    def as_legacy_scatterers(self) -> list[dict[str, float]]:
        """Return only the fields needed by the existing propagation code.

        The current propagation README says a scatterer contains at least
        ``x``, ``z`` and ``amp``. Extra metadata may safely be retained in the
        richer list, but this helper provides a clean legacy view.
        """
        return [
            {"x": float(s["x"]), "z": float(s["z"]), "amp": float(s["amp"])}
            for s in self.scatterers
        ]


def _inside_ellipse(x: np.ndarray, z: np.ndarray, lesion: LesionProperties) -> np.ndarray:
    qx = (x - lesion.center_x_m) / lesion.radius_x_m
    qz = (z - lesion.center_z_m) / lesion.radius_z_m
    return qx * qx + qz * qz <= 1.0


def _lesion_scale(lesion: LesionProperties, background_std: float) -> float:
    if lesion.scattering_scale is not None:
        return float(lesion.scattering_scale)
    if lesion.echo_class == "hypoechoic":
        return 0.35
    if lesion.echo_class == "isoechoic":
        return 1.0
    return 1.8


def generate_liver_phantom(config: PhantomConfig = PhantomConfig()) -> Phantom2D:
    """Generate a reproducible liver-like distributed point-scatterer phantom.

    Scatterer positions are uniform in the rectangular imaging region.
    Signed scatterer amplitudes are sampled from a zero-mean Gaussian. The
    lesion changes the local scattering-strength scale and can optionally
    carry a local impedance for the tissue interaction adapter.
    """
    rng = np.random.default_rng(config.seed)
    area_m2 = (config.x_max_m - config.x_min_m) * (config.z_max_m - config.z_min_m)
    n = int(np.round(config.scatterer_density_m2 * area_m2))

    x = rng.uniform(config.x_min_m, config.x_max_m, n)
    z = rng.uniform(config.z_min_m, config.z_max_m, n)
    amp = rng.normal(0.0, config.background_scatter_std, n)

    inside = np.zeros(n, dtype=bool)
    if config.lesion is not None and n:
        inside = _inside_ellipse(x, z, config.lesion)
        amp[inside] *= _lesion_scale(config.lesion, config.background_scatter_std)

    scatterers: list[dict[str, float | str | bool]] = []
    for i in range(n):
        item: dict[str, float | str | bool] = {
            "x": float(x[i]),
            "z": float(z[i]),
            "amp": float(amp[i]),
            "background_impedance_mrayl": float(config.background_impedance_mrayl),
            "is_lesion": bool(inside[i]),
        }
        if inside[i] and config.lesion is not None and config.lesion.impedance_mrayl is not None:
            item["impedance_mrayl"] = float(config.lesion.impedance_mrayl)
        scatterers.append(item)

    return Phantom2D(
        x_min_m=config.x_min_m,
        x_max_m=config.x_max_m,
        z_min_m=config.z_min_m,
        z_max_m=config.z_max_m,
        background_impedance_mrayl=config.background_impedance_mrayl,
        seed=config.seed,
        scatterers=scatterers,
        lesion=config.lesion,
    )


__all__ = ["LesionProperties", "PhantomConfig", "Phantom2D", "generate_liver_phantom"]
