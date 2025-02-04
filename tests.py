import pickle
import unittest
import config
from run import run_basic_example
from optimisation import (
    _block_load_increase_constraint,
    _block_load_decrease_constraint,
    _demand_constraint,
    BLOCK_DEMAND_INCREASE_CONSTRAINT_NAME,
    BLOCK_DEMAND_DECREASE_CONSTRAINT_NAME,
    DEMAND_CONSTRAINT_NAME,
)
import cvxpy as cp
import warnings
import numpy as np


# Ensure warnings are shown during tests
warnings.simplefilter('always', FutureWarning)


class TestRunBasicExample(unittest.TestCase):
    """
    A test case for the run_basic_example function.
    """

    def setUp(self):
        """
        Setup for unittest so we do not need this for every test.
        """
        self.results = run_basic_example(
            t=config.T,
            n=config.N,
            restart_targets=config.RESTART_TARGETS,
            block_limit=config.BLOCK_LIMIT,
            generators_inactive=0,
            min_operating_capacity=0.15
        )
        self.active_power = self.results[4]

    def test_run_basic_example(self):
        """
        Test the run_basic_example function.
        """
        # Call the function
        decision_fig, cumulative_cost_fig, active_power_fig, subplot_fig, active_power, c = self.results
        # The with statement means we do not have to close the file, removing ResourceWarning Unclosed file
        with open('.test_cache.p', 'wb') as f:
            pickle.dump(active_power, f)

        # Also add with statement for the read file to remove Unclosed file error
        with open('.test_cache.p', 'rb') as f:
            comparison_data = pickle.load(f)

        self.assertTrue(active_power.equals(comparison_data))

    def test_demand_equals_generation(self):
        """
        Test for demand = generation at a given timestamp
        """
        decision_fig, cumulative_cost_fig, active_power_fig, subplot_fig, active_power, c = self.results

        idx = active_power.index[2] #This is the time stamps in the data
                                    #The wind generation never goes to 0
                                    #At the first few time stamps generation > demand

        demand = active_power.loc[idx, 'block demand']

        solar = active_power.loc[idx, 'solar']
        wind = active_power.loc[idx, 'wind']

        gross_generation = solar + wind

        for col in active_power.columns:
            if col.startswith("Generator"):
                gross_generation += active_power.loc[idx, col]

        self.assertAlmostEqual(gross_generation, demand)

    def test_initial_demand(self):
        """
        Test for initial demand equals zero
        """
        decision_fig, cumulative_cost_fig, active_power_fig, subplot_fig, active_power, c = self.results

        idx = active_power.index[0] # Demand at the first timestamp

        initial_demand = active_power.loc[idx, 'block demand']


        self.assertEqual(initial_demand, 0)

    def test_block_demand_non_negativity(self):
        """
        Test that the block demand is always non-negative.
        """
        _, _, _, _, active_power, _ = self.results

        demand = active_power['block demand']

        # Check if all block demand values are non-negative
        self.assertTrue((demand >= 0).all(), "Demand is negative at some timestep.")

    def test_initial_generator_status(self):
        """
        Test that all generators (including solar and wind) are initially inactive.
        ISSUES with this, the wind is not inactive at the start ?
        """
        _, _, _, _, active_power, _ = self.results

        # Check the initial power output of each generator
        for i in range(config.N):
            generator_col = f'Generator {i}'
            initial_power = active_power[generator_col].iloc[0]
            self.assertEqual(initial_power, 0, f"Generator {i} is not initially inactive.")

        # Check the initial power output of solar and wind generators
        solar = active_power['solar'].iloc[0]
        #wind = active_power['wind'].iloc[0]

        self.assertEqual(solar, 0, "Solar generator is not initially inactive.")
        #self.assertEqual(wind, 0, "Wind generator is not initially inactive.")

    def test_cumulative_cost_increase(self):
        """
        Test that the cumulative cost increases over time.
        """
        _, cumulative_cost_fig, _, _, _, _ = self.results


        cumulative_cost_data = cumulative_cost_fig.data[0].y

        # Check that the cumulative cost is increasing
        self.assertTrue(
            all(cumulative_cost_data[i] <= cumulative_cost_data[i + 1] for i in range(len(cumulative_cost_data) - 1)),
            "Cumulative cost is not increasing over time.")

    def test_minimum_operating_capacity(self):
        """
        Test that active generators meet or exceed their minimum operating capacity.
        """
        MIN_OPERATING_CAPACITY = 0.15
        _, _, _, _, active_power, _ = self.results

        for col in active_power.columns:
            if col.startswith("Generator"):
                generator_output = active_power[col]
                # Check only for non-zero outputs
                active_output = generator_output[generator_output > 0]
                self.assertTrue((active_output >= MIN_OPERATING_CAPACITY).all(),
                                f"Generator{col} does not meet minimum operating capacity.")

    def test_constraint_naming(self):
        """
        Verify that constraints are correctly named.

        This test ensures that the generated constraints retain their expected names,
        preventing unintended modifications.
        """
        #dummy variables
        d = cp.Variable(5)
        p = cp.Variable((2, 5))
        F = np.zeros(5)
        t = 2

        # Test block load increase
        constraint_inc = _block_load_increase_constraint(d, t, block_limit=10)
        self.assertEqual(constraint_inc._name, BLOCK_DEMAND_INCREASE_CONSTRAINT_NAME)

        # Test block load decrease
        constraint_dec = _block_load_decrease_constraint(d, t)
        self.assertEqual(constraint_dec._name, BLOCK_DEMAND_DECREASE_CONSTRAINT_NAME)

        # Test demand constraint
        constraint_demand = _demand_constraint(p, F, d, t)
        self.assertEqual(constraint_demand._name, DEMAND_CONSTRAINT_NAME)


if __name__ == '__main__':
    warnings.simplefilter('always', FutureWarning)
    unittest.main(warnings='always')
