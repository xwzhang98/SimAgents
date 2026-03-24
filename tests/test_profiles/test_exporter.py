"""Tests for the native param file exporter."""
from pathlib import Path
from simagents.profiles.loader import load_profile
from simagents.profiles.exporter import export_native

PROFILES_DIR = str(Path(__file__).resolve().parents[2] / "data" / "software_profiles")


def test_export_gadget4_native():
    profile = load_profile("gadget-4", PROFILES_DIR)
    sections = {"params": {"Omega0": 0.3089, "OmegaLambda": 0.6911, "HubbleParam": 0.6774, "BoxSize": 75000}}
    result = export_native(profile, sections, "test_paper")
    assert len(result) > 0
    filename, content = list(result.items())[0]
    assert "Omega0" in content
    assert "0.3089" in content


def test_export_swift_yaml():
    profile = load_profile("swift", PROFILES_DIR)
    sections = {"params": {"h": 0.6774, "Omega_cdm": 0.2589, "Omega_lambda": 0.6911, "Omega_b": 0.0486}}
    result = export_native(profile, sections, "test_paper")
    assert len(result) > 0
    filename, content = list(result.items())[0]
    assert "Omega_cdm" in content or "h:" in content


def test_export_no_templates_returns_empty():
    profile = load_profile("mp-gadget", PROFILES_DIR)
    profile_copy = profile.model_copy(update={"templates_dir": Path("/nonexistent")})
    result = export_native(profile_copy, {"genic": {}}, "test")
    assert result == {}


def test_export_mp_gadget_two_sections():
    profile = load_profile("mp-gadget", PROFILES_DIR)
    sections = {
        "genic": {"BoxSize": 100000, "Ngrid": 512, "Seed": 12345},
        "gadget": {"Omega0": 0.3089, "TimeMax": 1.0},
    }
    result = export_native(profile, sections, "test_paper")
    assert len(result) == 2
    filenames = list(result.keys())
    assert any("genic" in f for f in filenames)
    assert any("gadget" in f for f in filenames)
