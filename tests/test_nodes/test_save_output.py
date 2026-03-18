"""Tests for save_output node."""
import json
from simagents.nodes.save_output import save_output

def test_save_output_writes_json_files(tmp_path):
    state = {
        "formatted_parameters": {
            "genic": {"BoxSize": 100000, "Ngrid": 64},
            "gadget": {"Omega0": 0.3, "TimeMax": 1.0},
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
