import collections

import cvxpy as cp
import numpy as np

from config import *
from logger import logger

INITIAL_CONDITION_CONSTRAINT_NAME = 'initial-condition-constraint'
TARGET_DEMAND_CONSTRAINT_NAME = 'target-demand-constraint'
BLOCK_DEMAND_INCREASE_CONSTRAINT_NAME = 'demand-increase-constraint'
BLOCK_DEMAND_DECREASE_CONSTRAINT_NAME = 'demand-decrease-constraint'
SINGLE_STARTUP_CONSTRAINT_NAME = 'single-startup-constraint'
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


def _block_load_increase_constraint(d_, t_, block_limit=10):
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
    constraint._name = BLOCK_DEMAND_INCREASE_CONSTRAINT_NAME

    # Return the constraint
    return constraint


def _block_load_decrease_constraint(d_, t_):
    """

    """
    constraint = d_[t_ + 1] - d_[t_] >= 0

    # Assign a name to the constraint
    constraint._name = BLOCK_DEMAND_DECREASE_CONSTRAINT_NAME

    # Return the constraint
    return constraint


def _single_generator_startup_constraint(c_, t_):
    """

    """
    constraint = cp.sum(c_[:, t_]) <= 1

    # Assign a name to the constraint
    constraint._name = SINGLE_STARTUP_CONSTRAINT_NAME

    # Return the constraint
    return constraint


def _demand_constraint(p_, F_, d_, t_):
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
    constraint = cp.sum(p_[:, t_]) + F_[t_] >= d_[t_]

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


def add_demand_target_constraint(t, Dtargettime, Dtargetvol, Dtargets_, d, D, constraints, constraints_dict):
    """
    Adds the demand target constraint to the list of constraints based on the current timestep.

    Args:
        t (int): Current timestep.
        Dtargettime (int): Timestep of the demand target.
        Dtargetvol (float): Volume of the demand target.
        Dtargets_ (pd.DataFrame): DataFrame containing the demand targets.
        d (cvxpy.Variable): Variable representing the demand.
        constraints (list): List of constraints.
        constraints_dict (defaultdict): Dictionary of constraints categorized by type.

    Returns:
        int: Updated Dtargettime.
        float: Updated Dtargetvol.
    """

    if t == Dtargettime:
        # Create the demand target constraint for the current timestep
        demand_target_constraint = d[t] >= Dtargetvol
        demand_target_constraint.name = TARGET_DEMAND_CONSTRAINT_NAME

        # Append the demand target constraint to the list of constraints
        constraints.append(demand_target_constraint)
        constraints_dict[TARGET_DEMAND_CONSTRAINT_NAME].append(demand_target_constraint)

        # Remove the first record from the Dtargets DataFrame if it is not empty
        Dtargets_ = Dtargets_.iloc[1:]

        # Update the Dtargettime and Dtargetvol variables with the next target values
        if not Dtargets_.empty:
            Dtargettime = Dtargets_.iloc[0]['t_index']
            Dtargetvol = Dtargets_.iloc[0]['volume']

    if t > Dtargettime and Dtargets_.empty:
        # Create the demand target constraint for the remaining timesteps
        demand_target_constraint = d[t] == D[t]
        demand_target_constraint.name = TARGET_DEMAND_CONSTRAINT_NAME

        # Append the demand target constraint to the list of constraints
        constraints.append(demand_target_constraint)
        constraints_dict[TARGET_DEMAND_CONSTRAINT_NAME].append(demand_target_constraint)

    return Dtargettime, Dtargetvol, Dtargets_


def define_constraints(u, c, p, d, F, D, Gmax, Gmin, Cminon, Cminoff, Dtargets, t_index, T_=T):
    """
    Define constraints for an optimization problem.

    Args:
        u (cvxpy.Variable): Binary variable indicating generator on/off status.
        c (cvxpy.Variable): Binary variable indicating generator startup status.
        p (cvxpy.Variable): Variable representing generator power output.
        d (cvxpy.Variable): Variable representing block load.
        F (cvxpy.Variable): Variable representing wind power.
        D (cvxpy.Variable): Variable representing demand.
        Gmax (list): List of maximum generator capacities.
        Gmin (list): List of minimum generator capacities.
        Cminon (list): List of minimum on-time timesteps for generators.
        Cminoff (list): List of minimum off-time timesteps for generators.
        Dtargets (pd.DataFrame): DataFrame containing the demand targets.
        t_index (np.ndarray): Array of timestep indices.
        T_ (int): Number of timesteps.

    Returns:
        list: List of constraints.
        defaultdict: Dictionary of constraints categorized by type.
    """

    constraints = []
    constraints_dict = collections.defaultdict(list)

    # Initial condition constraint
    initial_condition_constraint = d[0] == 0
    constraints.append(initial_condition_constraint)
    constraints_dict[INITIAL_CONDITION_CONSTRAINT_NAME].append(initial_condition_constraint)

    # Sort and index the demand targets
    Dtargets.sort_index(inplace=True)
    Dtargets['t_index'] = [t_index.tolist().index(t) for t in Dtargets.index]

    # Copy the demand targets DataFrame
    Dtargets_ = Dtargets.copy()
    Dtargettime = Dtargets_.iloc[0]['t_index']
    Dtargetvol = Dtargets_.iloc[0]['volume']

    # Demand target constraint
    for idt, t in enumerate(range(T_)):
        # Add demand target constraint based on the current timestep
        Dtargettime, Dtargetvol, Dtargets_ = add_demand_target_constraint(
            t, Dtargettime, Dtargetvol, Dtargets_, d, D, constraints, constraints_dict
        )

    for idt, t in enumerate(range(T_)):
        # Demand constraint
        demand_constraints = _demand_constraint(p, F, d, t)
        constraints.append(demand_constraints)
        constraints_dict[DEMAND_CONSTRAINT_NAME].append(demand_constraints)

        not_in_last_iteration = idt < T_-1

        # Demand increase and decrease constraints
        if not_in_last_iteration and t <= Dtargettime:
            block_limit = Dtargets[t <= Dtargets['t_index']].iloc[0]['block_limit']
            demand_increase_constraints = _block_load_increase_constraint(d, t, block_limit=block_limit)
            constraints, constraints_dict = _store_constraints(
                constraints, constraints_dict, demand_increase_constraints, BLOCK_DEMAND_INCREASE_CONSTRAINT_NAME
            )
            demand_decrease_constraints = _block_load_decrease_constraint(d, t)
            constraints, constraints_dict = _store_constraints(
                constraints, constraints_dict, demand_decrease_constraints, BLOCK_DEMAND_DECREASE_CONSTRAINT_NAME
            )

        # single_startup_constraint = _single_generator_startup_constraint(c, t)
        # constraints, constraints_dict = _store_constraints(
        #     constraints, constraints_dict, single_startup_constraint, SINGLE_STARTUP_CONSTRAINT_NAME
        # )

        for i in range(N):
            # Status constraints
            status_constraints = _status_constraint(Gmin, Cminon, u, c, p, i, t)
            constraints, constraints_dict = _store_constraints(
                constraints, constraints_dict, status_constraints, STATUS_CONSTRAINT_NAME
            )

            # Minimum power output constraint
            min_power_constraints = _min_power_constraint(Gmin, u, p, i, t)
            constraints, constraints_dict = _store_constraints(
                constraints, constraints_dict, min_power_constraints, MIN_POWER_CONSTRAINT_NAME
            )

            # Maximum power output constraint
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
            if t >= Cminoff[i]:
                cool_down_constraints = _cool_down_constraint(Cminoff, u, i, t)
                constraints, constraints_dict = _store_constraints(
                    constraints, constraints_dict, cool_down_constraints, COOL_DOWN_CONSTRAINT_NAME
                )

    return constraints, constraints_dict


def build(demand, renewables, generators, target_checkpoints, block_loading_targets):
    """
    Method for building optimization model.

    Parameters:
    - demand: Pandas DataFrame representing the demand data.
    - renewables: Pandas DataFrame representing the renewable power output data.
    - generators: Pandas DataFrame representing the generator data.
    - target_checkpoints: Pandas DataFrame representing minimum block loading targets. These are used to formulate the
        target demand values at each checkpoint.
        - index: datetime
            Target datetime for block loading
        - volume: float
            Target volume for block loading
    - block_loading_targets: Pandas Series representing the block loading targets by datetime index. These are used
        to formulate a penalty in the objective. Forcing generators to achieve the target as soon as possible.
        - index: datetime
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
    t_index = demand.index
    D = demand.values  # total forecasted demand
    F = renewables.values
    Gmin = generators['Minimum power output'].values
    Gmax = generators['Maximum power output'].values
    Cstart = generators['Start-up cost'].values
    Cfuel = generators['Fuel cost'].values
    Cminon = generators['Minimum on-time'].values
    Cminoff = generators['Minimum off-time'].values
    Dtarget = block_loading_targets.values

    # Define the problem parameters
    T_ = len(D)  # Number of time periods
    N = len(Gmin)  # Number of generating units

    # Define the decision variables
    u = cp.Variable((N, T_), boolean=True, name='on_off')  # On/off status
    c = cp.Variable((N, T_), boolean=True, name='startup')  # Start-up status
    p = cp.Variable((N, T_), name='power_out', nonneg=True)  # Power output
    d = cp.Variable(T_, name='demand', nonneg=True)  # Discrete demand variable

    constraints_list, constraint_dict = define_constraints(u, c, p, d,
                                                           F, D, Gmax, Gmin, Cminon, Cminoff, target_checkpoints,
                                                           t_index)

    # Define the problem objective
    obj = cp.Minimize(
        cp.sum(
            cp.multiply(cp.abs(d - Dtarget), 1000000) +
            cp.sum(
                cp.multiply(p, Cfuel.reshape(N, 1)) +
                cp.multiply(c, Cstart.reshape(N, 1))
            )
        )
    )

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
            logger.info('Problem successful')
        else:
            logger.info('Problem unsuccessful')
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

    # Define a list of constraints related to achieving block loading in time for targets
    target_block_loading_constraints = [
        INITIAL_CONDITION_CONSTRAINT_NAME, TARGET_DEMAND_CONSTRAINT_NAME, BLOCK_DEMAND_INCREASE_CONSTRAINT_NAME
    ]

    def _condition(_constraints):
        return all([constraint_status[c] for c in _constraints]) and \
            all([not constraint_status[c] for c in CONSTRAINT_NAMES if c not in _constraints])

    # Check if all constraints related to insufficient power are satisfied
    if _condition(insufficient_power_constraints):
        logger.warning('Insufficient available power to meet demand.')

    # Check if all constraints related to generator cooldown are satisfied
    elif _condition(too_hot_constraints):
        logger.warning('Generators cannot cool down in time.')

    # Check if all constraints related to block loading in time for targets
    elif _condition(target_block_loading_constraints):
        logger.warning('Cannot achieve block loading in time for targets.')

    # Check if all constraints related to generator startup are satisfied
    elif _condition(start_up_constraints):
        logger.warning('Generators cannot start up in time.')

    # Check if all constraints related to status
    elif _condition(status_constraints):
        logger.warning('Cannot enforce status variable.')

    else:
        print(status_constraints)
        logger.warning('UNKNOWN infeasibility condition.')

    # Return the dictionary of modified problem instances
    return constraint_status, constraint_group_problem
