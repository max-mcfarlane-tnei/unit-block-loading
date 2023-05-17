import os

import pandas as pd
import plotly.subplots
from plotly import express as px
import plotly.graph_objects as go
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
    # # Plot multiple lines
    # active_power_fig = px.line(active_power,
    #                            y=['forecasted demand', 'block demand'])
    # active_power_fig.update_layout(xaxis_title='Time', yaxis_title='MW',
    #                                title='Active Power Inputs')
    # Plot multiple lines
    active_power_fig = px.area(active_power,
                               y=['wind', 'solar'] + generators)
    active_power_fig.update_layout(xaxis_title='Time', yaxis_title='MW',
                                   title='Active Power Inputs')
    # Add line plots using Plotly Graph Objects
    active_power_fig.add_trace(go.Scatter(x=active_power.index, y=active_power['forecasted demand'], mode='lines', name='forecasted demand'))
    active_power_fig.add_trace(go.Scatter(x=active_power.index, y=active_power['block demand'], mode='lines', name='block demand'))

    return active_power_fig


def visualise(u, p, active_power, generators, target_checkpoints, block_limit, generators_inactive):
    """
    Visualizes the optimization results by generating Gantt charts for generator on/off status and active power generation.

    Args:
        u (pd.DataFrame): Binary variable indicating generator on/off status.
        active_power (pd.DataFrame): DataFrame representing active power generation.
        generators (pd.DataFrame): DataFrame representing generator and their characteristics.

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
    active_power_fig = active_power_chart(active_power, generators['Name'].tolist())

    for line in target_checkpoints.itertuples():
        active_power_fig.add_shape(
            type="line",
            x0=line.Index,
            y0=0,
            x1=line.Index,
            y1=max([sum(v) for v in list(zip(*[d['y'] for d in active_power_fig['data']]))]),
            line=dict(color="red", width=10))

    dispatch = p.T.melt(var_name='generator', value_name='MW', ignore_index=False).reset_index()
    dispatch['MWh'] = dispatch['MW'] / (pd.to_timedelta(1, unit='h')/pd.to_timedelta(pd.infer_freq(p.columns)))
    dispatch['£/MWh'] = dispatch['generator'].map(generators.set_index('Name')['Fuel cost'].to_dict())
    dispatch['£'] = dispatch['£/MWh'] * dispatch['MWh']
    dispatch['m£'] = dispatch['£']/1e6
    dispatch_costs = dispatch.groupby('datetime')['m£'].sum()
    cumulative_dispatch_costs = dispatch_costs.cumsum()

    # Plot multiple lines
    cumulative_cost_fig = px.line(cumulative_dispatch_costs)
    cumulative_cost_fig.update_layout(xaxis_title='Time', yaxis_title='m£',
                                   title='Cumulative cost')

    # Create a Plotly subplot
    subplots_fig = plotly.subplots.make_subplots(rows=3, cols=1, row_heights=[0.5, 0.5, 1], shared_xaxes=True,
                                                 subplot_titles=("Generator Schedule", "Fuel Cost", "Dispatch and Demand"))

    # Add the decision Gantt chart to the first subplot
    subplots_fig.add_traces(decision_fig.data, rows=[1] * len(decision_fig.data), cols=[1] * len(decision_fig.data))
    subplots_fig.add_traces(cumulative_cost_fig.data, rows=[2] * len(cumulative_cost_fig.data), cols=[1] * len(cumulative_cost_fig.data))

    subplots_fig.add_traces(active_power_fig.data, rows=[3] * len(active_power_fig.data),
                        cols=[1] * len(active_power_fig.data))

    # Update the x-axis type to 'date' for time-based plotting
    subplots_fig.update_xaxes(type='date')

    # Set y-axis titles for each subplot
    subplots_fig.update_yaxes(title_text='Generator Name', row=1, col=1)
    subplots_fig.update_yaxes(title_text='Cumulative Fuel Cost [m£]', row=2, col=1)
    subplots_fig.update_yaxes(title_text='Dispatch Volume [MW]', row=3, col=1)

    # Set title for the entire figure
    subplots_fig.update_layout(title=f'Block limit: {block_limit}, Inactive generators: {generators_inactive}')

    # # # Show the subplot containing both the decision and active power charts
    # subplots_fig.show()

    return decision_fig, cumulative_cost_fig, active_power_fig, subplots_fig
