"""
verify_beamformer.py
=====================
Runs the four T5 verification tests against mock point-target data:

  1. Point-target focusing      (Section 22)
  2. Correct vs incorrect delay (Section 23)
  3. Lateral localization       (Section 24)
  4. Depth localization         (Section 25)

Run:  python3 verify_beamformer.py
"""

import numpy as np

import config
from mock_data import generate_point_target_rf, generate_two_point_targets_rf
from receive_beamforming import das_beamform


def report(label, passed):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {label}")


def test_1_point_target_focusing():
    print("\n--- Test 1: Point-target focusing ---")
    element_positions = config.get_element_positions()
    x_target, z_target = 0.0, 0.03  # on-axis, 3 cm deep

    rf, _ = generate_point_target_rf(x_target, z_target, element_positions, config)
    scanline_positions = np.array([x_target])  # beamform straight at the target

    beamformed, z_axis = das_beamform(rf, element_positions, scanline_positions, config)

    peak_idx = np.argmax(np.abs(beamformed))
    z_peak = z_axis[peak_idx]
    error_mm = abs(z_peak - z_target) * 1000

    print(f"  expected depth: {z_target*1000:.2f} mm, measured peak: {z_peak*1000:.2f} mm "
          f"(error {error_mm:.3f} mm)")
    dz_mm = (config.SPEED_OF_SOUND / (2 * config.SAMPLING_FREQUENCY)) * 1000
    tolerance_mm = 5 * dz_mm  # a few depth-sample widths of slack
    report(f"peak within {tolerance_mm:.3f} mm tolerance", error_mm < tolerance_mm)


def test_2_correct_vs_incorrect_delay():
    print("\n--- Test 2: Correct vs incorrect receive delay ---")
    element_positions = config.get_element_positions()
    x_target, z_target = 0.0, 0.03

    rf, _ = generate_point_target_rf(x_target, z_target, element_positions, config)
    scanline_positions = np.array([x_target])

    bf_correct, _ = das_beamform(rf, element_positions, scanline_positions, config, apply_focus=True)
    bf_wrong, _ = das_beamform(rf, element_positions, scanline_positions, config, apply_focus=False)

    peak_correct = np.max(np.abs(bf_correct))
    peak_wrong = np.max(np.abs(bf_wrong))

    print(f"  peak amplitude with correct delays:   {peak_correct:.3f}")
    print(f"  peak amplitude with no RX focusing:   {peak_wrong:.3f}")
    report("correct-delay peak is stronger than unfocused peak", peak_correct > peak_wrong)


def test_3_lateral_localization():
    print("\n--- Test 3: Lateral localization (two targets) ---")
    element_positions = config.get_element_positions()

    x1, z1 = -0.004, 0.025
    x2, z2 = 0.005, 0.035

    rf, _ = generate_two_point_targets_rf(
        [(x1, z1, 1.0), (x2, z2, 1.0)], element_positions, config
    )

    scanline_positions = config.get_scanline_positions()
    # das_beamform expects one RF frame per line; here we reuse the same
    # plane-wave-style shot for every line (see receive_beamforming.py
    # docstring re: simplified transmit model).
    raw_rf_multi = np.repeat(rf[:, :, None], scanline_positions.shape[0], axis=2)

    beamformed, z_axis = das_beamform(raw_rf_multi, element_positions, scanline_positions, config)
    bmode_like = np.abs(beamformed)

    # Find the two strongest, well-separated local peaks
    peak_flat = np.argsort(bmode_like, axis=None)[::-1]
    depth_idx, line_idx = np.unravel_index(peak_flat[0], bmode_like.shape)
    found_x1, found_z1 = scanline_positions[line_idx], z_axis[depth_idx]
    print(f"  strongest peak at x={found_x1*1000:.2f} mm, z={found_z1*1000:.2f} mm")

    close_to_1 = abs(found_x1 - x1) < 0.002 and abs(found_z1 - z1) < 0.003
    close_to_2 = abs(found_x1 - x2) < 0.002 and abs(found_z1 - z2) < 0.003
    report("strongest peak lands near one of the two targets", close_to_1 or close_to_2)


def test_4_depth_localization():
    print("\n--- Test 4: Depth localization ---")
    element_positions = config.get_element_positions()
    x_target = 0.0

    for z_target in (0.015, 0.04, 0.055):
        rf, _ = generate_point_target_rf(x_target, z_target, element_positions, config)
        scanline_positions = np.array([x_target])
        beamformed, z_axis = das_beamform(rf, element_positions, scanline_positions, config)
        z_peak = z_axis[np.argmax(np.abs(beamformed))]
        error_mm = abs(z_peak - z_target) * 1000
        print(f"  target z={z_target*1000:.1f} mm -> measured peak z={z_peak*1000:.2f} mm "
              f"(error {error_mm:.3f} mm)")
        report(f"  depth error small at z={z_target*1000:.1f} mm", error_mm < 0.5)


if __name__ == "__main__":
    test_1_point_target_focusing()
    test_2_correct_vs_incorrect_delay()
    test_3_lateral_localization()
    test_4_depth_localization()
