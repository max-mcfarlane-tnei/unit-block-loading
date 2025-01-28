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
        # The with statement means we do not have to close the file, removing ResourceWarning Unclosed file
        with open('.test_cache.p', 'wb') as f:
            pickle.dump(active_power, f)

        # Also add with statement for the read file to remove Unclosed file error
        with open('.test_cache.p', 'rb') as f:
            comparison_data = pickle.load(f)

        self.assertTrue(active_power.equals(comparison_data))

import warnings
import traceback

# Custom warning handler to include tracebacks
def custom_warn_handler(message, category, filename, lineno, file=None, line=None):
    print(f"Warning: {message}")
    traceback.print_stack()

warnings.showwarning = custom_warn_handler
warnings.simplefilter('always', FutureWarning)

if __name__ == '__main__':
    unittest.main()
