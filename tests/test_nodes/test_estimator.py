"""Tests for the estimator node."""
import json
import math
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from simagents.nodes.estimator import compute_heuristic, estimator


def test_compute_heuristic_dm_only():
    """DM-only simulation heuristic estimates."""
    sections = {
        "genic": {"Ngrid": 256, "BoxSize": 100000},
        "gadget": {"Omega0": 0.3},
    }
    result = compute_heuristic(sections, "mp-gadget")
    assert result["n_particles"] == 256 ** 3
    assert result["is_hydro"] is False
    assert result["memory_gb"] > 0
    assert result["cpu_hours"] > 0
    assert result["ngrid"] == 256
    # DM memory: 256^3 * 150 bytes
    expected_memory_gb = (256 ** 3 * 150) / (1024 ** 3)
    assert abs(result["memory_gb"] - round(expected_memory_gb, 2)) < 0.01


def test_compute_heuristic_hydro():
    """Hydrodynamic simulation should have higher estimates than DM-only."""
    dm_sections = {
        "genic": {"Ngrid": 256, "BoxSize": 100000},
        "gadget": {"Omega0": 0.3},
    }
    hydro_sections = {
        "genic": {"Ngrid": 256, "BoxSize": 100000, "OmegaBaryon": 0.04},
        "gadget": {"Omega0": 0.3},
    }
    dm_result = compute_heuristic(dm_sections, "mp-gadget")
    hydro_result = compute_heuristic(hydro_sections, "mp-gadget")

    assert hydro_result["is_hydro"] is True
    assert dm_result["is_hydro"] is False
    # Hydro has 2x particles and 500 bytes/particle vs 150 bytes/particle for DM
    assert hydro_result["memory_gb"] > dm_result["memory_gb"]
    assert hydro_result["cpu_hours"] > dm_result["cpu_hours"]
    assert hydro_result["n_particles"] == 2 * dm_result["n_particles"]


def test_compute_heuristic_missing_params():
    """Should handle missing Ngrid gracefully."""
    sections = {"gadget": {"Omega0": 0.3, "HubbleParam": 0.7}}
    result = compute_heuristic(sections, "mp-gadget")
    assert result["n_particles"] == 0
    assert result["ngrid"] is None
    assert result["memory_gb"] == 0.0
    assert result["cpu_hours"] == 0


def test_compute_heuristic_empty_sections():
    """Should handle empty sections gracefully."""
    result = compute_heuristic({}, "mp-gadget")
    assert result["n_particles"] == 0
    assert result["is_hydro"] is False
    assert result["memory_gb"] == 0.0


def test_estimator_node_with_mocked_llm():
    """estimator node should call LLM and return resource estimates."""
    mock_llm = MagicMock()
    mock_response = AIMessage(content=json.dumps({
        "memory_per_node_gb": 64.0,
        "total_cpu_hours": 500000,
        "wall_clock": "3 days",
        "storage_tb": 2.5,
        "recommended_nodes": 512,
        "confidence": "medium",
        "reference_simulation": "BlueTides",
        "reasoning": "Scaled from BlueTides reference with smaller box size.",
    }))
    mock_llm.invoke.return_value = mock_response

    state = {
        "target_software": "mp-gadget",
        "formatted_parameters": {
            "sections": {
                "genic": {"Ngrid": 512, "BoxSize": 200000, "OmegaBaryon": 0.04},
                "gadget": {"Omega0": 0.3},
            }
        },
        "resource_estimates": {},
    }
    config = {"configurable": {"llm": mock_llm}}

    result = estimator(state, config)
    assert "resource_estimates" in result
    estimates = result["resource_estimates"]
    assert estimates["memory_per_node_gb"] == 64.0
    assert estimates["total_cpu_hours"] == 500000
    assert estimates["confidence"] == "medium"
    assert estimates["reference_simulation"] == "BlueTides"
    mock_llm.invoke.assert_called_once()


def test_estimator_node_fallback_on_llm_failure():
    """estimator node should return heuristic-only on LLM failure."""
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = Exception("LLM unavailable")

    state = {
        "target_software": "mp-gadget",
        "formatted_parameters": {
            "sections": {
                "genic": {"Ngrid": 128, "BoxSize": 50000},
                "gadget": {"Omega0": 0.3},
            }
        },
        "resource_estimates": {},
    }
    config = {"configurable": {"llm": mock_llm}}

    result = estimator(state, config)
    assert "resource_estimates" in result
    estimates = result["resource_estimates"]
    assert estimates["confidence"] == "low"
    assert "heuristic" in estimates["reasoning"].lower() or "failed" in estimates["reasoning"].lower()


def test_estimator_node_no_llm_fallback():
    """estimator node should return heuristic-only when no LLM is configured."""
    state = {
        "target_software": "mp-gadget",
        "formatted_parameters": {
            "sections": {
                "genic": {"Ngrid": 64, "BoxSize": 25000},
            }
        },
        "resource_estimates": {},
    }
    config = {"configurable": {}}

    result = estimator(state, config)
    assert "resource_estimates" in result
    estimates = result["resource_estimates"]
    assert estimates["confidence"] == "low"
