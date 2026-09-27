"""
Makes the two simulated input files used by the last cells of B_mode.ipynb (this folder):

    reconstructed_cyst_lesion.npz     6 mm anechoic cyst at 30 mm depth in speckle
    reconstructed_point_targets.npz   3 point targets at 10 / 20 / 30 mm depth

Chain: Teams 1-5 of the simulator (phantom -> propagation -> tissue -> RX delay-and-sum,
as in simulator/main.py run() up to das_beamform) -> the image-reconstruction steps from
B_mode.ipynb (Hilbert envelope, normalise to the peak, 20*log10). Keys: rf, envelope,
envelope_norm, envelope_db, fs, f0, c, pitch, depth_start_mm, plus the real axes
depth_mm and width_mm.

The .npz files are already in this folder. To remake them (about 13 minutes):
    python3 make_simulated_inputs.py
"""
import sys
from pathlib import Path

import numpy as np
from scipy.signal import hilbert

project = Path(__file__).resolve().parents[3]          # repository root
sys.path.insert(0, str(project / "simulator"))

import config  # noqa: E402  (the simulator's settings; puts the team folders on the path)
from receive_beamforming import das_beamform  # noqa: E402  (Team 5)
from tissue_phantoms import build_phantom, simulate_rf  # noqa: E402  (Teams 1-4)

OUT = Path(__file__).resolve().parent                # this folder
Z_SHOW_MM = 40.0                        # same depth window as the simulator's images (0-40 mm)


def main():
    for kind in ("cyst_lesion", "point_targets"):
        rf_el, t_axis = simulate_rf(build_phantom(kind))
        x_lines = config.get_scanline_positions()
        beamformed, z_axis = das_beamform(rf_el, config.get_element_positions(), x_lines, config, t_axis=t_axis)
        keep = z_axis * 1e3 <= Z_SHOW_MM + 1e-9
        rf = beamformed[keep].astype(np.float32)                 # (depth samples, scan lines)

        # image-reconstruction steps, same formulas as B_mode.ipynb code cells 3 and 5 (first half)
        envelope = np.abs(hilbert(rf, axis=0)).astype(np.float32)
        envelope_norm = (envelope / np.max(envelope)).astype(np.float32)
        envelope_db = (20 * np.log10(envelope_norm + 1e-12)).astype(np.float32)

        path = OUT / f"reconstructed_{kind}.npz"
        np.savez(path, rf=rf, envelope=envelope, envelope_norm=envelope_norm, envelope_db=envelope_db,
                 fs=float(config.FS), f0=float(config.F0), c=float(config.C),
                 pitch=float(x_lines[1] - x_lines[0]), depth_start_mm=float(z_axis[0] * 1e3),
                 depth_mm=(z_axis[keep] * 1e3).astype(np.float64), width_mm=(x_lines * 1e3).astype(np.float64))
        print(f"{path.name}: rf {rf.shape}, depth {z_axis[keep][0]*1e3:.2f}-{z_axis[keep][-1]*1e3:.2f} mm, "
              f"width {x_lines[0]*1e3:.2f}..{x_lines[-1]*1e3:.2f} mm, envelope_db {envelope_db.min():.1f}..0 dB")


if __name__ == "__main__":   # needed: simulate_rf() uses worker processes
    main()
