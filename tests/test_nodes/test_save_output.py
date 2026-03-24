"""Tests for save_output node."""
import json
from pathlib import Path
from simagents.nodes.save_output import save_output
from simagents.profiles.loader import SoftwareProfile, OutputSection


def test_save_output_writes_json_files(tmp_path):
    """Save output using sections format without profile (fallback)."""
    state = {
        "formatted_parameters": {
            "sections": {
                "genic": {"BoxSize": 100000, "Ngrid": 64},
                "gadget": {"Omega0": 0.3, "TimeMax": 1.0},
            },
            "comment": "Test extraction",
            "sources": [{"param": "BoxSize", "value": 100000, "location": "Table 1", "page": 3}],
        },
        "status": "complete",
        "missing_parameters": [],
        "paper_path": "/path/to/my_paper.pdf",
    }
    config = {"configurable": {"output_dir": str(tmp_path)}}
    result = save_output(state, config)
    genic_path = tmp_path / "my_paper_genic.json"
    gadget_path = tmp_path / "my_paper_gadget.json"
    assert genic_path.exists()
    assert gadget_path.exists()
    genic_data = json.loads(genic_path.read_text())
    assert genic_data["parameters"]["BoxSize"] == 100000
    gadget_data = json.loads(gadget_path.read_text())
    assert gadget_data["parameters"]["Omega0"] == 0.3
    assert result["status"] == "complete"


def test_save_output_with_profile(tmp_path):
    """Save output uses profile's filename_template."""
    profile = SoftwareProfile(
        slug="test-sw",
        name="TestSoftware",
        description="Test",
        family="gadget",
        output_format="key-value",
        output_sections=[
            OutputSection(name="params", description="Main params", filename_template="{paper}_params.json"),
            OutputSection(name="ic", description="IC params", filename_template="{paper}_ic.json"),
        ],
        units={},
        ic_generator="none",
        ic_note="",
        parameter_names={},
        docs_dir=Path("/tmp/fake"),
        templates_dir=Path("/tmp/fake"),
        profile_dir=Path("/tmp/fake"),
    )
    state = {
        "formatted_parameters": {
            "sections": {
                "params": {"BoxSize": 100000},
                "ic": {"Seed": 42},
            },
            "comment": "Test",
            "sources": [],
        },
        "status": "complete",
        "missing_parameters": [],
        "paper_path": "/path/to/sim_paper.pdf",
    }
    config = {"configurable": {"output_dir": str(tmp_path), "profile": profile}}
    result = save_output(state, config)
    params_path = tmp_path / "sim_paper_params.json"
    ic_path = tmp_path / "sim_paper_ic.json"
    assert params_path.exists()
    assert ic_path.exists()
    params_data = json.loads(params_path.read_text())
    assert params_data["parameters"]["BoxSize"] == 100000
    ic_data = json.loads(ic_path.read_text())
    assert ic_data["parameters"]["Seed"] == 42
    assert result["status"] == "complete"
