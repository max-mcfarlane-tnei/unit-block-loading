import datetime

import pandas as pd
import pytz

DAYS = 5
T = 48 * DAYS  # Number of time periods
N = 5  # Number of generating units
TARGETS = ((2, 0.6), (4, 1))
DEMAND_AMPLITUDE = 150
WIND_CAPACITY = 50
BLOCK_LIMIT = 300

input_path = './unitcomittment.xlsx'
