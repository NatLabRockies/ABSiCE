"""Tests for the $/module to $/metric ton conversion and RTN rebasing."""

from pathlib import Path

import pandas as pd
import pytest

from absice.data.cost_units import (
    BASELINE_RECYCLING_RATE_PER_KG,
    MODULES_PER_METRIC_TON,
)
from absice.schemas.simulation_config import CostConfig, SimulationConfig
from hpc import cost_scaling


def test_baseline_recycling_cost_is_12_5_per_module() -> None:
    """12.5 $/module is 12.5 / 18.9 $/kg, and the config holds it in $/metric ton."""
    cost: CostConfig = CostConfig()

    assert BASELINE_RECYCLING_RATE_PER_KG == pytest.approx(12.5 / 18.9)
    assert cost.original_recycling_cost[2] == pytest.approx(
        BASELINE_RECYCLING_RATE_PER_KG * 1000
    )
    assert cost_scaling.ratio_from_cost_rate(BASELINE_RECYCLING_RATE_PER_KG) == 1.0


def test_only_monetary_fields_are_converted() -> None:
    """The price decay, transport and premiums are not module costs."""
    cost: CostConfig = CostConfig()

    assert cost.fsthand_mkt_pric_reg_param == pytest.approx(
        [MODULES_PER_METRIC_TON, 0.04]
    )
    assert cost.sa_landfill_costs[1] == pytest.approx(0.999 * MODULES_PER_METRIC_TON)
    assert cost.hoarding_cost[2] == pytest.approx(0.135 * MODULES_PER_METRIC_TON)
    assert cost.transportation_cost == 0.095
    assert cost.hazardous_waste_management_cost["landfill"] == 0.0


def test_yaml_round_trip_keeps_module_units(tmp_path: Path) -> None:
    """Written configs use $/module and do not convert again when reloaded."""
    config: SimulationConfig = SimulationConfig()
    path: Path = tmp_path / "config.yaml"

    config.to_yaml(path)
    reloaded: SimulationConfig = SimulationConfig.from_yaml(path)

    assert "12.5" in path.read_text(encoding="utf-8")
    assert reloaded.cost.original_recycling_cost == pytest.approx(
        config.cost.original_recycling_cost
    )
    assert reloaded.cost.fsthand_mkt_pric_reg_param == pytest.approx(
        config.cost.fsthand_mkt_pric_reg_param
    )


def test_assignment_is_not_converted_again() -> None:
    """Scaling a config value (as the HPC runner does) keeps $/metric ton."""
    cost: CostConfig = CostConfig()
    scaled: list[float] = cost_scaling.scale_original_recycling_cost(
        cost.original_recycling_cost, 2.0
    )

    cost.original_recycling_cost = scaled

    assert cost.original_recycling_cost == scaled


def test_rtn_shipments_are_rebased_and_keep_transport(tmp_path: Path) -> None:
    """Processing cost is rebased to the 12.5 $/module baseline; transport is kept."""
    shipments: Path = tmp_path / "shipments.csv"
    pd.DataFrame({
        "Shipped_kg": [18.9],
        "RecyclingCost_$": [18.9 * cost_scaling.RAW_RTN_RECYCLING_RATE_PER_KG],
        "TransportCost_$": [2.0],
        "TotalCost_$": [18.9 * cost_scaling.RAW_RTN_RECYCLING_RATE_PER_KG + 2.0],
    }).to_csv(shipments, index=False)

    scaled: Path = cost_scaling._scale_shipment_file(
        file_path=shipments,
        scale=2.0 * BASELINE_RECYCLING_RATE_PER_KG
        / cost_scaling.RAW_RTN_RECYCLING_RATE_PER_KG,
        cost_col="RecyclingCost_$",
        transport_col="TransportCost_$",
        total_col="TotalCost_$",
        file_suffix="_rebased",
        output_dir=tmp_path,
    )
    result: pd.DataFrame = pd.read_csv(scaled)

    assert result["RecyclingCost_$"][0] == pytest.approx(25.0)
    assert result["TransportCost_$"][0] == 2.0
    assert result["TotalCost_$"][0] == pytest.approx(27.0)
