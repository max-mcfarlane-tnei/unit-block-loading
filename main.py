import os

import pandas as pd
import plotly.subplots

import config
import io_
import optimisation
from config import *
import graph_utils

DIR = os.path.dirname(__file__)


def run_basic_example():
    """
    Runs a basic unit commitment case optimization process.
    :return:
    """

    # Get historic wind, solar, and demand data
    wind, solar, demand = io_.get_historic_demand_wind_solar()

    # Limit the data to a certain time period specified by 'config.T'
    wind, solar, demand = wind.iloc[:config.T], solar.iloc[:config.T], demand.iloc[:config.T]

    # Sample generators based on the number of generators ('N') and total capacity
    generators = io_.sample_generators(num_generators=N, total_capacity=(demand - wind - solar).max())

    # Plot the active power generation using wind, solar, and demand data
    active_power_plot = io_.plot_active_power_generation(wind, solar, demand)

    # Uncomment the following line if you want to show the active power plot
    # active_power_plot.show()

    # Calculate the total renewable power output by summing wind and solar power
    renewables = wind + solar

    # Create sample block loading targets
    block_loading_targets = pd.Series({'time': demand.index[-1], 'volume': demand[-1]})

    # Build the optimization problem with demand, renewables, generators and block loading targets
    prob, u, c, p, d = optimisation.build(demand, renewables, generators, block_loading_targets)

    # Solve the optimization problem
    prob, u, c, p, d = optimisation.solve(prob, u, c, p, d)

    # Check if the problem has an optimal solution
    if prob.status != 'optimal':
        # Relax the constraints if the problem is infeasible
        constraint_status, constraint_group_problem = optimisation.relax_constraints(prob)
        exit()

    d = pd.Series(d.value, index=demand.index)

    # Create a dataframe with the start and end times for each task
    u = pd.DataFrame(u.value, index=generators['Name'], columns=demand.index)
    windows = u.diff(axis=1).fillna(u)
    windows_melted = windows.melt(var_name='time', value_name='action', ignore_index=False)
    windows_melted['action'] = windows_melted['action'].round(0)
    windows_melted = windows_melted.query('action!=0')

    # Generate a Gantt chart based on the task windows
    decision_fig = graph_utils.generate_gantt(windows_melted, u.columns)

    # Create dataframes for power output and cost for each generator and time period
    p = pd.DataFrame(p.value, index=generators['Name'], columns=demand.index)
    c = pd.DataFrame(c.value, index=generators['Name'], columns=demand.index)

    # Combine wind, solar, demand, and power output data into a single dataframe
    active_power = pd.concat([wind, solar, demand], axis=1)
    active_power = pd.concat([active_power, p.T], axis=1)

    # Calculate net demand and net generation by summing the power output of all generators
    active_power['net demand'] = demand - wind - solar
    active_power['net generation'] = active_power[generators['Name']].sum(axis=1)

    # Generate a chart showing the active power generation
    active_power_fig = graph_utils.active_power_chart(active_power, generators)

    # Create a Plotly subplot
    subplots = plotly.subplots.make_subplots(rows=2, cols=1, row_heights=[0.5, 1], shared_xaxes=True)

    # Add the decision Gantt chart to the first subplot
    subplots.add_traces(decision_fig.data, rows=[1] * len(decision_fig.data), cols=[1] * len(decision_fig.data))

    # Add the active power chart to the second subplot
    subplots.add_traces(active_power_fig.data, rows=[2] * len(active_power_fig.data),
                        cols=[1] * len(active_power_fig.data))

    # Update the x-axis type to 'date' for time-based plotting
    subplots.update_xaxes(type='date')

    # Show the subplot containing both the decision and active power charts
    subplots.show()


if __name__ == '__main__':
    run_basic_example()
