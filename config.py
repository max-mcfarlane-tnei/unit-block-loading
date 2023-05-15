import datetime

import pandas as pd
import pytz

T = 48 * 7  # Number of time periods
N = 5  # Number of generating units
DEMAND_AMPLITUDE = 150
WIND_CAPACITY = 50

input_path = './unitcomittment.xlsx'
