import datetime

import pandas as pd
import pytz

DAYS = 3
T = 48 * DAYS  # Number of time periods
N = 10  # Number of generating units
TARGETS = ((1, 0.6), (2, 1))
DEMAND_AMPLITUDE = 150
WIND_CAPACITY = 50
BLOCK_LIMIT = 500

input_path = './unitcomittment.xlsx'
