import os
import unittest
from pathlib import Path

from ABM_CE_PV_Model import ABM_CE_PV
from absice.data.data_loader import DataLoader
from absice.schemas.data_paths_config import DataPathsConfig
from absice.schemas.simulation_config import SimulationConfig

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


class TestABM_CE_PV(unittest.TestCase):
    def setUp(self):
        config: SimulationConfig = SimulationConfig()
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
            self.model = ABM_CE_PV(config=config, data=data)
        finally:
            os.chdir(PROJECT_ROOT)

    def test_tclp_test(self):
        # Test the tclp_test with samples of different market-share years
        hazardous_2035 = []
        hazardous_2056 = []
        for _ in range(1000):
            hazardous_2035.append(self.model.tclp_test(
                self.model.tclp_market_share_df, current_year=2035, state='CA'))
            hazardous_2056.append(self.model.tclp_test(
                self.model.tclp_market_share_df, current_year=2056, state='CA'))
        hazardous_2035_rate = sum(hazardous_2035) / len(hazardous_2035)
        hazardous_2056_rate = sum(hazardous_2056) / len(hazardous_2056)

        # Higher BSF share year has a higher hazardous rate
        self.assertGreater(hazardous_2035_rate, hazardous_2056_rate)


if __name__ == '__main__':
    unittest.main()