"""
parameter_tests.py
==================

Basic parameter tests (plan, 24 September): change frequency, TX focus depth,
attenuation, apodization and sampling frequency, and check that the image
changes the way the physics predicts.

    python3 tests/parameter_tests.py      # prints a table, saves results/parameter_tests.png

Each case simulates ONE point target with the same physics as main.py --
tissue_phantoms.point_echo() (T3 forward_propagation x element directivity ->
T4 tissue_interaction -> T3 return_propagation x directivity) -> das_beamform --
changing only the parameter under test (f0 / alpha0 / tau_tx are arguments;
T3's code is not modified). Probe: Philips L12-4 reference (128 elements,
0.30 mm pitch, 8 MHz). The target is
beamformed on a fine grid of 401 lines over x = -4..+4 mm (0.02 mm apart),
and the envelope gives:

    peak (x, z)      position of the envelope maximum
    level            peak envelope, dB re the reference case of that test
    axial / lateral  -6 dB full widths of the point-spread function
    sidelobe         highest lateral level outside the main lobe (first minima)

Predictions checked
-------------------
frequency    4 / 8 / 12 MHz (the L12-4's range and centre), simulated at
             fs = 128 MHz so every case has >= 10 samples per cycle: axial width =
             (C/2) * 2.355 * sigma, sigma = N_CYCLES/(2 f0) (T3's Gaussian pulse),
             i.e. proportional to 1/f0. Lateral width also shrinks as f0 rises:
             with the F# = 1 dynamic receive aperture it scales with lambda * F#.
             (A first version, run at fs = 40 MHz with the fixed full receive
             aperture, failed both frequency checks: 12 MHz axial +10 % from
             under-sampling, and lateral width stuck at 0.30 mm at 8 and 12 MHz
             because element directivity, not the array, limited the aperture.)
attenuation  level(30 mm) - level(10 mm) drops by 2 * alpha0 * f0 * 2 cm
             versus alpha0 = 0 (round trip, 20 mm extra depth, on axis).
TX focus     T2's delays (calculate_tx_delays) focused at z_f: the incident
             wave at the target (0, 20 mm) is strongest for z_f = 20 mm.
apodization  rect: narrowest main lobe, highest sidelobes; Hann: widest main
             lobe, lowest sidelobes; Hamming in between.
sampling     32 / 64 / 128 MHz (4 / 8 / 16 samples per 8 MHz cycle): same peak
             position (np.interp on the real t_axis, README Section 6). The
             level is NOT constant: linear interpolation is a low-pass filter and
             runs twice (T3's return path and the DAS lookup), so at 4 samples
             per cycle the peak is lower; the level must converge as fs rises.
             (A first version of this test expected a constant level and failed.)
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.signal import hilbert  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "simulator"))  # project modules
import config  # noqa: E402
import tissue_phantoms  # noqa: E402,F401  (puts T4 on sys.path)
from nitk_usoundsim.acoustic_propagation import N_CYCLES  # noqa: E402
from receive_beamforming import das_beamform  # noqa: E402

sys.path.insert(0, str(config.T2_DIR))
from src.beamformer import calculate_tx_delays  # noqa: E402  (T2's delay law, unmodified)

EX = config.get_element_positions()
LINES = np.linspace(-0.004, 0.004, 401)
FREQ_TEST_FS = 128e6  # >= 10 samples per cycle up to 12 MHz


def simulate(x, z, f0=config.F0, alpha0=config.ALPHA_0, tau_tx=None, fs=config.FS):
    """RF of one point target (tissue_phantoms.point_echo) with the given parameters. Returns (rf, t_axis)."""
    t = np.arange(config.T_START, config.T_END, 1.0 / fs)
    s = {"x": x, "z": z, "amp": 1.0}
    return tissue_phantoms.point_echo(s, t, f0=f0, alpha0=alpha0, tau_tx=tau_tx), t


def measure(rf, t, z_target, apodization=None):
    """Envelope of the beamformed target on the fine line grid, plus its PSF metrics."""
    bf, z = das_beamform(rf, EX, LINES, config, t_axis=t, apodization=apodization)
    win = np.abs(z - z_target) <= 0.003
    env, z = np.abs(hilbert(bf, axis=0))[win], z[win]
    i, j = np.unravel_index(env.argmax(), env.shape)
    ax_prof, lat_prof = env[:, j] / env[i, j], env.max(axis=0) / env[i, j]  # lateral: max over depth window

    def width(p, step):
        above = np.where(p >= 0.5)[0]
        return (above.max() - above.min() + 1) * step

    k = j  # main lobe = between the first local minima either side of the peak
    lo = k
    while lo > 0 and lat_prof[lo - 1] < lat_prof[lo]:
        lo -= 1
    hi = k
    while hi < lat_prof.size - 1 and lat_prof[hi + 1] < lat_prof[hi]:
        hi += 1
    side = np.concatenate([lat_prof[:lo], lat_prof[hi + 1:]])
    return dict(x=LINES[j], z=z[i], peak=env[i, j], axial=width(ax_prof, z[1] - z[0]),
                lateral=width(lat_prof, LINES[1] - LINES[0]),
                sidelobe=20 * np.log10(side.max()) if side.size else np.nan,
                lat_prof=lat_prof, ax_prof=ax_prof, z_prof=z - z[i])


def db(a, ref):
    return 20 * np.log10(a / ref)


def main():
    out = config.RESULTS_DIR
    out.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 4, figsize=(20, 4.5))
    ok_all = []

    def report(name, passed):
        ok_all.append(passed)
        print(f"  -> {'PASS' if passed else 'FAIL'}: {name}")

    # 1. Frequency -------------------------------------------------------
    print("\n1. Centre frequency (target (0, 20) mm)")
    res = {}
    for f0 in (4e6, 8e6, 12e6):
        m = measure(*simulate(0, 0.020, f0=f0, fs=FREQ_TEST_FS), 0.020)
        pred = config.C / 2 * 2.355 * N_CYCLES / (2 * f0)
        res[f0] = m
        print(f"   f0 {f0 / 1e6:3.1f} MHz: axial {m['axial'] * 1e3:.3f} mm (predicted {pred * 1e3:.3f}),"
              f" lateral {m['lateral'] * 1e3:.3f} mm, peak ({m['x'] * 1e3:+.2f}, {m['z'] * 1e3:.2f}) mm")
        axes[0].plot(m["z_prof"] * 1e3, m["ax_prof"], label=f"{f0 / 1e6:g} MHz")
    a = [res[f]["axial"] for f in (4e6, 8e6, 12e6)]
    lat = [res[f]["lateral"] for f in (4e6, 8e6, 12e6)]
    report("axial and lateral widths shrink as f0 rises", a[0] > a[1] > a[2] and lat[0] > lat[1] > lat[2])
    report("axial width within 10 % of (C/2)*2.355*sigma",
           all(abs(res[f]["axial"] / (config.C / 2 * 2.355 * N_CYCLES / (2 * f)) - 1) < 0.10 for f in res))
    axes[0].set(title="Frequency: axial profile at peak line", xlabel="z - z_peak (mm)", ylabel="normalised envelope",
                xlim=(-1.5, 1.5)); axes[0].legend()

    # 2. Attenuation -----------------------------------------------------
    print(f"\n2. Attenuation (on-axis targets at 10 and 30 mm, f0 = {config.F0/1e6:g} MHz)")
    ratio = {}
    for alpha0 in (0.0, 0.5, 1.0):
        p10 = measure(*simulate(0, 0.010, alpha0=alpha0), 0.010)["peak"]
        p30 = measure(*simulate(0, 0.030, alpha0=alpha0), 0.030)["peak"]
        ratio[alpha0] = db(p30, p10)
    for alpha0 in (0.5, 1.0):
        pred = -2 * alpha0 * config.F0 / 1e6 * 2.0
        meas = ratio[alpha0] - ratio[0.0]
        print(f"   alpha0 {alpha0:.1f} dB/MHz/cm: level(30 mm) - level(10 mm) = {ratio[alpha0]:6.2f} dB;"
              f" change vs alpha0 = 0: {meas:6.2f} dB (predicted {pred:6.2f})")
        report(f"alpha0 {alpha0}: extra loss within 1 dB of prediction", abs(meas - pred) < 1.0)
    print(f"   (alpha0 = 0: level(30) - level(10) = {ratio[0.0]:.2f} dB -- geometry only)")

    # 3. TX focus (T2's delays) -------------------------------------------
    print("\n3. TX focus depth, T2 calculate_tx_delays (target (0, 20) mm)")
    t = np.arange(config.T_START, config.T_END, 1.0 / config.FS)
    inc_peak = {}
    for zf in (None, 0.010, 0.020, 0.030):
        tau = np.zeros(config.N_ELEMENTS) if zf is None else calculate_tx_delays(EX, 0.0, zf, config.C)
        inc = tissue_phantoms.incident_wave({"x": 0.0, "z": 0.020}, t, tau_tx=tau)
        inc_peak[zf] = np.abs(hilbert(inc)).max()
    for zf, p in inc_peak.items():
        print(f"   focus {'broadcast' if zf is None else f'{zf * 1e3:.0f} mm':>9s}: incident peak at target"
              f" {db(p, inc_peak[None]):+6.2f} dB re broadcast")
    report("focus at the target depth (20 mm) gives the strongest incident wave",
           max(inc_peak, key=inc_peak.get) == 0.020)

    # 4. Apodization -----------------------------------------------------
    print("\n4. Receive apodization (target (0, 20) mm)")
    rf, t = simulate(0, 0.020)
    ap = {}
    for kind in ("rect", "hamming", "hann"):
        ap[kind] = m = measure(rf, t, 0.020, apodization=kind)
        print(f"   {kind:7s}: lateral -6 dB width {m['lateral'] * 1e3:.3f} mm, highest sidelobe {m['sidelobe']:6.1f} dB")
        axes[1].plot(LINES * 1e3, 20 * np.log10(np.maximum(m["lat_prof"], 1e-6)), label=kind)
    report("rect narrowest main lobe, Hann widest", ap["rect"]["lateral"] < ap["hamming"]["lateral"] <= ap["hann"]["lateral"])
    report("rect highest sidelobes, Hann/Hamming lower", ap["rect"]["sidelobe"] > max(ap["hann"]["sidelobe"], ap["hamming"]["sidelobe"]))
    axes[1].set(title="Apodization: lateral profile (max over depth)", xlabel="x (mm)", ylabel="dB", ylim=(-60, 2))
    axes[1].legend()

    # 5. Sampling frequency ---------------------------------------------
    print("\n5. Sampling frequency (target (+2, 25) mm)")
    sf = {}
    for fs in (32e6, 64e6, 128e6):
        sf[fs] = m = measure(*simulate(0.002, 0.025, fs=fs), 0.025)
        print(f"   fs {fs / 1e6:3.0f} MHz: peak ({m['x'] * 1e3:+.3f}, {m['z'] * 1e3:.3f}) mm, level {db(m['peak'], sf[32e6]['peak'] if fs != 32e6 else m['peak']):+.2f} dB re 32 MHz")
    zs = [sf[f]["z"] for f in sf]; ps = [sf[f]["peak"] for f in sf]
    report("peak depth identical within one depth sample (dz = 0.019 mm)", max(zs) - min(zs) <= config.DZ * 1.0001)
    d1, d2 = db(ps[1], ps[0]), db(ps[2], ps[1])
    print(f"   level change 32->64 MHz {d1:+.2f} dB, 64->128 MHz {d2:+.2f} dB (linear-interpolation loss shrinking)")
    report("level converges as fs rises (64->128 change smaller than 32->64, and < 1 dB)", abs(d2) < abs(d1) and abs(d2) < 1.0)

    # Figure panels 3-4: focus and attenuation summaries
    labels = ["broadcast", "10 mm", "20 mm", "30 mm"]
    axes[2].bar(labels, [db(inc_peak[k], inc_peak[None]) for k in (None, 0.010, 0.020, 0.030)], color="#2a78d6")
    axes[2].set(title="TX focus (T2 delays): incident peak at (0, 20) mm", ylabel="dB re broadcast")
    axes[3].bar(["0", "0.5", "1.0"], [ratio[a] for a in (0.0, 0.5, 1.0)], color="#2a78d6")
    axes[3].set(title="Attenuation: level(30 mm) - level(10 mm)", xlabel="alpha0 (dB/MHz/cm)", ylabel="dB")
    fig.tight_layout(); fig.savefig(out / "parameter_tests.png", dpi=110); plt.close(fig)

    print(f"\n{sum(ok_all)}/{len(ok_all)} checks passed. Figure: {out / 'parameter_tests.png'}")
    return 0 if all(ok_all) else 1


if __name__ == "__main__":
    sys.exit(main())
