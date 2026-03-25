"""Tests for profile-driven validator."""
from pathlib import Path
from simagents.profiles.loader import SoftwareProfile, OutputSection, ValidationConfig
from simagents.profiles.validator import validate_and_correct, generate_validation_rules_text


def _make_profile(**overrides) -> SoftwareProfile:
    defaults = dict(
        slug="test",
        name="Test",
        description="",
        family="gadget",
        output_sections=[OutputSection(name="params", description="test")],
        docs_dir=Path("/tmp/docs"),
        templates_dir=Path("/tmp/templates"),
        profile_dir=Path("/tmp/profile"),
        validation=ValidationConfig(
            parameter_ranges={
                "Omega0": [0.2, 0.4],
                "OmegaLambda": [0.6, 0.8],
                "HubbleParam": [0.5, 1.0],
            },
            swap_detection=[
                {"pair": ["Omega0", "OmegaLambda"], "rule": "Omega0 ~0.3, OmegaLambda ~0.7"}
            ],
            large_value_corrections=[
                {"params": ["Ngrid"], "threshold": 50000, "action": "cube_root", "reason": "N³ -> N"}
            ],
            required_parameters=["Omega0", "OmegaLambda", "HubbleParam", "BoxSize"],
        ),
    )
    defaults.update(overrides)
    return SoftwareProfile(**defaults)


def test_swap_detection():
    profile = _make_profile()
    sections = {"params": {"Omega0": 0.7, "OmegaLambda": 0.3, "HubbleParam": 0.67}}
    corrected, issues = validate_and_correct(sections, profile)
    assert corrected["params"]["Omega0"] == 0.3
    assert corrected["params"]["OmegaLambda"] == 0.7
    assert any("Swapped" in i for i in issues)


def test_no_swap_when_correct():
    profile = _make_profile()
    sections = {"params": {"Omega0": 0.3, "OmegaLambda": 0.7, "HubbleParam": 0.67}}
    corrected, issues = validate_and_correct(sections, profile)
    assert corrected["params"]["Omega0"] == 0.3
    assert corrected["params"]["OmegaLambda"] == 0.7
    assert not any("Swapped" in i for i in issues)


def test_cube_root_correction():
    profile = _make_profile()
    sections = {"params": {"Ngrid": 512**3}}  # 134217728
    corrected, issues = validate_and_correct(sections, profile)
    assert corrected["params"]["Ngrid"] == 512
    assert any("cube root" in i.lower() or "N³" in i for i in issues)


def test_no_cube_root_when_small():
    profile = _make_profile()
    sections = {"params": {"Ngrid": 1024}}
    corrected, issues = validate_and_correct(sections, profile)
    assert corrected["params"]["Ngrid"] == 1024
    assert not any("Corrected Ngrid" in i for i in issues)


def test_range_violation_reported():
    profile = _make_profile()
    sections = {"params": {"HubbleParam": 67.0}}  # Not h, full H0
    _, issues = validate_and_correct(sections, profile)
    assert any("HubbleParam=67.0" in i and "outside" in i for i in issues)


def test_none_values_removed():
    profile = _make_profile()
    sections = {"params": {"Omega0": 0.3, "BadParam": None, "HubbleParam": 0.67}}
    corrected, _ = validate_and_correct(sections, profile)
    assert "BadParam" not in corrected["params"]


def test_empty_validation_config():
    profile = _make_profile(validation=ValidationConfig())
    sections = {"params": {"Omega0": 0.7, "OmegaLambda": 0.3}}
    corrected, issues = validate_and_correct(sections, profile)
    # No swap detection configured, values unchanged
    assert corrected["params"]["Omega0"] == 0.7
    assert issues == []


def test_generate_validation_rules_text():
    profile = _make_profile()
    text = generate_validation_rules_text(profile)
    assert "Omega0 must be in range" in text
    assert "HubbleParam must be in range" in text
    assert "swapped" in text.lower()
    assert "Ngrid" in text


def test_generate_validation_rules_empty():
    profile = _make_profile(validation=ValidationConfig())
    text = generate_validation_rules_text(profile)
    assert text == ""


def test_multi_section_swap():
    """Swap detection works across multiple sections (e.g. genic + gadget)."""
    profile = _make_profile()
    sections = {
        "genic": {"Omega0": 0.7, "OmegaLambda": 0.3},
        "gadget": {"Omega0": 0.7, "OmegaLambda": 0.3},
    }
    corrected, issues = validate_and_correct(sections, profile)
    assert corrected["genic"]["Omega0"] == 0.3
    assert corrected["gadget"]["Omega0"] == 0.3


def test_load_profile_with_validation():
    """Profiles load validation config from YAML."""
    from simagents.profiles.loader import load_profile
    profile = load_profile("mp-gadget")
    assert profile.validation.parameter_ranges.get("Omega0") == [0.2, 0.4]
    assert len(profile.validation.swap_detection) > 0
    assert len(profile.validation.required_parameters) > 0
