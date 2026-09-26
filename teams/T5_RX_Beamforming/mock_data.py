"""
mock_data.py
============

Point-target RF for T5's verify_beamformer.py, generated with the REAL engine,
not a simplified model: tissue_phantoms.simulate_rf(), i.e.

    T3 forward_propagation (broadcast, zero TX delays)
      -> T4 tissue_interaction -> T3 return_propagation

Both functions return (rf, t_axis): rf has shape (n_elements, len(t_axis)) and
t_axis is the real time axis (starts at -1.175 us, T3's convention). Because
the RF does not start at t = 0, a beamformer that broke the README Section 6
time-axis rule (tau * FS as an index) would land ~0.90 mm too deep and fail
test 1 (0.096 mm tolerance).
"""

import numpy as np

from tissue_phantoms import simulate_rf


def _check_geometry(element_positions, config):
    # simulate_rf() always uses the project array; refuse anything else rather
    # than silently simulating a different geometry than the caller asked for.
    if not np.allclose(element_positions, config.get_element_positions()):
        raise ValueError("mock_data only supports the project array, config.get_element_positions()")


def generate_point_target_rf(x, z, element_positions, config, amp=1.0):
    """RF for one point target at (x, z) [m]. Returns (rf, t_axis)."""
    _check_geometry(element_positions, config)
    return simulate_rf([{"x": x, "z": z, "amp": amp}])


def generate_two_point_targets_rf(targets, element_positions, config):
    """RF for point targets given as [(x, z, amp), ...] [m]. Returns (rf, t_axis)."""
    _check_geometry(element_positions, config)
    return simulate_rf([{"x": x, "z": z, "amp": a} for x, z, a in targets])
