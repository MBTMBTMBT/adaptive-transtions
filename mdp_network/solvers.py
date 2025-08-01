from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from mdp_tables import QTable, ValueTable, PolicyTable
from mdp_network import MDPNetwork


def policy_evaluation(mdp_network: MDPNetwork,
                      policy: PolicyTable,
                      gamma: float = 0.9,
                      theta: float = 1e-6,
                      max_iterations: int = 1000) -> ValueTable:
    """
    Evaluate a given policy using value iteration to compute state values.
    Now supports probabilistic policies.

    Args:
        mdp_network: The MDP network to solve
        policy: Policy table mapping state -> action probability distribution
        gamma: Discount factor (0 <= gamma <= 1)
        theta: Convergence threshold
        max_iterations: Maximum number of iterations

    Returns:
        ValueTable object containing computed state values under the given policy
    """

    # Initialize value table
    value_table = ValueTable()

    # Get all states
    states = mdp_network.states

    # Initialize values to zero
    for state in states:
        value_table.set_value(state, 0.0)

    # Policy evaluation loop
    for iteration in range(max_iterations):
        max_delta = 0.0

        # Update value for each state
        for state in states:
            if mdp_network.is_terminal_state(state):
                # Terminal states have zero value
                value_table.set_value(state, 0.0)
                continue

            old_value = value_table.get_value(state)

            # Compute expected value over all actions according to policy
            new_value = 0.0
            action_probs = policy.get_action_probabilities(state)

            for action, action_prob in action_probs.items():
                if action_prob <= 0:
                    continue

                # Compute value for this action
                action_value = 0.0

                # Get transition probabilities for this state-action pair
                transition_probs = mdp_network.get_transition_probabilities(state, action)

                if not transition_probs:
                    # No transitions defined, assume staying in same state
                    transition_probs = {state: 1.0}

                # Sum over all possible next states
                for next_state, prob in transition_probs.items():
                    # Immediate reward for transitioning to next_state
                    reward = mdp_network.get_state_reward(next_state)

                    # Value of next state
                    next_value = value_table.get_value(next_state)

                    # Add contribution from this transition
                    action_value += prob * (reward + gamma * next_value)

                # Weight by action probability
                new_value += action_prob * action_value

            # Update value
            value_table.set_value(state, new_value)

            # Track maximum change for convergence check
            delta = abs(new_value - old_value)
            max_delta = max(max_delta, delta)

        # Check for convergence
        if max_delta < theta:
            print(f"Policy evaluation converged after {iteration + 1} iterations")
            break
    else:
        print(f"Policy evaluation reached maximum iterations ({max_iterations})")

    return value_table


def optimal_value_iteration(mdp_network: MDPNetwork,
                            gamma: float = 0.9,
                            theta: float = 1e-6,
                            max_iterations: int = 1000) -> Tuple[ValueTable, QTable]:
    """
    Solve MDP using optimal value iteration to compute optimal values and Q-values.
    No longer returns a deterministic policy - use q_table_to_policy instead.

    Args:
        mdp_network: The MDP network to solve
        gamma: Discount factor (0 <= gamma <= 1)
        theta: Convergence threshold
        max_iterations: Maximum number of iterations

    Returns:
        Tuple of (optimal_value_table, optimal_q_table)
    """

    # Initialize value and Q tables
    value_table = ValueTable()
    q_table = QTable()

    # Get all states and actions
    states = mdp_network.states
    num_actions = mdp_network.num_actions

    # Initialize values to zero
    for state in states:
        value_table.set_value(state, 0.0)
        for action in range(num_actions):
            q_table.set_q_value(state, action, 0.0)

    # Optimal value iteration loop
    for iteration in range(max_iterations):
        max_delta = 0.0

        # Update values for each state
        for state in states:
            if mdp_network.is_terminal_state(state):
                # Terminal states have zero value
                value_table.set_value(state, 0.0)
                for action in range(num_actions):
                    q_table.set_q_value(state, action, 0.0)
                continue

            old_value = value_table.get_value(state)

            # Compute Q-values for all actions in this state
            action_values = []
            for action in range(num_actions):
                # Compute Q-value using Bellman optimality equation
                q_value = 0.0

                # Get transition probabilities for this state-action pair
                transition_probs = mdp_network.get_transition_probabilities(state, action)

                if not transition_probs:
                    # No transitions defined, assume staying in same state
                    transition_probs = {state: 1.0}

                # Sum over all possible next states
                for next_state, prob in transition_probs.items():
                    # Immediate reward for transitioning to next_state
                    reward = mdp_network.get_state_reward(next_state)

                    # Optimal value of next state
                    next_value = value_table.get_value(next_state)

                    # Add contribution from this transition
                    q_value += prob * (reward + gamma * next_value)

                # Store Q-value
                q_table.set_q_value(state, action, q_value)
                action_values.append(q_value)

            # Optimal value is the maximum over all actions
            new_value = max(action_values) if action_values else 0.0
            value_table.set_value(state, new_value)

            # Track maximum change for convergence check
            delta = abs(new_value - old_value)
            max_delta = max(max_delta, delta)

        # Check for convergence
        if max_delta < theta:
            print(f"Optimal value iteration converged after {iteration + 1} iterations")
            break
    else:
        print(f"Optimal value iteration reached maximum iterations ({max_iterations})")

    return value_table, q_table


def q_learning(mdp_network: MDPNetwork,
               alpha: float = 0.1,
               gamma: float = 0.9,
               epsilon: float = 0.1,
               num_episodes: int = 10000,
               max_steps_per_episode: int = 1000,
               seed: Optional[int] = None) -> Tuple[QTable, ValueTable]:
    """
    Solve MDP using Q-Learning algorithm.
    No longer returns a deterministic policy - use q_table_to_policy instead.

    Args:
        mdp_network: The MDP network to solve
        alpha: Learning rate (0 < alpha <= 1)
        gamma: Discount factor (0 <= gamma <= 1)
        epsilon: Exploration rate for epsilon-greedy policy (0 <= epsilon <= 1)
        num_episodes: Number of episodes to run
        max_steps_per_episode: Maximum steps per episode
        seed: Random seed for reproducibility

    Returns:
        Tuple of (q_table, optimal_value_table)
    """

    # Initialize random number generator
    rng = np.random.default_rng(seed)

    # Initialize Q-table and value table
    q_table = QTable()
    value_table = ValueTable()

    # Initialize Q-values for all state-action pairs
    states = mdp_network.states
    num_actions = mdp_network.num_actions

    for state in states:
        value_table.set_value(state, 0.0)  # Initialize with value 0
        for action in range(num_actions):
            q_table.set_q_value(state, action, 0.0)

    # Q-Learning episodes
    for episode in range(num_episodes):
        # Start from a random start state
        current_state = mdp_network.sample_start_state(rng)

        for step in range(max_steps_per_episode):
            # Terminal state check
            if mdp_network.is_terminal_state(current_state):
                break

            # Choose action using epsilon-greedy policy
            if rng.random() < epsilon:
                # Explore: random action
                action = rng.integers(0, num_actions)
            else:
                # Exploit: best action according to current Q-values
                action, _ = q_table.get_best_action(current_state)

            # Take action and observe next state
            next_state = mdp_network.sample_next_state(current_state, action, rng)

            # Get immediate reward
            reward = mdp_network.get_state_reward(next_state)

            # Get current Q-value
            current_q = q_table.get_q_value(current_state, action)

            # Calculate target Q-value
            if mdp_network.is_terminal_state(next_state):
                target_q = reward
            else:
                _, max_next_q = q_table.get_best_action(next_state)
                target_q = reward + gamma * max_next_q

            # Update Q-value using Q-learning update rule
            new_q = current_q + alpha * (target_q - current_q)
            q_table.set_q_value(current_state, action, new_q)

            # Move to next state
            current_state = next_state

        # Print progress
        if (episode + 1) % (num_episodes // 10) == 0:
            print(f"Q-Learning progress: {episode + 1}/{num_episodes} episodes completed")

    # Extract optimal value table from learned Q-values
    for state in states:
        if mdp_network.is_terminal_state(state):
            # Terminal states have zero value
            value_table.set_value(state, 0.0)
        else:
            # State value is the maximum Q-value over all actions
            _, best_q_value = q_table.get_best_action(state)
            value_table.set_value(state, best_q_value)

    return q_table, value_table


def compute_occupancy_measure(mdp_network: MDPNetwork,
                              policy: PolicyTable,
                              gamma: float = 0.9,
                              theta: float = 1e-6,
                              max_iterations: int = 1000) -> ValueTable:
    """
    Compute occupancy measure for a given policy in MDP.
    Now supports probabilistic policies.

    Returns a ValueTable containing the expected cumulative frequency of visiting each state.
    """
    # Initialize occupancy measure table
    occupancy_table = ValueTable()

    # Get all states
    states = mdp_network.states

    # Initialize occupancy measures to zero
    for state in states:
        occupancy_table.set_value(state, 0.0)

    # Initialize current state distribution (uniform over start states)
    current_distribution = {}
    start_states = list(mdp_network.start_states)

    if not start_states:
        print("Warning: No start states found")
        return occupancy_table

    # Uniform initial distribution over start states
    initial_prob = 1.0 / len(start_states)
    for state in start_states:
        current_distribution[state] = initial_prob

    # Iterative computation of occupancy measures
    for iteration in range(max_iterations):
        max_change = 0.0
        next_distribution = {state: 0.0 for state in states}

        # For each state in current distribution
        for state, state_prob in current_distribution.items():
            if state_prob <= 0 or mdp_network.is_terminal_state(state):
                continue

            # Update occupancy measure for this state
            old_occupancy = occupancy_table.get_value(state)
            new_occupancy = old_occupancy + state_prob
            occupancy_table.set_value(state, new_occupancy)

            # Track maximum change for convergence
            change = abs(new_occupancy - old_occupancy)
            max_change = max(max_change, change)

            # Get action probabilities from policy
            action_probs = policy.get_action_probabilities(state)

            # For each possible action
            for action, action_prob in action_probs.items():
                if action_prob <= 0:
                    continue

                # Get transition probabilities for this state-action pair
                transition_probs = mdp_network.get_transition_probabilities(state, action)

                if not transition_probs:
                    # No transitions defined, assume staying in same state
                    transition_probs = {state: 1.0}

                # Propagate probability to next states with discount factor
                for next_state, transition_prob in transition_probs.items():
                    if not mdp_network.is_terminal_state(next_state):
                        # Discounted probability of reaching next state
                        propagated_prob = state_prob * action_prob * transition_prob * gamma
                        next_distribution[next_state] += propagated_prob

        # Update current distribution for next iteration
        current_distribution = next_distribution

        # Check for convergence
        if max_change < theta:
            print(f"Occupancy measure computation converged after {iteration + 1} iterations")
            break
    else:
        print(f"Occupancy measure computation reached maximum iterations ({max_iterations})")

    # Ensure terminal states have zero occupancy
    for state in states:
        if mdp_network.is_terminal_state(state):
            occupancy_table.set_value(state, 0.0)

    return occupancy_table
