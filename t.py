import unittest

import config
from run import run_basic_example
import pickle
import pandas as pd


class TestRun (unittest.TestCase):
    """
    A test case for the run_basic_example function.
    """

    def test_run_basic_example_targets(self):
        """
        Test the run_basic_example function.
        """
        # Call the function
        decision_fig, cumulative_cost_fig, active_power_fig, subplot_fig, active_power, c = run_basic_example(
            t=config.T,
            n=config.N,
            restart_targets=config.RESTART_TARGETS,
            block_limit=config.BLOCK_LIMIT,
            generators_inactive=0,
            min_operating_capacity=0.15
        )

        for (target_days, target_proportion) in [(2, 0.6), (4, 1)]:

            idx = active_power.index[0] + pd.Timedelta(days=target_days)

            target_volume = active_power.loc[idx, 'forecasted demand'] * target_proportion

            block_demand = active_power.loc[idx, 'block demand']

            net_generation = active_power.loc[idx, 'net generation']
            solar = active_power.loc[idx, 'solar']
            wind = active_power.loc[idx, 'wind']

            gross_generation = solar + wind + net_generation

            self.assertAlmostEqual(block_demand, gross_generation)
            self.assertTrue(round(block_demand, 2) >= round(target_volume, 2))


if __name__ == '__main__':
    unittest.main()
