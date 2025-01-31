import numpy as np

#these are meant to be const but for testing purpose I want to vary them

DAYS = np.random.randint(1, 11)
T = 48 * DAYS  # Number of time periods
N = np.random.randint(1, 11)  # Number of generating units
RESTART_TARGETS = ((2, 0.6), (4, 1))
DEMAND_AMPLITUDE = np.random.randint(100, 200)
WIND_CAPACITY = np.random.randint(10, 100)
BLOCK_LIMIT = np.random.randint(200, 400)

input_path = './unitcomittment.xlsx'

print(f"DAYS: {DAYS}")
print(f"T: {T}")
print(f"N: {N}")
print(f"RESTART_TARGETS: {RESTART_TARGETS}")
print(f"DEMAND_AMPLITUDE: {DEMAND_AMPLITUDE}")
print(f"WIND_CAPACITY: {WIND_CAPACITY}")
print(f"BLOCK_LIMIT: {BLOCK_LIMIT}")

