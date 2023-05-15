import collections

import cvxpy as cp

from config import *
from logger import logger

DEMAND_CONSTRAINT_NAME = 'demand-constraint'
STATUS_CONSTRAINT_NAME = 'status-constraint'
MIN_POWER_CONSTRAINT_NAME = 'min_power-constraint'
MAX_POWER_CONSTRAINT_NAME = 'max_power-constraint'
START_UP_CONSTRAINT_NAME = 'start_up-constraint'
COOL_DOWN_CONSTRAINT_NAME = 'cool_down-constraint'

CONSTRAINT_NAMES = [
    DEMAND_CONSTRAINT_NAME,
    STATUS_CONSTRAINT_NAME,
    MIN_POWER_CONSTRAINT_NAME,
    MAX_POWER_CONSTRAINT_NAME,
    START_UP_CONSTRAINT_NAME,
    COOL_DOWN_CONSTRAINT_NAME
]


def define_constraints(u, c, p, d, F, D, Gmax, Gmin, Cminon, Cminoff, Dtargettime, Dtargetvol, T_=T):
    """
    Define constraints for an optimization problem.

    :param u: Binary variable indicating generator on/off status.
    :param c: Binary variable indicating generator startup status.
    :param p: Variable representing generator power output.
    :param d: Variable representing block load.
    :param F: Variable representing wind power.
    :param D: Variable representing demand.
    :param Gmax: List of maximum generator capacities.
    :param Gmin: List of minimum generator capacities.
    :param Cminon: List of minimum on-time timesteps for generators.
    :param Cminoff: List of minimum off-time timesteps for generators.
    :param T_: Number of timesteps.
    :return: List of constraints and constraints categorized by type in a dictionary.
    """

    def _block_load_constraint(d_, t_, block_limit=10):
        """
        Constraint function for limiting the increase in demand per block.

        Parameters:
        - d_: Variable representing the demand.
        - t_: Timestep index.

        Returns:
        - constraint: Constraint limiting the increase in demand per block.
        """
        constraint = d_[t_ + 1] - d_[t_] <= block_limit

        # Assign a name to the constraint
        constraint._name = 'demand-increase-constraint'

        # Return the constraint
        return constraint

    def _demand_constraint(p_, F_, D_, t_):
        """
        Constraint function for ensuring that generation equals demand at a given timestep.

        Parameters:
        - p_: Power output of generators at the given timestep.
        - F_: Wind power output at the given timestep.
        - D_: Demand at the given timestep.
        - t_: Timestep index.

        Returns:
        - constraint: Constraint ensuring that the total power output of generators and wind power is greater than or equal to demand.
        """

        # Sum the power output of all generators (p_[:, t_]) at timestep t_ and add the wind power (F_[t_])
        # Ensure that the total is greater than or equal to the demand (D_[t_])
        constraint = cp.sum(p_[:, t_]) + F_[t_] >= D_[t_]

        # Assign a name to the constraint
        constraint._name = DEMAND_CONSTRAINT_NAME

        # Return the constraint
        return constraint

    def _status_constraint(Gmin_, Cminon_, u_, c_, p_, i_, t_):
        """
        Constraint function for determining the generator status based on power output.

        Parameters:
        - Gmin_: Minimum power output of the generator.
        - Cminon_: Minimum on-time of the generator.
        - u_: Decision variable representing the on/off status of generators.
        - c_: Decision variable representing the start-up status of generators.
        - p_: Decision variable representing the power output of generators.
        - i_: Generator index.
        - t_: Timestep index.

        Returns:
        - constraint: Constraints determining the generator status based on power output.
        """

        M = 1e6  # Choose a large positive constant

        constraint = [
            p_[i_, t_] <= M * u_[i_, t_],
            # u_[i_, t_] <= c_[i_, t_],
            # u_[i_, t_] >= c_[i_, t_] - (1 - c_[i_, t_]) * M,
        ]
        return constraint

    def _min_power_constraint(Gmin_, u_, p_, i_, t_):
        """
        Constraint function for ensuring that the generator output is at least the minimum power output (Gmin).

        Parameters:
        - Gmin_: Minimum power output of the generator.
        - u_: Decision variable representing the on/off status of generators.
        - p_: Decision variable representing the power output of generators.
        - i_: Generator index.
        - t_: Timestep index.

        Returns:
        - constraint: Constraint ensuring that the generator output is at least the minimum power output (Gmin).
        """

        # Ensure that the power output (p_[i_, t_]) is at least Gmin_[i_] multiplied by the on/off status (u_[i_, t_])
        constraint = Gmin_[i_] * u_[i_, t_] <= p_[i_, t_]

        # Assign a name to the constraint
        constraint._name = MIN_POWER_CONSTRAINT_NAME

        # Return the constraint
        return constraint

    def _max_power_constraint(Gmax_, u_, p_, i_, t_):
        """
        Constraint function for ensuring that the generator output is at most the maximum power output (Gmax).

        Parameters:
        - Gmax_: Maximum power output of the generator.
        - u_: Decision variable representing the on/off status of generators.
        - p_: Decision variable representing the power output of generators.
        - i_: Generator index.
        - t_: Timestep index.

        Returns:
        - constraint: Constraint ensuring that the generator output is at most the maximum power output (Gmax).
        """

        # Ensure that the power output (p_[i_, t_]) is at most Gmax_[i_] multiplied by the on/off status (u_[i_, t_])
        constraint = p_[i_, t_] <= Gmax_[i_] * u_[i_, t_]

        # Assign a name to the constraint
        constraint._name = MAX_POWER_CONSTRAINT_NAME

        # Return the constraint
        return constraint

    def _start_up_constraint(Cminon_, u_, c_, i_, t_):
        """
        Constraint function for ensuring that the generator is on for at least Cminon timesteps.

        Parameters:
        - Cminon_: Minimum on-time of the generator.
        - u_: Decision variable representing the on/off status of generators.
        - c_: Decision variable representing the start-up status of generators.
        - i_: Generator index.
        - t_: Timestep index.

        Returns:
        - constraint: Constraint ensuring that the generator is on for at least Cminon timesteps.
        """

        # If the current timestep is greater than or equal to Cminon_[i_]
        if t_ >= Cminon_[i_]:
            # Sum the startup events (c_) over the previous Cminon_[i_] timesteps and ensure it is at least Cminon_[i_]
            constraint = cp.sum(c_[i_, t_ - Cminon_[i_] + 1: t_ + 1]) >= Cminon_[i_] * u_[i_, t_]
        else:
            # If the current timestep is less than Cminon_[i_]
            # Sum all the previous startup events (c_) up to the current timestep and ensure it is at least (t_ + 1)
            constraint = cp.sum(c_[i_, : t_ + 1]) >= (t_ + 1) * u_[i_, t_]

        # Assign a name to the constraint
        constraint._name = START_UP_CONSTRAINT_NAME

        # Return the constraint
        return constraint

    def _cool_down_constraint(Cminoff_, u_, i_, t_):
        """
        Constraint function for ensuring that the generator is off for at least Cminoff timesteps.

        Parameters:
        - Cminoff_: Minimum off-time of the generator.
        - u_: Decision variable representing the on/off status of generators.
        - i_: Generator index.
        - t_: Timestep index.

        Returns:
        - constraint: Constraint ensuring that the generator is off for at least Cminoff timesteps.
        """

        # Sum the periods when the generator is on (u_ = 0) over the previous Cminoff_[i_] timesteps
        # and ensure it is at least (1 - u_[i_, t_])
        constraint = cp.sum(1 - u_[i_, t_ - Cminoff_[i_] + 1:t_ + 1]) >= 1 - u_[i_, t_]

        # Assign a name to the constraint
        constraint._name = COOL_DOWN_CONSTRAINT_NAME

        # Return the constraint
        return constraint

    def _store_constraints(all_constraints, all_constraints_dict, _constraints, name):
        """
        Helper function for storing constraints in lists and dictionaries.

        Parameters:
        - all_constraints: List of all constraints.
        - all_constraints_dict: Dictionary of constraints organized by name.
        - _constraints: Constraints to be stored.
        - name: Name of the constraints.

        Returns:
        - all_constraints: Updated list of all constraints.
        - all_constraints_dict: Updated dictionary of constraints.
        """

        all_constraints.extend(_constraints) if isinstance(_constraints, list) else all_constraints.append(_constraints)
        all_constraints_dict[name].extend(_constraints) if isinstance(_constraints, list) else all_constraints_dict[
            name].append(_constraints)
        return all_constraints, all_constraints_dict

    # Define the problem constraints
    constraints = []
    constraints_dict = collections.defaultdict(list)

    # Demand target constraint
    demand_target_constraint = d[Dtargettime] >= Dtargetvol
    demand_target_constraint.name = 'demand_target_constraint'

    constraints.append(demand_target_constraint)

    for idt, t in enumerate(range(T_)):  # for each timestep
        # Demand constraint
        demand_constraints = _demand_constraint(p, F, D, t)
        constraints.append(demand_constraints)
        constraints_dict[DEMAND_CONSTRAINT_NAME].append(demand_constraints)

        not_in_last_iteration = idt < T_-1

        # Demand increase constraint
        if not_in_last_iteration:
            demand_increase_constraints = _block_load_constraint(d, t)
            constraints, constraints_dict = _store_constraints(
                constraints, constraints_dict, demand_increase_constraints, 'demand-increase-constraint'
            )

        for i in range(N):  # for each generator
            # Status constraints
            status_constraints = _status_constraint(Gmin, Cminon, u, c, p, i, t)
            constraints, constraints_dict = _store_constraints(
                constraints, constraints_dict, status_constraints, STATUS_CONSTRAINT_NAME
            )

            # Min power output constraint
            min_power_constraints = _min_power_constraint(Gmin, u, p, i, t)
            constraints, constraints_dict = _store_constraints(
                constraints, constraints_dict, min_power_constraints, MIN_POWER_CONSTRAINT_NAME
            )

            max_power_constraints = _max_power_constraint(Gmax, u, p, i, t)
            constraints, constraints_dict = _store_constraints(
                constraints, constraints_dict, max_power_constraints, MAX_POWER_CONSTRAINT_NAME
            )

            # Start-up constraint
            start_up_constraints = _start_up_constraint(Cminon, u, c, i, t)
            constraints, constraints_dict = _store_constraints(
                constraints, constraints_dict, start_up_constraints, START_UP_CONSTRAINT_NAME
            )

            # Minimum off-time constraint
            if t >= Cminoff[i]:  # apply from start of time
                cool_down_constraints = _cool_down_constraint(Cminoff, u, i, t)
                constraints, constraints_dict = _store_constraints(
                    constraints, constraints_dict, cool_down_constraints, COOL_DOWN_CONSTRAINT_NAME
                )

    return constraints, constraints_dict


def build(demand, renewables, generators, block_loading_targets):
    """
    Method for building optimization model.

    Parameters:
    - demand: Pandas DataFrame representing the demand data.
    - renewables: Pandas DataFrame representing the renewable power output data.
    - generators: Pandas DataFrame representing the generator data.
    - block_loading_targets: Pandas Series representing the block loading targets.
        - index: None
        - time: datetime
            Target datetime for block loading
        - volume: float
            Target volume for block loading

    Returns:
    - prob: The optimization problem.
    - u: Decision variable representing the on/off status of generators.
    - c: Decision variable representing the start-up status of generators.
    - p: Decision variable representing the power output of generators.
    - d: Variable representing block load.
    """

    # Extract the data as numpy arrays
    D = demand.values  # total forecasted demand
    F = renewables.values
    Gmin = generators['Minimum power output'].values
    Gmax = generators['Maximum power output'].values
    Cstart = generators['Start-up cost'].values
    Cfuel = generators['Fuel cost'].values
    Cminon = generators['Minimum on-time'].values
    Cminoff = generators['Minimum off-time'].values

    # Extract block loading targets
    Dtargettime, Dtargetvol = block_loading_targets['time'], block_loading_targets['volume']

    # Obtain index of target time
    Dtargettime = demand.index.tolist().index(Dtargettime)

    # Define the problem parameters
    T_ = len(D)  # Number of time periods
    N = len(Gmin)  # Number of generating units

    # Define the decision variables
    u = cp.Variable((N, T_), boolean=True, name='on_off')  # On/off status
    c = cp.Variable((N, T_), boolean=True, name='startup')  # Start-up status
    p = cp.Variable((N, T_), name='power_out')  # Power output
    d = cp.Variable(T_, name='demand')  # Discrete demand variable

    constraints_list, constraint_dict = define_constraints(u, c, p, d,
                                                           F, D, Gmax, Gmin, Cminon, Cminoff, Dtargettime, Dtargetvol)

    # Define the problem objective
    obj = cp.Minimize(cp.sum(
        # cp.multiply(p, Cstart.reshape(N, 1)) +
        cp.multiply(p, Cfuel.reshape(N, 1)) +
        cp.multiply(c, Cstart.reshape(N, 1))
    ))

    # Solve the problem
    prob = cp.Problem(obj, constraints_list)

    prob.constraint_dict = constraint_dict

    return prob, u, c, p, d


def solve(prob, u, c, p, d, verbose=True):
    """Method for solving."""

    prob.solve(solver=cp.CBC, verbose=verbose)

    # # Print the optimal solution
    # print("Minimum cost: ", prob.value)
    # print("On/off status: ", u.value)
    # print("Start-up status: ", c.value)
    # print("Power output: ", p.value)
    return prob, u, c, p, d


def relax_constraints(prob, verbose=False):
    """Method for assessing infeasibility by modifying constraints.

    This method follows the steps below to assess infeasibility and identify the constraints that significantly contribute
    to it. It then revises or modifies the problem formulation, constraints, or problem data to make the problem feasible.

    Steps:
    1. Start with an infeasible optimization problem.
    2. Disable one constraint by removing it from the problem formulation or relaxing its restrictions.
    3. Solve the modified problem to obtain a feasible solution.
    4. Analyze the impact of disabling the constraint on the feasibility and solution quality.
    5. Repeat steps 2-4 for each constraint in the problem, one at a time.
    6. Based on the analysis, identify the constraints that, when disabled, contribute significantly to the infeasibility.
    7. Use this information to revise or modify the problem formulation, constraints, or problem data to make the problem feasible.

    Args:
        prob (Problem): The infeasible optimization problem.
        verbose (bool, optional): Whether to print solver output (default is False).

    Returns:
        tuple: A tuple containing two dictionaries:
            - constraint_status: A dictionary mapping each constraint group to a boolean indicating its feasibility status.
            - constraint_group_problem: A dictionary mapping each constraint group to a modified problem instance
              that excludes that group's constraint.
    """

    # Initialize dictionaries to store constraint status and modified problem instances
    constraint_status = {k: False for k in prob.constraint_dict.keys()}
    constraint_group_problem = {k: None for k in prob.constraint_dict.keys()}

    # Iterate over each constraint group
    for constraint_group in prob.constraint_dict.keys():
        logger.info(f'Optimizing with {constraint_group} deactivated.')

        # Create a modified constraint dictionary without the current constraint group
        constraint_dict_ = {k: v for k, v in prob.constraint_dict.items() if k != constraint_group}

        # Solve the modified problem
        prob_ = cp.Problem(prob.objective, sum(constraint_dict_.values(), []))
        prob_.constraint_dict = constraint_dict_
        prob_.solve(solver=cp.CBC, verbose=verbose)

        # Check if the modified problem is feasible
        if prob_.status == 'optimal':
            constraint_status[constraint_group] = True

        # Store the modified problem instance for the current constraint group
        constraint_group_problem[constraint_group] = prob_

    # Define a list of constraints related to insufficient power
    insufficient_power_constraints = [MAX_POWER_CONSTRAINT_NAME, DEMAND_CONSTRAINT_NAME]

    # Define a list of constraints related to generator cooldown
    too_hot_constraints = [COOL_DOWN_CONSTRAINT_NAME]

    # Define a list of constraints related to generator startup
    start_up_constraints = [START_UP_CONSTRAINT_NAME]

    # Define a list of constraints related to status
    status_constraints = [STATUS_CONSTRAINT_NAME]

    def _condition(_constraints):
        return all([constraint_status[c] for c in _constraints]) and \
            all([not constraint_status[c] for c in CONSTRAINT_NAMES if c not in _constraints])

    # Check if all constraints related to insufficient power are satisfied
    if _condition(insufficient_power_constraints):
        logger.warning('Insufficient available power to meet demand.')

    # Check if all constraints related to generator cooldown are satisfied
    elif _condition(too_hot_constraints):
        logger.warning('Generators cannot cool down in time.')

    # Check if all constraints related to generator startup are satisfied
    elif _condition(start_up_constraints):
        logger.warning('Generators cannot start up in time.')

    # Check if all constraints related to status
    elif _condition(status_constraints):
        logger.warning('Cannot enforce status variable.')

    else:
        logger.warning('UNKNOWN infeasibility condition.')

    # Return the dictionary of modified problem instances
    return constraint_status, constraint_group_problem
