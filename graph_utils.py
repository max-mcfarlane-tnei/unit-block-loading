import os

import pandas as pd
from plotly import express as px

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
                               y=['demand', 'wind', 'solar', 'net demand', 'net generation', 'block demand'] + generators['Name'].tolist())
    active_power_fig.update_layout(xaxis_title='Time', yaxis_title='MW',
                                   title='Active Power Inputs')
    return active_power_fig
