import os
DIR = os.path.dirname(__file__)


class InfeasibleSolutionException(Exception):
    msg = 'Infeasible solution'
