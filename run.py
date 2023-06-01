import os

import pandas as pd

import config
import optimisation
from graph_utils import visualise
from util import prepare_inputs, process_outputs

DIR = os.path.dirname(__file__)


def run_basic_example(
        t=config.T,
        n=config.N,
        restart_targets=config.RESTART_TARGETS,
        block_limit=config.BLOCK_LIMIT,
        generators_inactive=0,
        min_operating_capacity=0.15,
):
    """
    Runs a basic unit commitment case optimization process.

    Parameters:
    t (int, optional): The time period to consider for the optimization process. Default is config.T.
    n (int, optional): The number of generators to consider for the optimization process. Default is config.N.
    restart_targets (list, optional): List of restart targets for block loading. Default is config.RESTART_TARGETS.
    block_limit (float, optional): The block limit for block loading. Default is config.BLOCK_LIMIT.
    generators_inactive (int, optional): The number of inactive generators. Default is 0.
    min_operating_capacity (float, optional): The minimum operating capacity for generators. Default is 0.15.

    Returns:
    tuple: A tuple containing four figures - decision_fig, cumulative_cost_fig, active_power_fig, subplot_fig.

    """
    demand, wind, solar, renewables, generators, target_checkpoints, block_loading_targets = prepare_inputs(
        t, n, restart_targets, block_limit, generators_inactive, min_operating_capacity
    )

    # Build the optimization problem with demand, renewables, generators and block loading targets
    prob, u, c, p, d = optimisation.build(demand, renewables, generators, target_checkpoints, block_loading_targets, t)

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

    decision_fig, cumulative_cost_fig, active_power_fig, subplot_fig = visualise(
        u, p, active_power, generators,
        target_checkpoints, block_limit,
        generators_inactive
    )

    return decision_fig, cumulative_cost_fig, active_power_fig, subplot_fig, active_power, c
