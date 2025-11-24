import sys
if "/workspaces/f1_fantasy" not in sys.path:
    sys.path.insert(0, "/workspaces/f1_fantasy")

import numpy as np

from pulp import LpMaximize, LpProblem, LpStatus, lpSum, LpVariable, PULP_CBC_CMD

driver_prices = [1.0, 2.0, 3.0, 4.0, 5.0, 6.5, 7.0, 8.0, 9.0, 10.0, 9.5, 99999.99]
constructor_prices = [4.0, 6.0, 5.0, 7.0, 12.0]

driver_team = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
constructor_team = [1, 1, 0, 0, 0]

n_drivers = len(driver_prices)
n_constructors = len(constructor_prices)
N_drivers = range(n_drivers)
N_constructors = range(n_constructors)

team_size_drivers = 5
team_size_constructors = 2
team_size_total = team_size_drivers + team_size_constructors

max_cost = 25.0
max_moves = 2

model = LpProblem("F1_Team", LpMaximize)

var_team_drivers = LpVariable.dicts('driver', N_drivers, cat="Binary")
var_team_constructors = LpVariable.dicts('constructor', N_constructors, cat="Binary")

cost_drivers = [driver_prices[i] * var_team_drivers[i] for i in N_drivers]
cost_constructors = [constructor_prices[i] * var_team_constructors[i] for i in N_constructors]

objective = lpSum(cost_drivers + cost_constructors)

constraint_total_value = objective <= max_cost
constraint_driver_team_size = lpSum([var_team_drivers[i] for i in N_drivers]) == team_size_drivers
constraint_constructor_team_size = lpSum([var_team_constructors[i] for i in N_constructors]) == team_size_constructors

constraint_driver_unavailable = var_team_drivers[9] == 0

var_driver_moves = [driver_team[i] * var_team_drivers[i] for i in N_drivers]
var_constructor_moves = [constructor_team[i] * var_team_constructors[i] for i in N_constructors]
var_team_moves = team_size_total - lpSum(var_driver_moves + var_constructor_moves)

constraint_team_moves = var_team_moves <= max_moves

model += objective
model += constraint_total_value
model += constraint_driver_team_size
model += constraint_constructor_team_size
model += constraint_team_moves
model += constraint_driver_unavailable

PULP_CBC_CMD(msg=0).solve(model)

for var in model.variables():
    print(f"{var.name}: {var.value()}")

print(model.objective.value())
print(var_team_moves.value())
