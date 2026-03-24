"""Tests for software profile loader."""
import pytest
from pathlib import Path
from simagents.profiles.loader import load_profile, list_profiles

PROFILES_DIR = str(Path(__file__).resolve().parents[2] / "data" / "software_profiles")


def test_load_profile_mp_gadget():
    profile = load_profile("mp-gadget", PROFILES_DIR)
    assert profile.slug == "mp-gadget"
    assert profile.name == "MP-Gadget"
    assert profile.family == "gadget"
    assert len(profile.output_sections) == 2
    assert profile.ic_generator == "builtin"
    assert profile.parameter_names["matter_density"] == "Omega0"


def test_load_profile_swift():
    profile = load_profile("swift", PROFILES_DIR)
    assert profile.slug == "swift"
    assert profile.family == "swift"
    assert profile.units["length"] == "Mpc"
    assert profile.parameter_names["matter_density"] == "Omega_cdm"
    assert profile.ic_generator == "external"


def test_load_profile_gadget4():
    profile = load_profile("gadget-4", PROFILES_DIR)
    assert profile.family == "gadget"
    assert len(profile.output_sections) == 1


def test_load_profile_not_found():
    with pytest.raises(FileNotFoundError):
        load_profile("nonexistent", PROFILES_DIR)


def test_list_profiles():
    profiles = list_profiles(PROFILES_DIR)
    assert len(profiles) >= 5
    slugs = [p["slug"] for p in profiles]
    assert "mp-gadget" in slugs
    assert "swift" in slugs
    assert "gadget-4" in slugs
    assert "arepo" in slugs
    assert "gizmo" in slugs


def test_profile_has_docs_dir():
    profile = load_profile("mp-gadget", PROFILES_DIR)
    assert profile.docs_dir.exists()
    assert any(profile.docs_dir.glob("*.md"))
