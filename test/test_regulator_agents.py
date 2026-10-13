# -*- coding:utf-8 -*-
"""
Unit tests for Regulators agent policy scheduling logic.

Uses a real ABM_CE_PV model instance (shared across tests via setUpClass)
with a minimal configuration to keep startup time low.
"""

import os
import unittest
from pathlib import Path

from ABM_CE_PV_Model import ABM_CE_PV
from absice.data.data_loader import DataLoader
from absice.schemas.data_paths_config import DataPathsConfig
from absice.schemas.simulation_config import SimulationConfig

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


def _find_regulator(model, state: str):
    """Return the Regulators agent for the given state abbreviation."""
    for agent_id, agent_state in model.regulator_state_map.items():
        if agent_state == state:
            return model.agent_map[agent_id]
    return None


class TestRegulatorPolicies(unittest.TestCase):
    """
    Tests for Regulators agent policy scheduling and policy query methods.
    Covers: check_and_update_regulations, is_epr_applicable,
    is_recycling_bonds_applicable, and _load_policy_schedule_by_state.
    """

    @classmethod
    def setUpClass(cls):
        config: SimulationConfig = SimulationConfig()
        config.consumer.model_states = ["WA", "CA"]
        config.data_source.solar_cycle = False
        config.data_source.rtn = False
        data = DataLoader(DataPathsConfig.make_default(PROJECT_ROOT)).load_all(
            resolution=config.consumer.resolution,
            model_states=config.consumer.model_states,
            rtn=config.data_source.rtn,
            solar_cycle=config.data_source.solar_cycle,
            file_names=config.legacy_data.file_name.model_dump(by_alias=True),
        )
        # Model resolves paths from cwd and PV_ICE chdirs into a subfolder.
        os.chdir(PROJECT_ROOT)
        try:
            cls.model = ABM_CE_PV(config=config, data=data)
        finally:
            os.chdir(PROJECT_ROOT)

    # ------------------------------------------------------------------
    # _load_policy_schedule_by_state
    # ------------------------------------------------------------------

    def test_wa_epr_schedule_loaded(self):
        """Model loads WA EPR start_year=2030 from policy_schedule.yaml."""
        schedule = self.model.policy_schedule_by_state
        self.assertIn("WA", schedule)
        self.assertIn("epr", schedule["WA"])
        self.assertEqual(schedule["WA"]["epr"]["start_year"], 2030)

    def test_ca_has_no_epr_schedule(self):
        """CA has no EPR schedule entry in the baseline config."""
        schedule = self.model.policy_schedule_by_state
        ca_schedule = schedule.get("CA", {})
        self.assertNotIn("epr", ca_schedule)

    # ------------------------------------------------------------------
    # Baseline policy values (year 2020, model just initialised)
    # ------------------------------------------------------------------

    def test_wa_epr_false_at_start(self):
        """WA EPR is False at simulation start (year 2020, before 2030)."""
        wa_regulator = _find_regulator(self.model, "WA")
        self.assertIsNotNone(wa_regulator)
        self.assertFalse(wa_regulator.is_epr_applicable())

    def test_recycling_bonds_false_at_start(self):
        """No state has recycling bonds active in the baseline CSV."""
        wa_regulator = _find_regulator(self.model, "WA")
        ca_regulator = _find_regulator(self.model, "CA")
        self.assertFalse(wa_regulator.is_recycling_bonds_applicable())
        self.assertFalse(ca_regulator.is_recycling_bonds_applicable())

    # ------------------------------------------------------------------
    # check_and_update_regulations: EPR schedule for WA
    # ------------------------------------------------------------------

    def test_wa_epr_false_before_2030(self):
        """WA EPR stays False when simulation year is before 2030."""
        wa_regulator = _find_regulator(self.model, "WA")
        self.model.clock = 9   # year 2029 (2020 + 9)
        wa_regulator.check_and_update_regulations()
        self.assertFalse(wa_regulator.is_epr_applicable())

    def test_wa_epr_true_from_2030(self):
        """WA EPR becomes True once the simulation year reaches 2030."""
        wa_regulator = _find_regulator(self.model, "WA")
        self.model.clock = 10  # year 2030
        wa_regulator.check_and_update_regulations()
        self.assertTrue(wa_regulator.is_epr_applicable())

    def test_ca_epr_unaffected_by_wa_schedule(self):
        """CA EPR remains False at year 2030 — WA schedule does not bleed over."""
        ca_regulator = _find_regulator(self.model, "CA")
        self.model.clock = 10  # year 2030
        ca_regulator.check_and_update_regulations()
        self.assertFalse(ca_regulator.is_epr_applicable())

    def test_wa_epr_stays_true_after_2030(self):
        """WA EPR remains True beyond 2030 (start_year only, no end_year)."""
        wa_regulator = _find_regulator(self.model, "WA")
        self.model.clock = 20  # year 2040
        wa_regulator.check_and_update_regulations()
        self.assertTrue(wa_regulator.is_epr_applicable())

    def test_ca_universal_waste_regulation_true_from_csv(self):
        """CA universal waste regulation is True as read from policy_by_state.csv."""
        ca_regulator = _find_regulator(self.model, "CA")
        self.assertIsNotNone(ca_regulator)
        self.assertTrue(ca_regulator.is_universal_waste_regulation_applicable())


if __name__ == "__main__":
    unittest.main()

