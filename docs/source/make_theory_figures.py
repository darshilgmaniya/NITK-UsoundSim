"""
make_theory_figures.py
======================

Figures for docs/NITK-UsoundSim_Theory_Guide.pdf. Every curve is computed from the
project's own config / code, or from the saved simulation results in results/*.npz
(run simulator/main.py first). Writes PNGs to docs/source/fig/ and prints the numbers
quoted in the guide.

    python3 docs/source/make_theory_figures.py      (from the project root)
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.signal import hilbert  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "simulator"))
import config  # noqa: E402
from nitk_usoundsim.acoustic_propagation import generate_pulse  # noqa: E402

OUT = Path(__file__).resolve().parent / "fig"
OUT.mkdir(exist_ok=True)
RES = ROOT / "results"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "figure.dpi": 100})
BLUE, ORANGE, GREEN, RED, GREY = "#1f5f99", "#e07b00", "#2a8a3e", "#c0392b", "#666666"
C, F0, FS, LAM, PITCH = config.C, config.F0, config.FS, config.LAMBDA, config.PITCH
NUM = {}


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- basics: wave and echo
fig, ax = plt.subplots(1, 2, figsize=(10, 3.2))
x = np.linspace(0, 4 * LAM, 800) * 1e3
ax[0].plot(x, np.sin(2 * np.pi * x / (LAM * 1e3)), color=BLUE)
ax[0].annotate("", xy=(LAM * 1e3, 1.15), xytext=(0, 1.15), arrowprops=dict(arrowstyle="<->", color=RED))
ax[0].text(LAM * 1e3 + 0.02, 1.15, f"wavelength λ = {LAM * 1e3:.3f} mm", ha="left", va="center", color=RED)
ax[0].set(ylim=(-1.3, 1.55), xlabel="distance (mm)", ylabel="pressure", title=f"A sound wave in tissue at {F0 / 1e6:g} MHz")
z = np.array([10, 20, 30]); t = 2 * z * 1e-3 / C * 1e6
ax[1].stem(t, [1, 0.8, 0.6], basefmt=" ")
for zi, ti in zip(z, t):
    ax[1].text(ti, 1.05, f"{zi} mm\n→ {ti:.1f} µs", ha="center", fontsize=9)
ax[1].set(xlim=(0, 45), ylim=(0, 1.35), xlabel="time after transmit (µs)", ylabel="echo strength",
          title="Echo time tells depth: t = 2z / c")
save(fig, "basics_wave_echo")
NUM["t_10_20_30"] = t

# ---------------------------------------------------------------- T1: array geometry
fig, ax = plt.subplots(figsize=(10, 2.6))
ex = config.get_element_positions() * 1e3
pw = PITCH * 1e3
for i, xi in enumerate(ex[:8]):
    ax.add_patch(plt.Rectangle((xi - pw / 2 + 0.006, 0), pw - 0.012, 0.6, color=BLUE, alpha=0.85))
    ax.text(xi, 0.3, str(i), color="white", ha="center", va="center", fontsize=9)
ax.annotate("", xy=(ex[1], 0.8), xytext=(ex[0], 0.8), arrowprops=dict(arrowstyle="<->", color=RED, lw=1.5, shrinkA=0, shrinkB=0))
ax.text((ex[0] + ex[1]) / 2, 0.9, f"pitch = {pw:.2f} mm", color=RED, ha="center")
ax.annotate("", xy=(ex[3] + pw / 2, -0.15), xytext=(ex[3] - pw / 2, -0.15), arrowprops=dict(arrowstyle="<->", color=GREEN, lw=1.5, shrinkA=0, shrinkB=0))
ax.text(ex[3], -0.32, f"width w = {config.ELEMENT_WIDTH * 1e3:.2f} mm", color=GREEN, ha="center", va="top")
ax.text(ex[7] + pw, 0.3, f"…  continues to element 127\n     (x = {ex[0]:.2f} … {ex[-1]:+.2f} mm, aperture {config.APERTURE * 1e3:.1f} mm)",
        va="center", fontsize=9.5)
ax.set(xlim=(ex[0] - 0.2, ex[0] + 5.2), ylim=(-0.6, 1.15), yticks=[], xlabel="x (mm)",
       title="Linear array: the first 8 of the 128 elements (no gap between elements assumed)")
ax.grid(False)
save(fig, "t1_array")

# ---------------------------------------------------------------- T1/T5: directivity and grating lobes
th = np.linspace(-90, 90, 721)
s = np.sin(np.deg2rad(th))
D = np.sinc(config.ELEMENT_WIDTH * s * F0 / C)
g_angle = np.degrees(np.arcsin(LAM / PITCH))
fnum_angle = np.degrees(np.arctan(1 / (2 * config.RX_F_NUMBER)))
fig, ax = plt.subplots(figsize=(8.5, 3.3))
ax.plot(th, 20 * np.log10(np.maximum(np.abs(D), 1e-4)), color=BLUE, label="element directivity  sinc(w·sinθ/λ)")
ax.axvspan(-fnum_angle, fnum_angle, color=GREEN, alpha=0.12, label=f"angles used with F# = 1 (±{fnum_angle:.1f}°)")
for sgn in (-1, 1):
    ax.axvline(sgn * g_angle, color=RED, ls="--")
ax.text(g_angle + 1, -35, f"grating-lobe angle\nsinθ = λ/pitch → {g_angle:.1f}°", color=RED, fontsize=9)
ax.set(ylim=(-45, 3), xlabel="angle from the element's axis θ (degrees)", ylabel="dB",
       title="How strongly one element sends/receives in each direction")
ax.legend(loc="lower left", fontsize=8.5)
save(fig, "t1_directivity")
NUM.update(grating_angle=g_angle, fnum_angle=fnum_angle,
           D_at_grating=20 * np.log10(abs(np.sinc(config.ELEMENT_WIDTH * LAM / PITCH * F0 / C))))

# ---------------------------------------------------------------- T2: pulse and spectrum
tp, p = generate_pulse(f0=F0)
sigma = 3 / (2 * F0)
fig, ax = plt.subplots(1, 2, figsize=(10, 3.2))
ax[0].plot(tp * 1e6, p, color=BLUE, label="pulse p(t)")
ax[0].plot(tp * 1e6, np.exp(-tp ** 2 / (2 * sigma ** 2)), color=ORANGE, ls="--", label="Gaussian envelope")
ax[0].set(xlabel="time (µs)", title=f"Transmit pulse: {F0 / 1e6:g} MHz, 3 cycles, {tp.size} samples at 40 MHz")
ax[0].legend(fontsize=8.5)
tt = np.arange(-4e-6, 4e-6, 1 / 1e9)
pp = np.sin(2 * np.pi * F0 * tt) * np.exp(-tt ** 2 / (2 * sigma ** 2))
f = np.fft.rfftfreq(tt.size, 1e-9); P = np.abs(np.fft.rfft(pp)); P /= P.max()
ax[1].plot(f / 1e6, 20 * np.log10(np.maximum(P, 1e-6)), color=BLUE)
ax[1].axvspan(config.F_MIN / 1e6, config.F_MAX / 1e6, color=GREEN, alpha=0.12, label="L12-4 range 4–12 MHz")
above = f[P >= 0.5]
ax[1].set(xlim=(0, 20), ylim=(-40, 3), xlabel="frequency (MHz)", ylabel="dB", title="Its frequency content (spectrum)")
ax[1].legend(fontsize=8.5)
save(fig, "t2_pulse_spectrum")
NUM.update(sigma_us=sigma * 1e6, bw_lo=above.min() / 1e6, bw_hi=above.max() / 1e6, pulse_n=tp.size)

# ---------------------------------------------------------------- T2: focusing delays geometry
xf, zf = 0.0, 0.020
d = np.hypot(xf - config.get_element_positions(), zf)
tau = (d.max() - d) / C
fig, ax = plt.subplots(1, 2, figsize=(10, 3.4))
for xi in config.get_element_positions()[::16]:
    ax[0].plot([xi * 1e3, xf * 1e3], [0, zf * 1e3], color=GREY, lw=0.8)
ax[0].plot(config.get_element_positions() * 1e3, np.zeros(128), "s", ms=2, color=BLUE)
ax[0].plot(xf * 1e3, zf * 1e3, "*", ms=14, color=RED)
ax[0].text(1, zf * 1e3, "focus (0, 20) mm", color=RED, va="center")
ax[0].set(ylim=(25, -2), xlabel="x (mm)", ylabel="depth z (mm)", title="Edge elements are farther from the focus")
ax[1].plot(config.get_element_positions() * 1e3, tau * 1e6, color=ORANGE)
ax[1].set(xlabel="element x (mm)", ylabel="transmit delay (µs)", title="So they fire first; the centre fires last")
save(fig, "t2_focus_delays")
NUM.update(tau_max_us=tau.max() * 1e6)

# ---------------------------------------------------------------- T2/T5: windows
n = np.arange(128)
fig, ax = plt.subplots(figsize=(7.5, 2.8))
ax.plot(n, np.ones(128), label="rectangular (no weighting)", color=GREY)
ax.plot(n, np.hamming(128), label="Hamming", color=GREEN)
ax.plot(n, np.hanning(128), label="Hann (used on receive)", color=BLUE)
ax.set(xlabel="element number", ylabel="weight", title="Apodization windows: how much each element counts")
ax.legend(fontsize=8.5, loc="lower center")
save(fig, "t2_windows")

# ---------------------------------------------------------------- T3: attenuation
zz = np.linspace(0, 40, 200)
fig, ax = plt.subplots(figsize=(7.5, 3.0))
for f0, col in ((4e6, GREEN), (8e6, BLUE), (12e6, RED)):
    ax.plot(zz, -2 * config.ALPHA_0 * f0 / 1e6 * zz / 10, color=col, label=f"{f0 / 1e6:g} MHz")
ax.set(xlabel="depth z (mm)", ylabel="round-trip loss (dB)",
       title=f"Attenuation: loss = 2 · α₀ · f · z,  α₀ = {config.ALPHA_0} dB/MHz/cm")
ax.legend(fontsize=8.5)
save(fig, "t3_attenuation")
NUM["att_8MHz_40mm"] = 2 * config.ALPHA_0 * 8 * 4

# ---------------------------------------------------------------- T3: sampling / interpolation
t_axis = config.get_t_axis()
tc = np.linspace(0, 3 / F0, 600)
ts = t_axis[(t_axis >= 0) & (t_axis <= 3 / F0)]
fig, ax = plt.subplots(figsize=(7.5, 2.8))
ax.plot(tc * 1e6, np.sin(2 * np.pi * F0 * tc), color=GREY, label="true signal")
ax.plot(ts * 1e6, np.sin(2 * np.pi * F0 * ts), "o-", color=BLUE, ms=4, label="samples at 40 MHz, joined by straight lines (np.interp)")
ax.set(xlabel="time (µs)", title=f"Sampling: fs = 40 MHz gives {FS / F0:g} samples per 8 MHz cycle")
ax.legend(fontsize=8.5, loc="lower left")
save(fig, "t3_sampling")

# ---------------------------------------------------------------- T4: speckle statistics (real data)
sc = np.load(RES / "scatterers.npz")
env = np.abs(hilbert(sc["beamformed"], axis=0))
zb = sc["z_axis"]
region = env[(zb >= 0.014) & (zb <= 0.016)]
v = region.ravel() / region.mean()
snr = region.mean() / region.std()
fig, ax = plt.subplots(1, 2, figsize=(10, 3.2))
ax[0].hist(v, bins=120, density=True, color=BLUE, alpha=0.6, label="our speckle (14–16 mm)")
s2 = np.sqrt(2 / np.pi)  # Rayleigh scale for mean 1
r = np.linspace(0, v.max(), 300)
ax[0].plot(r, r / s2 ** 2 * np.exp(-r ** 2 / (2 * s2 ** 2)), color=RED, label="Rayleigh theory")
ax[0].set(xlabel="envelope / mean", ylabel="probability density", title=f"Our speckle vs Rayleigh theory\n(mean/std = {snr:.2f}, theory 1.91)")
ax[0].legend(fontsize=8.5)
rng = np.random.default_rng(1)
ph = rng.uniform(0, 2 * np.pi, 12); a = rng.normal(0, 1, 12)
z = np.concatenate([[0], np.cumsum(a * np.exp(1j * ph))])
ax[1].plot(z.real, z.imag, "-o", ms=3, color=GREY)
ax[1].annotate("", xy=(z[-1].real, z[-1].imag), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color=RED, lw=2))
ax[1].set(aspect="equal", title="Why: many random echoes\nadd up to a random total", xlabel="real part", ylabel="imaginary part")
save(fig, "t4_speckle_stats")
NUM["speckle_snr_14_16"] = snr

# ---------------------------------------------------------------- T5: DAS alignment (real point-target RF)
pt = np.load(RES / "point_targets.npz")
rf, ta = pt["rf"], pt["t_axis"]
xe = config.get_element_positions()
xl, zl = 0.0, 0.020
tau_rx = np.hypot(xl - xe, zl) / C
tau_tx = np.hypot(xl - xe, zl).min() / C
w = (ta >= 22e-6) & (ta <= 32e-6)
al = np.array([np.interp(tau_tx + tau_rx[m] + ta[w] - 26e-6, ta, rf[m]) for m in range(128)])
v1 = np.percentile(np.abs(rf[:, w]), 99.5)
fig, ax = plt.subplots(1, 3, figsize=(11, 3.6))
ax[0].imshow(rf[:, w].T, aspect="auto", cmap="gray", vmin=-v1, vmax=v1, interpolation="none",
             extent=[0.5, 128.5, ta[w][-1] * 1e6, ta[w][0] * 1e6])
ax[0].set(title="1. raw echoes: a curve\n(edge elements hear it later)", xlabel="element", ylabel="time (µs)"); ax[0].grid(False)
ax[1].imshow(al.T, aspect="auto", cmap="gray", vmin=-v1, vmax=v1, interpolation="none",
             extent=[0.5, 128.5, ta[w][-1] * 1e6 - 26 + (tau_tx + tau_rx.min()) * 1e6, ta[w][0] * 1e6 - 26 + (tau_tx + tau_rx.min()) * 1e6])
ax[1].set(title="2. after the delays: a straight line\n(all elements line up)", xlabel="element"); ax[1].grid(False)
ax[1].set_yticks([])
wts = np.hanning(128)


def das_line(xline):
    """Hann-weighted delay-and-sum at depth 20 mm on one line (same delays as receive_beamforming)."""
    trx = np.hypot(xline - xe, zl) / C
    ttx = np.hypot(xline - xe, zl).min() / C
    tt = np.linspace(-1e-6, 1e-6, 400)
    vals = np.array([np.interp(ttx + trx[m] + tt, ta, rf[m]) for m in range(128)])
    return tt, (wts[:, None] * vals).sum(0) / wts.sum()


tt, on = das_line(0.0)
_, off = das_line(0.002)
ref = np.abs(on).max()
ax[2].plot(tt * 1e6, on / ref, color=RED, lw=1.5, label="line through the target (x = 0)")
ax[2].plot(tt * 1e6, off / ref, color=BLUE, lw=1.2, label="line 2 mm to the side")
ax[2].set(ylim=(-1.2, 1.5), title="3. weight and add: big where the\ntarget is, cancels elsewhere", xlabel="time around the target (µs)")
ax[2].legend(fontsize=7.5, loc="upper right")
NUM["das_off_on_ratio_db"] = 20 * np.log10(np.abs(off).max() / ref)
save(fig, "t5_das_alignment")

# ---------------------------------------------------------------- T5: dynamic aperture
zd = np.linspace(0, 40, 200)
half = np.maximum(zd / (2 * config.RX_F_NUMBER), 2 * PITCH * 1e3)
fig, ax = plt.subplots(figsize=(7.5, 2.9))
ax.fill_between(zd, -half, half, color=GREEN, alpha=0.25, label="active receive aperture (F# = 1)")
ax.axhline(config.APERTURE * 1e3 / 2, color=GREY, ls="--"); ax.axhline(-config.APERTURE * 1e3 / 2, color=GREY, ls="--")
ax.text(1, config.APERTURE * 1e3 / 2 + 0.8, "edge of the 38.4 mm array", color=GREY, fontsize=9)
ax.set(xlabel="depth z (mm)", ylabel="x around the scan line (mm)", ylim=(-22, 22),
       title="Dynamic aperture: width = depth / F#  (grows with depth)")
ax.legend(fontsize=8.5, loc="lower right")
save(fig, "t5_dynamic_aperture")

# ---------------------------------------------------------------- T5: point spread function (real)
b = pt["bmode"]; zb = pt["z_axis"]; xb = pt["x_lines"]
m = (np.abs(zb - 0.020) < 1.5e-3); c0 = np.argmin(np.abs(xb))
sub = b[m][:, np.abs(xb) < 1.5e-3]
fig, ax = plt.subplots(1, 3, figsize=(11.5, 3.2), gridspec_kw=dict(width_ratios=[1, 1.2, 1.2], wspace=0.35))
ax[0].imshow(sub, cmap="gray", extent=[-1.5, 1.5, 21.5, 18.5], vmin=0, vmax=1); ax[0].grid(False)
ax[0].set(title="target at (0, 20) mm", xlabel="x (mm)", ylabel="z (mm)")
env_pt = np.abs(hilbert(pt["beamformed"], axis=0))
row = env_pt[np.argmin(np.abs(zb - 0.020))]; col = env_pt[:, c0]
zz2 = zb[m] * 1e3; colm = col[m] / col[m].max()
ax[1].plot(zz2, 20 * np.log10(colm), color=BLUE); ax[1].axhline(-6, color=RED, ls="--")
ax[1].set(ylim=(-40, 2), xlabel="depth z (mm)", ylabel="dB", title="axial profile (along depth)")
xm = np.abs(xb) < 1.5e-3; rowm = row[xm] / row[xm].max()
ax[2].plot(xb[xm] * 1e3, 20 * np.log10(rowm), color=BLUE); ax[2].axhline(-6, color=RED, ls="--")
ax[2].set(ylim=(-40, 2), xlabel="x (mm)", title="lateral profile (across)")
save(fig, "t5_psf")

# ---------------------------------------------------------------- T6 recon: Hilbert envelope and log compression
bf = sc["beamformed"][:, 128]
zmm = sc["z_axis"] * 1e3
w = (zmm >= 15) & (zmm <= 17)
e = np.abs(hilbert(sc["beamformed"], axis=0))[:, 128]
fig, ax = plt.subplots(1, 2, figsize=(10, 3.2))
ax[0].plot(zmm[w], bf[w], color=GREY, lw=0.8, label="beamformed RF (wiggles at 8 MHz)")
ax[0].plot(zmm[w], e[w], color=RED, lw=2, label="envelope |RF + j·Hilbert(RF)|")
ax[0].set(xlabel="depth (mm)", title="Envelope detection: keep the outline, drop the wiggles"); ax[0].legend(fontsize=8)
ev = np.linspace(1e-4, 1, 500)
L = 20 * np.log10(ev); B = (np.clip(L, -50, 0) + 50) / 50
ax[1].plot(ev, B, color=BLUE, label="50 dB log compression")
ax[1].plot(ev, ev, color=GREY, ls="--", label="linear (no compression)")
ax[1].set(xlabel="envelope / max", ylabel="display brightness 0–1", title="Log compression lifts weak echoes")
ax[1].legend(fontsize=8.5, loc="lower right")
save(fig, "t6_envelope_log")

# ---------------------------------------------------------------- T7: scan conversion grid
fig, ax = plt.subplots(1, 2, figsize=(10, 3.2))
bm = sc["bmode"]
ax[0].imshow(bm[: int(np.argmin(np.abs(sc["z_axis"] - 0.040)))], cmap="gray", aspect="auto"); ax[0].grid(False)
ax[0].set(title=f"before: {bm.shape[0]} depth samples × {bm.shape[1]} lines\n(array index, 0.019 × 0.078 mm cells)",
          xlabel="scan line #", ylabel="depth sample #")
im = sc["image"]
ax[1].imshow(im, cmap="gray", extent=[sc["x_img"][0] * 1e3, sc["x_img"][-1] * 1e3, sc["z_img"][-1] * 1e3, sc["z_img"][0] * 1e3]); ax[1].grid(False)
ax[1].set(title=f"after: {im.shape[0]} × {im.shape[1]} square pixels\n(0.078 mm × 0.078 mm, real mm axes)", xlabel="x (mm)", ylabel="z (mm)")
save(fig, "t7_scan_conversion")

# ---------------------------------------------------------------- post-processing: guided filter concept (1-D)
rng = np.random.default_rng(3)
xx = np.arange(300)
clean = np.where((xx > 100) & (xx < 200), 0.25, 0.75)
noisy = np.clip(clean + rng.normal(0, 0.08, xx.size), 0, 1)


def gf1(I, r, eps):
    k = np.ones(2 * r + 1) / (2 * r + 1)
    box = lambda v: np.convolve(np.pad(v, r, mode="edge"), k, mode="valid")
    mI = box(I); var = box(I * I) - mI * mI
    a = var / (var + eps); bb = mI - a * mI
    return box(a) * I + box(bb)


fig, ax = plt.subplots(figsize=(8.5, 3.0))
ax.plot(xx, noisy, color=GREY, lw=0.7, label="noisy row (made-up example)")
ax.plot(xx, gf1(noisy, 8, 0.03), color=BLUE, lw=1.6, label="guided filter (r = 8, eps = 0.03)")
ax.plot(xx, np.convolve(np.pad(noisy, 8, mode="edge"), np.ones(17) / 17, mode="valid"), color=ORANGE, lw=1.2, ls="--", label="plain average (blurs the edges)")
ax.set(xlabel="pixel", ylabel="brightness", title="Guided filter idea: smooth flat areas, keep edges (1-D illustration)")
ax.legend(fontsize=8, loc="upper right")
save(fig, "post_guided_idea")

print("numbers used in the guide:")
for k, val in NUM.items():
    print(f"  {k}: {val}")
print(f"  lambda = {LAM * 1e3:.4f} mm, pitch/lambda = {PITCH / LAM:.3f}, dz = {C / (2 * FS) * 1e3:.4f} mm")
print(f"  axial FWHM theory = {C / 2 * 2.3548 * sigma * 1e3:.3f} mm")
print("figures in", OUT)
