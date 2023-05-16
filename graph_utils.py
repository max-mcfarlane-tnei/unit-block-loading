import os

import pandas as pd
import plotly.subplots
from plotly import express as px, graph_objs as go

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
                               y=['forecasted demand', 'wind', 'solar', 'net demand', 'net generation', 'block demand'] + generators)
    active_power_fig.update_layout(xaxis_title='Time', yaxis_title='MW',
                                   title='Active Power Inputs')
    return active_power_fig


def visualise(u, active_power, generators):
    """
    Visualizes the optimization results by generating Gantt charts for generator on/off status and active power generation.

    Args:
        u (pd.DataFrame): Binary variable indicating generator on/off status.
        active_power (pd.DataFrame): DataFrame representing active power generation.
        generators (list): List of generator names.

    Returns:
        None
    """

    # Generate task windows based on changes in generator status
    windows = u.diff(axis=1).fillna(u)
    windows_melted = windows.melt(var_name='time', value_name='action', ignore_index=False)
    windows_melted['action'] = windows_melted['action'].round(0)
    windows_melted = windows_melted.query('action!=0')

    # Generate a Gantt chart based on the task windows
    decision_fig = generate_gantt(windows_melted, u.columns)

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


def plot_active_power_generation(wind: pd.Series, solar: pd.Series, demand: pd.Series) -> None:
    """
    Plots the total demand, wind generation, solar generation and net demand.

    Parameters:
    ----------
    wind : pd.Series
        A pandas Series containing the wind generation data in MW.

    solar : pd.Series
        A pandas Series containing the solar generation data in MW.

    demand : pd.Series
        A pandas Series containing the total demand data in MW.

    Returns:
    ----------
    plotly.graph_objs._figure.Figure: A plotly figure object containing the plot.
    """

    # Set the time period to smooth over
    smooth_window = '24h'

    # Apply rolling mean smoothing to the demand, wind, solar, and net series
    smoothed_demand = demand.rolling(smooth_window).mean()
    smoothed_wind = wind.rolling(smooth_window).mean()
    smoothed_solar = solar.rolling(smooth_window).mean()
    smoothed_net = (demand - wind - solar).rolling(smooth_window).mean()

    # Create a new plotly figure object
    fig = go.Figure()

    # Add each of the series to the figure as a line plot
    fig.add_trace(go.Scatter(x=demand.index, y=smoothed_demand, mode='lines', name='Total Demand'))
    fig.add_trace(go.Scatter(x=wind.index, y=smoothed_wind, mode='lines', name='Wind Generation'))
    fig.add_trace(go.Scatter(x=solar.index, y=smoothed_solar, mode='lines', name='Solar Generation'))
    fig.add_trace(go.Scatter(x=demand.index, y=smoothed_net, mode='lines', name='Net Demand'))

    # Update the layout of the figure with appropriate titles and axis labels
    fig.update_layout(title='Total Demand and Renewable Energy Input', xaxis_title='Time', yaxis_title='Power (MW)',
                      legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))

    # Show the figure
    # fig.show()

    # Return the figure object
    return fig
