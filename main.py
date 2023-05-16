import os

import pandas as pd

import config
import graph_utils
import io_
import optimisation
from config import *
from graph_utils import visualise

DIR = os.path.dirname(__file__)


def define_block_load_targets(demand):
    """
    Defines block loading targets based on the given demand data.

    Args:
        demand (pd.Series): Time series data representing the demand.

    Returns:
        pd.DataFrame: A DataFrame containing the block loading targets, including the target datetime and volume.
        pd.Series: A Series containing the block loading targets per timestep.
    """

    # Create block loading targets for multiple target configurations

    # Convert the index of the demand series to a pandas datetime if needed
    first_date = pd.to_datetime(demand.sort_index().index[0])

    # Initialize a list to store the block loading targets
    target_checkpoints = []

    # Iterate over each target configuration in the config.TARGETS list
    for target_ in config.TARGETS:
        target_days = target_[0]
        target_proportion = target_[1]

        # Set the target datetime by adding a timedelta to the first date
        target_datetime = first_date + pd.Timedelta(days=target_days)

        # Calculate the absolute time difference between each index value and the target datetime
        time_diff = abs((demand.index - target_datetime).values)

        # Find the index label corresponding to the minimum time difference
        closest_index = time_diff.argmin()

        # Retrieve the target datetime from the demand index at the closest index
        target_datetime = demand.index[closest_index]

        # Calculate the target volume based on the demand value at the closest index multiplied by the target proportion
        target_volume = demand[demand.index[closest_index]] * target_proportion

        # Create a series containing the target datetime and volume
        target_checkpoints_ = pd.Series({
            'time': target_datetime,
            'volume': target_volume,
            'block_limit': config.BLOCK_LIMIT
        })

        # Append the block loading targets series to the list
        target_checkpoints.append(target_checkpoints_)

    # Concatenate the block loading targets list into a single DataFrame
    target_checkpoints = pd.concat(target_checkpoints, axis=1)

    # Transpose the DataFrame and set the 'time' column as the index
    target_checkpoints = target_checkpoints.T.set_index('time')

    # Create a block loading targets series per timestep
    _block_target_t = [
        ((demand.index < r.Index), r.volume) for r in target_checkpoints.sort_index(ascending=False).itertuples()
    ]
    block_loading_targets = pd.Series(index=demand.index, data=[0] * len(demand))
    for idx_mask, block_target_ in _block_target_t:
        block_loading_targets[idx_mask] = block_target_

    return target_checkpoints, block_loading_targets


def prepare_inputs():
    """
    Prepares inputs for the application by retrieving data, sampling generators, and calculating relevant values.

    Returns:
    tuple: A tuple containing the following prepared inputs:
        - demand (DataFrame): Historic demand data limited to a specified time period.
        - wind (DataFrame): Historic wind power data limited to a specified time period.
        - solar (DataFrame): Historic solar power data limited to a specified time period.
        - renewables (DataFrame): Total renewable power output calculated from wind and solar data.
        - generators (DataFrame): Sampled generators based on the number of generators and total capacity.
        - target_checkpoints (list): Checkpoints for defining block loading targets.
        - block_loading_targets (DataFrame): Block loading targets for the demand.
    """
    # Get historic wind, solar, and demand data
    wind, solar, demand = io_.get_historic_demand_wind_solar()

    # Limit the data to a certain time period specified by 'config.T'
    wind, solar, demand = wind.iloc[:config.T], solar.iloc[:config.T], demand.iloc[:config.T]

    # Sample generators based on the number of generators ('N') and total capacity
    generators = io_.sample_generators(num_generators=N, total_capacity=(demand - wind - solar).max())

    lines = io_.generate_transmission_lines(generators)

    # # Plot the active power generation using wind, solar, and demand data
    # active_power_plot = graph_utils.plot_active_power_generation(wind, solar, demand)
    #
    # # Uncomment the following line if you want to show the active power plot
    # active_power_plot.show()

    # Calculate the total renewable power output by summing wind and solar power
    renewables = wind + solar

    # Compile block loading targets
    target_checkpoints, block_loading_targets = define_block_load_targets(demand)

    return demand, wind, solar, renewables, generators, target_checkpoints, block_loading_targets


def process_outputs(wind, solar, demand, generators, p, d):
    """
    Processes the outputs of the application by combining data and calculating net demand and net generation.

    Parameters:
        wind (DataFrame): Wind power data.
        solar (DataFrame): Solar power data.
        demand (DataFrame): Historic demand data.
        generators (DataFrame): Sampled generators data.
        p (DataFrame): Power output data of generators.
        d (Series): Block demand data.

    Returns:
        DataFrame: A DataFrame containing the processed outputs, including net demand and net generation.
    """
    # Combine wind, solar, demand, and power output data into a single dataframe
    active_power = pd.concat([wind, solar, demand], axis=1)
    active_power = pd.concat([active_power, p.T], axis=1)

    # Calculate net demand and net generation by summing the power output of all generators
    active_power['block demand'] = d
    active_power['net demand'] = demand - wind - solar
    active_power['net generation'] = active_power[generators['Name']].sum(axis=1)

    return active_power


def run_basic_example():
    """
    Runs a basic unit commitment case optimization process.
    :return:
    """
    demand, wind, solar, renewables, generators, target_checkpoints, block_loading_targets = prepare_inputs()

    # Build the optimization problem with demand, renewables, generators and block loading targets
    prob, u, c, p, d = optimisation.build(demand, renewables, generators, target_checkpoints, block_loading_targets)

    # Solve the optimization problem
    prob, u, c, p, d = optimisation.solve(prob, u, c, p, d)

    # Create a dataframe for block demand
    d = pd.Series(d.value, index=demand.index)

    # Create a dataframe with the start and end times for each task
    u = pd.DataFrame(u.value, index=generators['Name'], columns=demand.index)

    # Create dataframes for power output and cost for each generator and time period
    p = pd.DataFrame(p.value, index=generators['Name'], columns=demand.index)
    c = pd.DataFrame(c.value, index=generators['Name'], columns=demand.index)

    active_power = process_outputs(wind, solar, demand, generators, p, d)

    visualise(u, active_power, generators['Name'].tolist())


if __name__ == '__main__':
    run_basic_example()
