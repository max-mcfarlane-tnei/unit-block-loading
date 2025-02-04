import os
import numpy as np
import pandas as pd
import config
import io_

DIR = os.path.dirname(__file__)


def define_block_load_targets(demand, targets=config.RESTART_TARGETS, block_limit=config.BLOCK_LIMIT):
    """
    Defines block loading targets based on the given demand data.

    Parameters:
    demand (pd.Series): Time series data representing the demand.
    targets (list, optional): List of target configurations. Each configuration is a tuple of (target_days, target_proportion).
                              Default is config.RESTART_TARGETS.
    block_limit (float, optional): The block limit for block loading. Default is config.BLOCK_LIMIT.

    Returns:
    tuple: A tuple containing the following:
        - target_checkpoints (pd.DataFrame): A DataFrame containing the block loading targets, including the target datetime
                                             and volume.
        - block_loading_targets (pd.Series): A Series containing the block loading targets per timestep.
    """
    # Convert the index of the demand series to a pandas datetime if needed
    first_date = pd.to_datetime(demand.sort_index().index[0])

    # Initialize a list to store the block loading targets
    target_checkpoints = []

    # Iterate over each target configuration in the config.TARGETS list
    for target_ in targets:
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
            'time': pd.Timestamp(target_datetime),  # Ensures datetime dtype
            'volume': float(target_volume),  # Ensures float dtype
            'block_limit': float(block_limit)  # Ensures float dtype
        }, dtype=object)  # Explicitly set dtype to object to avoid inference

        # Append the block loading targets series to the list
        target_checkpoints.append(target_checkpoints_)

    # Concatenate the block loading targets list into a single DataFrame
    target_checkpoints = pd.concat(target_checkpoints, axis=1).T

    # Transpose the DataFrame and set the 'time' column as the index
    target_checkpoints = target_checkpoints.set_index('time')

    # Create a block loading targets series per timestep
    _block_target_t = [
        ((demand.index < r.Index), r.volume) for r in target_checkpoints.sort_index(ascending=False).itertuples()
    ]
    block_loading_targets = pd.Series(index=demand.index, data=[0] * len(demand), dtype='float64')  # Explicitly setting the dtype here removes FutureWarning of incompatible dtype
    for idx_mask, block_target_ in _block_target_t:
        block_loading_targets[idx_mask] = block_target_

    return target_checkpoints, block_loading_targets


def prepare_inputs(t=config.T, n=config.N, targets=config.RESTART_TARGETS, block_limit=config.BLOCK_LIMIT,
                   generators_inactive=0, min_operating_capacity=0.15):
    """
    Prepare inputs for the application by retrieving data, sampling generators, and calculating relevant values.

    Parameters:
    t (int, optional): The time period to consider for the preparation. Default is config.T.
    n (int, optional): The number of generators to sample. Default is config.N.
    targets (list, optional): The restart targets for block loading. Default is config.RESTART_TARGETS.
    block_limit (float, optional): The block limit for block loading. Default is config.BLOCK_LIMIT.

    Returns:
    tuple: A tuple containing the following prepared inputs:
        - demand (DataFrame): Historic demand data limited to the specified time period.
        - renewables (DataFrame): Total renewable power output calculated from wind and solar data.
        - generators (DataFrame): Sampled generators based on the number of generators and total capacity.
        - target_checkpoints (list): Checkpoints for defining block loading targets.
        - block_loading_targets (DataFrame): Block loading targets for the demand.
    """
    # Get historic wind, solar, and demand data
    wind, solar, demand = io_.get_historic_demand_wind_solar()

    SCO_POP = 5.5e6
    UK_POP = 67e6

    proportion = SCO_POP / UK_POP

    # Limit the data to a certain time period specified by t
    wind = wind.iloc[:t] * proportion
    solar = solar.iloc[:t] * proportion
    demand = demand.iloc[:t] * proportion

    # Ensure dtypes are explicitly set
    wind = wind.astype('float64')
    solar = solar.astype('float64')
    demand = demand.astype('float64')

    # Sample generators based on the number of generators ('N') and total capacity
    generators = io_.sample_generators(num_generators=n, total_capacity=(demand - wind - solar).max(),
                                       min_percentage=min_operating_capacity)

    np.random.seed(230516)
    generators_offline = np.random.randint(0, n, generators_inactive)
    generators = generators[~generators.index.to_series().isin(generators_offline)].reset_index(drop=True)

    # Calculate the total renewable power output by summing wind and solar power
    renewables = (wind + solar).astype('float64')

    # Compile block loading targets
    target_checkpoints, block_loading_targets = define_block_load_targets(demand, targets, block_limit)

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

    # Ensure dtypes are explicitly set
    active_power = active_power.astype('float64')

    return active_power