"""
main.py
=======

NITK-UsoundSim end-to-end run: phantom in, B-mode image out.

    python3 simulator/main.py                  # all three phantoms (run from the project root)
    python3 simulator/main.py point_targets    # one or more of: point_targets scatterers cyst_lesion
    python3 simulator/main.py --out results    # output folder (default: the project's results/)

Pipeline (one broadcast transmit; see README Sections 2 and 5):

    build_phantom(kind)                      tissue_phantoms  (T4 phantom.py for speckle/cyst)
      -> simulate_rf(scatterers)             T3 forward -> T4 tissue_interaction -> T3 return
      -> das_beamform(rf, ...)               T5 receive DAS, dynamic focus, np.interp on real t_axis
      -> bmode_formation(beamformed)         T6 Hilbert envelope + log compression (DYNAMIC_RANGE_DB)
      -> scan_convert(bmode, x, z)           T7 rectangular resample to display pixels (0-Z_MAX)
      -> postprocess(image)                  T7 guided-filter despeckling

For each phantom it saves <kind>.png (B-mode before/after post-processing,
mm axes), <kind>_final_bmode.npy (the final image array, depth x lateral,
[0, 1]) and <kind>.npz (every intermediate array), prints the checks below,
and writes final_bmode.png with the final images of all phantoms side by side.

Checks printed
--------------
point_targets : measured peak position and level of each target.
scatterers    : speckle index (SI) before / after post-processing.
cyst_lesion   : lesion vs surrounding-ring contrast (dB), CNR, gCNR, SI,
                edge sharpness, before / after post-processing.
"""

import argparse
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import config  # noqa: E402
from bmode_formation import bmode_formation  # noqa: E402
from post_processing import (  # noqa: E402
    cnr, edge_sharpness, gcnr, lesion_ring, postprocess, scan_convert, speckle_index, to_uint8,
)
from receive_beamforming import das_beamform  # noqa: E402
from tissue_phantoms import KINDS, POINT_TARGETS, build_phantom, simulate_rf  # noqa: E402


def run(kind):
    """Full chain for one phantom; returns a dict of every stage's output."""
    t0 = time.time()
    scatterers = build_phantom(kind)
    rf, t_axis = simulate_rf(scatterers)
    t1 = time.time()
    x_lines = config.get_scanline_positions()
    beamformed, z_axis = das_beamform(rf, config.get_element_positions(), x_lines, config, t_axis=t_axis)
    bmode = bmode_formation(beamformed)
    image, x_img, z_img = scan_convert(bmode, x_lines, z_axis)
    final = postprocess(image)
    print(f"\n[{kind}] {len(scatterers)} scatterers | simulate_rf {t1 - t0:.1f} s, rest {time.time() - t1:.1f} s"
          f" | bmode {bmode.shape} -> image {image.shape} ({(x_img[1] - x_img[0]) * 1e3:.3f} mm/px)")
    return dict(kind=kind, rf=rf, t_axis=t_axis, beamformed=beamformed, z_axis=z_axis, x_lines=x_lines,
                bmode=bmode, image=image, final=final, x_img=x_img, z_img=z_img)


def check(res):
    """Print the per-phantom checks listed in the module docstring."""
    kind, dr = res["kind"], config.DYNAMIC_RANGE_DB
    if kind == "point_targets":
        b, x, z = res["bmode"], res["x_lines"], res["z_axis"]
        for p in POINT_TARGETS:
            m = np.ix_(np.abs(z - p["z"]) <= 1e-3, np.abs(x - p["x"]) <= 1e-3)
            sub = b[m]; i, j = np.unravel_index(sub.argmax(), sub.shape)
            zi = np.where(np.abs(z - p["z"]) <= 1e-3)[0][i]; xj = np.where(np.abs(x - p["x"]) <= 1e-3)[0][j]
            print(f"  target ({p['x'] * 1e3:+.0f}, {p['z'] * 1e3:.0f}) mm -> peak ({x[xj] * 1e3:+.2f}, {z[zi] * 1e3:.2f}) mm,"
                  f" {dr * (sub.max() - 1):6.2f} dB re frame peak")
        return
    before, after = to_uint8(res["image"]), to_uint8(res["final"])
    print(f"  speckle index SI: before {speckle_index(before):.3f}, after {speckle_index(after):.3f}")
    if kind == "cyst_lesion":
        zz, xx = np.meshgrid(res["z_img"], res["x_img"], indexing="ij")
        lesion = ((xx - config.LESION_CENTER_X) / config.LESION_RADIUS_X) ** 2 + \
                 ((zz - config.LESION_CENTER_Z) / config.LESION_RADIUS_Z) ** 2 <= 1
        ring = lesion_ring(lesion)
        for name, img, u8 in (("before", res["image"], before), ("after", res["final"], after)):
            contrast = dr * (img[lesion].mean() - img[ring].mean())
            print(f"  lesion {name:6s}: mean displayed level lesion - ring {contrast:6.2f} dB | CNR {cnr(u8, lesion):.3f}"
                  f" | gCNR {gcnr(u8, lesion):.3f} | edge {edge_sharpness(u8, lesion):.1f}")


def plot(res, path):
    ext = [res["x_img"][0] * 1e3, res["x_img"][-1] * 1e3, res["z_img"][-1] * 1e3, res["z_img"][0] * 1e3]
    fig, ax = plt.subplots(1, 2, figsize=(7, 9))
    for a, img, title in zip(ax, (res["image"], res["final"]), ("B-mode (scan-converted)", "post-processed (guided)")):
        im = a.imshow(img, cmap="gray", vmin=0, vmax=1, extent=ext)
        a.set_title(f"{res['kind']}\n{title}", fontsize=10); a.set_xlabel("lateral x (mm)"); a.set_ylabel("depth z (mm)")
    fig.colorbar(im, ax=ax, fraction=0.04, label=f"brightness (0 = -{config.DYNAMIC_RANGE_DB:g} dB, 1 = 0 dB)")
    fig.savefig(path, dpi=120, bbox_inches="tight"); plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    ap.add_argument("kinds", nargs="*", metavar="kind", help=f"any of {', '.join(KINDS)} (default: all)")
    ap.add_argument("--out", default=str(config.RESULTS_DIR))
    args = ap.parse_args(argv)
    kinds = args.kinds or list(KINDS)
    bad = [k for k in kinds if k not in KINDS]
    if bad:
        ap.error(f"unknown phantom kind(s) {bad}; choose from {list(KINDS)}")
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

    results = []
    for kind in kinds:
        res = run(kind)
        check(res)
        plot(res, out / f"{kind}.png")
        np.save(out / f"{kind}_final_bmode.npy", res["final"])
        np.savez_compressed(out / f"{kind}.npz", **{k: v for k, v in res.items() if k != "kind"})
        results.append(res)

    fig, ax = plt.subplots(1, len(results), figsize=(3.2 * len(results), 9), squeeze=False)
    for a, res in zip(ax[0], results):
        ext = [res["x_img"][0] * 1e3, res["x_img"][-1] * 1e3, res["z_img"][-1] * 1e3, res["z_img"][0] * 1e3]
        a.imshow(res["final"], cmap="gray", vmin=0, vmax=1, extent=ext)
        a.set_title(res["kind"], fontsize=10); a.set_xlabel("x (mm)"); a.set_ylabel("z (mm)")
    fig.suptitle(f"NITK-UsoundSim final images ({config.DYNAMIC_RANGE_DB:g} dB, guided despeckle)")
    fig.savefig(out / "final_bmode.png", dpi=120, bbox_inches="tight"); plt.close(fig)
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    sys.exit(main())
