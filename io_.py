import io
import os
import pandas as pd
import plotly.graph_objs as go
import numpy as np
import pytz
import requests

DIR = os.path.dirname(__file__)
import json
# from config import *


def get_ngeso_wind_day_ahead():
    """
    Retrieves the National Grid ESO wind forecast data for the next day ahead from the API.

    Returns:
    ----------
    pd.DataFrame: A pandas DataFrame containing the wind forecast data.

    """
    # Set the URL of the dataset
    url = 'https://data.nationalgrideso.com/api/3/action/datastore_search?resource_id=b2f03146-f05d-4824-a663-3a4f36090c71'

    # Make the curl request using requests
    response = requests.get(url)

    # Determine the encoding of the response content
    encoding = response.encoding or 'utf-8'  # fallback to utf-8 if encoding not provided

    # Decode the bytes string into a regular string using the appropriate encoding
    content = response.content.decode(encoding)

    return pd.DataFrame.from_dict(json.loads(content)['result']['records'])


def get_historic_demand_wind_solar():
    """
    Retrieves the National Grid ESO demand forecast data for the next two days ahead from the API.

    Returns:
    ----------
    Tuple[pd.Series, pd.Series, pd.Series]: A tuple containing the demand forecast data for wind, solar, and overall demand.
    """
    # Set the URL of the dataset
    url = 'https://data.nationalgrideso.com/backend/dataset/8f2fe0af-871c-488d-8bad-960426f24601/resource/bb44a1b5-75b1-4db2-8491-257f23385006/download/demanddata.csv'

    # If data has been previously retrieved and saved, load it from file instead of making a new request
    if os.path.exists('./_demand_wind_solar.p'):
        response_data = pd.read_pickle('./_demand_wind_solar.p')
    else:
        # Make the curl request using requests
        response = requests.get(url)

        # Determine the encoding of the response content
        encoding = response.encoding or 'utf-8'  # fallback to utf-8 if encoding not provided

        # Parse the CSV response into a DataFrame
        response_data = pd.read_csv(io.StringIO(response.text))

        # Convert data types for selected columns
        response_data = response_data.astype({
            'SETTLEMENT_DATE': 'datetime64[ns]',
            'SETTLEMENT_PERIOD': 'int',
            'ND': 'int',
            'TSD': 'int',
            'ENGLAND_WALES_DEMAND': 'int',
            'EMBEDDED_WIND_GENERATION': 'int',
            'EMBEDDED_WIND_CAPACITY': 'int',
            'EMBEDDED_SOLAR_GENERATION': 'int',
            'EMBEDDED_SOLAR_CAPACITY': 'int',
            'NON_BM_STOR': 'int',
            'PUMP_STORAGE_PUMPING': 'int',
            'IFA_FLOW': 'int',
            'IFA2_FLOW': 'int',
            'BRITNED_FLOW': 'int',
            'MOYLE_FLOW': 'int',
            'EAST_WEST_FLOW': 'int',
            'NEMO_FLOW': 'int',
            'NSL_FLOW': 'int',
            'ELECLINK_FLOW': 'int'
        })

        # Select and rename relevant columns
        response_data = response_data[['SETTLEMENT_DATE', 'SETTLEMENT_PERIOD', 'ND', 'EMBEDDED_WIND_GENERATION', 'EMBEDDED_SOLAR_GENERATION']].copy()

        # Generate a DatetimeIndex for the data
        datetime_range = pd.date_range(response_data['SETTLEMENT_DATE'].iloc[0],
                                       response_data['SETTLEMENT_DATE'].iloc[-1] +
                                       pd.to_timedelta(1, 'day'),
                                       freq='30min', inclusive='left', tz=pytz.timezone('Europe/London'))

        # Add local and UTC timestamps as columns to the DataFrame
        response_data['datetime_local'] = datetime_range
        response_data['datetime'] = datetime_range.tz_convert('UTC')

        # Set the index of the DataFrame to be the UTC timestamp, and select the relevant columns
        response_data = response_data.set_index('datetime')[['EMBEDDED_WIND_GENERATION', 'EMBEDDED_SOLAR_GENERATION', 'ND']].copy()

        # Save the DataFrame to file for future use
        response_data.to_pickle('./_demand_wind_solar.p')

    # Return the relevant columns from data
    return response_data['EMBEDDED_WIND_GENERATION']._set_name('wind'), \
        response_data['EMBEDDED_SOLAR_GENERATION']._set_name('solar'), \
        response_data['ND']._set_name('forecasted demand')


def generate_active_power_inputs(DEMAND_AMPLITUDE, WIND_CAPACITY, T):
    """
    Generates random input data for active power simulations.

    Returns:
    ----------
    tuple: A tuple containing the generated data in the following order: demand, wind, generators.

    """
    random_seed = 230425
    np.random.seed(random_seed)

    # Generate the sinusoidal component of the demand curve
    daily_amplitude = DEMAND_AMPLITUDE
    daily_offset = 2 * daily_amplitude
    daily_period = 48
    demand = daily_amplitude * np.sin(2 * np.pi / daily_period * np.arange(T)) + daily_offset

    wind_capacity = WIND_CAPACITY  # MW
    wind = wind_capacity * np.random.rand(T)

    return demand, wind


def sample_generators(num_generators=15, total_capacity=47000, min_percentage=0.15) -> pd.DataFrame:
    """
    Generate a pandas DataFrame with simulated data for a given number of power generators.
     The DataFrame contains information on each generator's minimum and maximum power output, start-up cost,
     fuel cost, minimum on-time, minimum off-time, and name.

    Parameters
    ----------
    num_generators : int, optional
        The number of generators to simulate. Default is 15.
    total_capacity : int, optional
        The total capacity of all generators combined in MW. Default is 47000.
    min_percentage : float, optional
        The minimum power output of each generator as a percentage of its maximum output. Default is 0.

    Returns
    -------
    pd.DataFrame
        A pandas DataFrame with the following columns:
        - 'Name': str
            The name of the generator.
        - 'Minimum power output': float
            The minimum power output of the generator in MW.
        - 'Maximum power output': float
            The maximum power output of the generator in MW.
        - 'Start-up cost': int
            The start-up cost of the generator in GBP.
        - 'Fuel cost': int
            The fuel cost of the generator in GBP/MWh.
        - 'Minimum on-time': int
            The minimum time the generator must run once it is started, in half hours.
        - 'Minimum off-time': int
            The minimum time the generator must be off once it is stopped, in half hours.

    """
    np.random.seed(230504)
    # Generate random capacities for each generator
    Gmax = np.random.randint(1000, 5000, size=num_generators).astype('float64')

    # Compute the scaling factor to normalise the capacities to the total capacity
    scaling_factor = (total_capacity / np.sum(Gmax)).astype('float64')

    # Normalise the capacities
    Gmax *= scaling_factor

    Gmin = Gmax * min_percentage  # Minimum power output
    Cstart = np.arange(10, 10 * num_generators + 1, 10)  # Start-up cost
    Cfuel = np.arange(10, 10 * num_generators + 1, 10)  # Fuel cost
    Cminon = np.full((num_generators,), 4)  # Minimum on-time
    Cminoff = np.full((num_generators,), 2)  # Minimum off-time

    generators = pd.DataFrame({
        'Name': [f'Generator {g}' for g in range(len(Gmin))],
        'Minimum power output': Gmin,
        'Maximum power output': Gmax,
        'Start-up cost': Cstart,
        'Fuel cost': Cfuel,
        'Minimum on-time': Cminon,
        'Minimum off-time': Cminoff,
    })

    return generators


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



