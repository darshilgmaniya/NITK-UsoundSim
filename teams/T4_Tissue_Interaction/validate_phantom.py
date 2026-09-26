"""Create diagnostic validation plots for the Tissue Interaction module."""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

from phantom import LesionProperties, PhantomConfig, generate_liver_phantom
from tissue_interaction import tissue_interaction

OUT = Path("validation_plots")
OUT.mkdir(exist_ok=True)

lesion = LesionProperties(
    center_x_m=0.0,
    center_z_m=0.035,
    radius_x_m=0.007,
    radius_z_m=0.008,
    echo_class="hypoechoic",
)
cfg = PhantomConfig(seed=2026, scatterer_density_m2=120_000, lesion=lesion)
phantom = generate_liver_phantom(cfg)

x = np.array([s["x"] for s in phantom.scatterers], dtype=float)
z = np.array([s["z"] for s in phantom.scatterers], dtype=float)
a = np.array([s["amp"] for s in phantom.scatterers], dtype=float)
is_lesion = np.array([s["is_lesion"] for s in phantom.scatterers], dtype=bool)

# 1. Geometry
fig, ax = plt.subplots(figsize=(7, 6))
ax.scatter(x[~is_lesion] * 1e3, z[~is_lesion] * 1e3, s=3, alpha=0.35, label="background scatterers")
ax.scatter(x[is_lesion] * 1e3, z[is_lesion] * 1e3, s=5, alpha=0.6, label="lesion-region scatterers")
t = np.linspace(0, 2 * np.pi, 400)
ax.plot((lesion.center_x_m + lesion.radius_x_m * np.cos(t)) * 1e3,
        (lesion.center_z_m + lesion.radius_z_m * np.sin(t)) * 1e3,
        linewidth=2, label="lesion boundary")
ax.set(xlabel="Lateral x [mm]", ylabel="Depth z [mm]", title="2-D Acoustic Phantom Geometry")
ax.invert_yaxis(); ax.legend(); fig.tight_layout(); fig.savefig(OUT / "01_phantom_geometry.png", dpi=180); plt.close(fig)

# 2. Amplitude distribution
fig, ax = plt.subplots(figsize=(7, 4.5))
ax.hist(a[~is_lesion], bins=50, alpha=0.65, label="background")
if np.any(is_lesion):
    ax.hist(a[is_lesion], bins=30, alpha=0.65, label="lesion region")
ax.set(xlabel="Signed scatterer amplitude", ylabel="Count", title="Scatterer Amplitude Distribution")
ax.legend(); fig.tight_layout(); fig.savefig(OUT / "02_scatterer_amplitudes.png", dpi=180); plt.close(fig)

# 3. Example waveform
fs = 40e6
n = 256
t_s = np.arange(n) / fs
f0 = 5e6
window = np.exp(-((t_s - 3.0 / f0) / (1.2 / f0)) ** 2)
incident = np.sin(2 * np.pi * f0 * t_s) * window
scatterer = phantom.scatterers[len(phantom.scatterers) // 2]
scattered = tissue_interaction(incident, scatterer)
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(t_s * 1e6, incident, label="incident")
ax.plot(t_s * 1e6, scattered, label="scattered")
ax.set(xlabel="Time [µs]", ylabel="Relative pressure amplitude", title="Example Incident / Scattered Waveform")
ax.legend(); fig.tight_layout(); fig.savefig(OUT / "03_waveform.png", dpi=180); plt.close(fig)

# 4. Background vs lesion-region scattering strength map (diagnostic only)
fig, ax = plt.subplots(figsize=(7, 6))
sc = ax.scatter(x * 1e3, z * 1e3, c=np.abs(a), s=4)
ax.plot((lesion.center_x_m + lesion.radius_x_m * np.cos(t)) * 1e3,
        (lesion.center_z_m + lesion.radius_z_m * np.sin(t)) * 1e3,
        linewidth=2)
fig.colorbar(sc, ax=ax, label="|scatterer amplitude|")
ax.set(xlabel="Lateral x [mm]", ylabel="Depth z [mm]", title="Acoustic Scatterer Strength (Not a B-mode Image)")
ax.invert_yaxis(); fig.tight_layout(); fig.savefig(OUT / "04_scattering_strength_map.png", dpi=180); plt.close(fig)

print(f"Generated {phantom.num_scatterers} scatterers")
print(f"Lesion-region scatterers: {int(is_lesion.sum())}")
print(f"Plots written to: {OUT.resolve()}")
