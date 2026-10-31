"""Tests for the HPC scenario runner."""

from pathlib import Path

import pytest
import yaml

from absice.schemas.simulation_config import SimulationConfig
from hpc.scenario_runner import run_scenario


def test_settings_file_replaces_only_listed_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_folder = tmp_path / "project"
    project_folder.mkdir()
    settings_path = project_folder / "run_settings.yaml"
    settings_path.write_text(
        yaml.safe_dump(
            {"scenario": {"landfill_solar_waste_acceptance_ratio": 0.75}}
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "hpc.scenario_runner.run_batch",
        lambda **kwargs: [],
    )

    run_scenario(
        landfill_set=None,
        ratio=1.0,
        cost_component="recycling",
        n_runs=1,
        n_steps=1,
        results_base=tmp_path / "results",
        recycle_rate=0.20,
        att_mean=0.515,
        att_std=0.1,
        rtn=False,
        project_root=project_folder,
        settings_file=Path("run_settings.yaml"),
    )

    saved_config_path = next(
        (tmp_path / "results").rglob("scenario_config.yaml")
    )
    saved_config = SimulationConfig.from_yaml(saved_config_path)
    assert saved_config.scenario.landfill_solar_waste_acceptance_ratio == 0.75
    # A neighbouring value in the same section keeps its base setting.
    assert saved_config.scenario.hazardous_waste_regulation_enabled is False


@pytest.mark.parametrize(
    ("rtn", "expected_states"),
    [
        (False, None),
        (True, ["TX", "AZ", "NV", "NM"]),
    ],
)
def test_run_uses_base_config_for_run_type(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rtn: bool,
    expected_states: list[str] | None,
) -> None:
    monkeypatch.setattr(
        "hpc.scenario_runner.run_batch",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        "hpc.scenario_runner.cost_scaling.prepare_rtn_recycling_cost_file",
        lambda **kwargs: "test_recycling_costs.csv",
    )

    run_scenario(
        landfill_set="all_landfills" if rtn else None,
        ratio=1.0,
        cost_component="recycling",
        n_runs=1,
        n_steps=1,
        results_base=tmp_path / "results",
        recycle_rate=0.20,
        att_mean=0.515,
        att_std=0.1,
        rtn=rtn,
    )

    saved_config_path = next(
        (tmp_path / "results").rglob("scenario_config.yaml")
    )
    saved_config = SimulationConfig.from_yaml(saved_config_path)
    assert saved_config.consumer.model_states == expected_states
    assert saved_config.data_source.rtn is rtn


def test_calibration_sweep_pairs_settings_file_with_results_folder() -> None:
    spec_path = Path(__file__).parents[1] / "hpc" / "torc_att_calibration.yaml"
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    job = spec["jobs"][0]

    assert "--settings-file hpc/run_settings_{condition}.yaml" in job["command"]
    assert "--results-base results/att_calibration/{condition}" in job["command"]
    assert "condition" in job["parameters"]
