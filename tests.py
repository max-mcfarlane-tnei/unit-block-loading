import unittest

import config
from run import run_basic_example
import pickle
import pandas as pd


class TestRunBasicExample(unittest.TestCase):
    """
    A test case for the run_basic_example function.
    """

    def test_run_basic_example(self):
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

        # pickle.dump(active_power, open('.test_cache.p', 'wb'))
        comparison_data = pickle.load(open('.test_cache.p', 'rb'))

        self.assertTrue(active_power.equals(comparison_data))

if __name__ == '__main__':
    unittest.main()
