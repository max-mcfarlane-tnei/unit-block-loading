# import os
#
# # from config import *
# from run import run_basic_example
#
# DIR = os.path.dirname(__file__)
#
# if __name__ == '__main__':
#     cases = []
#     figs = []
#     for block_limit in [500, 750, 1000]:
#         for generators_inactive in [0, 1, 2]:
#             decision_fig, active_power_fig, subplot_fig = run_basic_example(
#                 t=48 * 6, n=3, restart_targets=((2, 0.6), (4, 1)),
#                 block_limit=block_limit, generators_inactive=generators_inactive
#             )
#             cases = [(block_limit, generators_inactive)]
#             figs.append({
#                 'decision_fig': decision_fig, 'active_power_fig': active_power_fig, 'subplot_fig': subplot_fig
#             })
