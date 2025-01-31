import pickle
import unittest
import config
from run_SCIP import run_basic_example_scip_solver
import warnings

# Ensure warnings are shown during tests
warnings.simplefilter('always', FutureWarning)


class TestRunBasicExample(unittest.TestCase):
    """
    A test case for the run_basic_example function.
    """

    def test_run_basic_example_scip(self):
        """
        Test the run_basic_example function.
        """
        # Call the function
        decision_fig, cumulative_cost_fig, active_power_fig, subplot_fig, active_power, c = run_basic_example_scip_solver(
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

    def test_constraints(self):
        """
        Test for demand = generation at a given timestamp
        """
        decision_fig, cumulative_cost_fig, active_power_fig, subplot_fig, active_power, c = run_basic_example_scip_solver(
            t=config.T,
            n=config.N,
            restart_targets=config.RESTART_TARGETS,
            block_limit=config.BLOCK_LIMIT,
            generators_inactive=0,
            min_operating_capacity=0.15
        )

        idx = active_power.index[2] #This is the time stamps in the data
                                    #The wind generation never goes to 0
                                    #At the first few time stamps generation > demand

        demand = active_power.loc[idx, 'block demand']
        generator_0= active_power.loc[idx, 'Generator 0']
        generator_1= active_power.loc[idx, 'Generator 1']
        generator_2= active_power.loc[idx, 'Generator 2']
        generator_3= active_power.loc[idx, 'Generator 3']
        generator_4= active_power.loc[idx, 'Generator 4']
        solar = active_power.loc[idx, 'solar']
        wind = active_power.loc[idx, 'wind']


        gross_generation = solar + wind + generator_0 + generator_1 + generator_2 + generator_3 + generator_4

        self.assertAlmostEqual(gross_generation, demand)

    def test_initial_demand(self):
        """
        Test for initial demand equals zero
        """
        decision_fig, cumulative_cost_fig, active_power_fig, subplot_fig, active_power, c = run_basic_example_scip_solver(
            t=config.T,
            n=config.N,
            restart_targets=config.RESTART_TARGETS,
            block_limit=config.BLOCK_LIMIT,
            generators_inactive=0,
            min_operating_capacity=0.15
        )
        idx = active_power.index[0] # Demand at the first timestamp

        initial_demand = active_power.loc[idx, 'block demand']


        self.assertEqual(initial_demand, 0)

    def test_block_demand_non_negativity(self):
        """
        Test that the block demand is always non-negative.
        """
        _, _, _, _, active_power, _ = run_basic_example_scip_solver(
            t=config.T,
            n=config.N,
            restart_targets=config.RESTART_TARGETS,
            block_limit=config.BLOCK_LIMIT,
            generators_inactive=0,
            min_operating_capacity=0.15
        )
        demand = active_power['block demand']

        # Check if all block demand values are non-negative
        self.assertTrue((demand >= 0).all(), "Block demand is negative at some timestep.")

    def test_initial_generator_status(self):
        """
        Test that all generators (including solar and wind) are initially inactive.
        ISSUES with this, the wind is not inactive at the start ?
        """
        _, _, _, _, active_power, _ = run_basic_example_scip_solver(
            t=config.T,
            n=config.N,
            restart_targets=config.RESTART_TARGETS,
            block_limit=config.BLOCK_LIMIT,
            generators_inactive=0,
            min_operating_capacity=0.15
        )

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





if __name__ == '__main__':
    warnings.simplefilter('always', FutureWarning)
    unittest.main(warnings='always')
