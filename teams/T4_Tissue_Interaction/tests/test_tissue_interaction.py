import numpy as np
import pytest

from tissue_interaction import interaction_gain, pressure_reflection_coefficient, tissue_interaction


def test_equal_impedance_has_zero_interface_reflection():
    assert pressure_reflection_coefficient(1.63, 1.63) == 0.0


def test_reflection_coefficient_matches_normal_incidence_formula():
    z1, z2 = 1.5, 1.8
    expected = (z2 - z1) / (z2 + z1)
    assert np.isclose(pressure_reflection_coefficient(z1, z2), expected)


def test_existing_amp_only_phantom_remains_compatible():
    wave = np.array([0.0, 1.0, -0.5, 0.25])
    out = tissue_interaction(wave, {"x": 0.0, "z": 0.02, "amp": 0.4})
    np.testing.assert_allclose(out, 0.4 * wave)


def test_output_shape_is_preserved():
    wave = np.sin(np.linspace(0, 10, 100))
    out = tissue_interaction(wave, {"amp": 0.7})
    assert out.shape == wave.shape
    assert np.all(np.isfinite(out))


def test_impedance_contrast_can_modify_scattering_gain():
    g_equal = interaction_gain({"amp": 1.0, "background_impedance_mrayl": 1.63, "impedance_mrayl": 1.63})
    g_contrast = interaction_gain({"amp": 1.0, "background_impedance_mrayl": 1.63, "impedance_mrayl": 2.0})
    assert g_equal == 1.0
    assert g_contrast > g_equal


def test_empty_phantom_has_no_scatterers():
    from phantom import PhantomConfig, generate_liver_phantom
    p = generate_liver_phantom(PhantomConfig(scatterer_density_m2=0.0, seed=7))
    assert p.num_scatterers == 0


def test_single_scatterer_has_predictable_echo():
    wave = np.array([1.0, -2.0, 0.5])
    out = tissue_interaction(wave, {"amp": 0.25})
    np.testing.assert_allclose(out, 0.25 * wave)


def test_multiple_scatterers_can_be_composited_linearly():
    wave = np.array([1.0, 2.0])
    a = tissue_interaction(wave, {"amp": 0.2})
    b = tissue_interaction(wave, {"amp": -0.1})
    np.testing.assert_allclose(a + b, 0.1 * wave)


def test_same_seed_gives_identical_phantom():
    from phantom import PhantomConfig, generate_liver_phantom
    cfg = PhantomConfig(seed=123, scatterer_density_m2=10_000)
    a = generate_liver_phantom(cfg)
    b = generate_liver_phantom(cfg)
    assert a.scatterers == b.scatterers


def test_different_seed_gives_different_phantom():
    from phantom import PhantomConfig, generate_liver_phantom
    a = generate_liver_phantom(PhantomConfig(seed=1, scatterer_density_m2=10_000))
    b = generate_liver_phantom(PhantomConfig(seed=2, scatterer_density_m2=10_000))
    assert a.scatterers != b.scatterers


def test_lesion_changes_local_scattering_statistics():
    from phantom import LesionProperties, PhantomConfig, generate_liver_phantom
    lesion = LesionProperties(center_z_m=0.035, radius_x_m=0.008, radius_z_m=0.008, echo_class="hypoechoic")
    p = generate_liver_phantom(PhantomConfig(seed=99, scatterer_density_m2=80_000, lesion=lesion))
    lesion_amps = np.array([float(s["amp"]) for s in p.scatterers if s["is_lesion"]])
    background_amps = np.array([float(s["amp"]) for s in p.scatterers if not s["is_lesion"]])
    assert lesion_amps.size > 0
    assert background_amps.size > 0
    assert np.std(lesion_amps) < np.std(background_amps)


def test_shape_units_and_finiteness():
    from phantom import PhantomConfig, generate_liver_phantom
    p = generate_liver_phantom(PhantomConfig(seed=4, scatterer_density_m2=20_000))
    for s in p.scatterers:
        assert p.x_min_m <= s["x"] <= p.x_max_m
        assert p.z_min_m <= s["z"] <= p.z_max_m
        assert np.isfinite(float(s["amp"]))


def test_invalid_waveform_is_rejected():
    with pytest.raises(ValueError):
        tissue_interaction(np.ones((2, 2)), {"amp": 1.0})
