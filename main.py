import os

import plotly.express as px
import plotly.subplots

import config
import io_
import optimisation
from config import *

DIR = os.path.dirname(__file__)


def generate_gantt(_windows, times):
    """

    :param _windows: pd.DataFrame
        A pandas DataFrame with the following columns:
            - index: str
                Generator name.
            - time: datetime
                Date and time of action.
            - action: int
                Neg/Pos integer indicating startup/shutdown of generator.
                1 = startup
                -1 = shutdown
    """
    generator_names = []
    start_times = []
    end_times = []
    for g_, w in _windows.groupby('Name'):
        if len(w['time']) % 2 > 0:
            w = pd.concat([w,
                           pd.DataFrame({'time': [times[-1] + pd.to_timedelta(30, unit='m')], 'action': [-1]},
                                        index=[g_])], axis=0)
        for a in w.itertuples():
            if a.action == 1:
                generator_names += [a.Index]
                start_times += [a.time]
            elif a.action == -1:
                end_times += [a.time]

    # Create a dataframe with the start and end times of each generator
    gantt_chart = pd.DataFrame({'Generator': generator_names,
                                'Start': start_times,
                                'End': end_times})
    # Convert the Start and End columns to datetime format
    gantt_chart['Start'] = pd.to_datetime(gantt_chart['Start'])
    gantt_chart['End'] = pd.to_datetime(gantt_chart['End'])

    # Create the Gantt chart
    decision_fig = px.timeline(gantt_chart, x_start="Start", x_end="End", y="Generator", color="Generator")
    decision_fig.update_layout(xaxis_title='Time', yaxis_title='Generator',
                               title='Generator Schedule')
    return decision_fig


def active_power_chart(active_power, generators):
    # Plot multiple lines
    active_power_fig = px.line(active_power,
                               y=['demand', 'wind', 'solar', 'net demand', 'net generation'] + generators['Name'].tolist())
    active_power_fig.update_layout(xaxis_title='Time', yaxis_title='MW',
                                   title='Active Power Inputs')
    return active_power_fig


# Define the main function for running the basic example
def run_basic_example():
    """
    Process for solving a basic unit commitment case.
    Inputs:
    - sinusoidal gross demand
    - random wind output
    - sample generators in unitcomittment.xlsx (generators)
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

    # Build the optimization problem with demand, renewables, and generators
    prob, u, c, p = optimisation.build(demand, renewables, generators)

    # Solve the optimization problem
    prob, u, c, p = optimisation.solve(prob, u, c, p)

    # Check if the problem has an optimal solution
    if prob.status != 'optimal':
        # Relax the constraints if the problem is infeasible
        constraint_status, constraint_group_problem = optimisation.relax_constraints(prob)
        exit()

    # Create a dataframe with the start and end times for each task
    u = pd.DataFrame(u.value, index=generators['Name'], columns=demand.index)
    windows = u.diff(axis=1).fillna(u)
    windows_melted = windows.melt(var_name='time', value_name='action', ignore_index=False)
    windows_melted['action'] = windows_melted['action'].round(0)
    windows_melted = windows_melted.query('action!=0')

    # Generate a Gantt chart based on the task windows
    decision_fig = generate_gantt(windows_melted, u.columns)

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
    active_power_fig = active_power_chart(active_power, generators)

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
