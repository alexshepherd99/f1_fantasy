import sys
if "/workspaces/f1_fantasy" not in sys.path:
    sys.path.insert(0, "/workspaces/f1_fantasy")

import numpy as np

from pulp import LpMaximize, LpProblem, LpStatus, lpSum, LpVariable, PULP_CBC_CMD

driver_prices = {
    "VER": 1.0,
    "LEC": 2.0,
    "HAM": 3.0,
    "ALO": 4.0,
    "STR": 5.0,
    "HUL": 6.5,
    "MAG": 7.0,
    "BOT": 8.0,
    "NOR": 9.0,
    "PIA": 10.0,
    "TSU": 9.5,
    "RUS": 99999.99
}
constructor_prices = {
    "MCL": 4.0,
    "FER": 6.0,
    "RED": 5.0,
    "MER": 7.0,
    "AST": 12.0,
}

driver_team = {
    "VER": 1,
    "LEC": 1,
    "HAM": 1,
    "ALO": 1,
    "STR": 1,
    "HUL": 0,
    "MAG": 0,
    "BOT": 0,
    "NOR": 0,
    "PIA": 0,
    "TSU": 0,
    "RUS": 0,
}
constructor_team = {
    "MCL": 1,
    "FER": 1,
    "RED": 0,
    "MER": 0,
    "AST": 0,
}

driver_list = list(driver_team.keys())
constructor_list = list(constructor_team.keys())

team_size_drivers = 5
team_size_constructors = 2
team_size_total = team_size_drivers + team_size_constructors

max_cost = 25.0
max_moves = 2

model = LpProblem("F1_Team", LpMaximize)

var_team_drivers = LpVariable.dicts('driver', driver_list, cat="Binary")
var_team_constructors = LpVariable.dicts('constructor', constructor_list, cat="Binary")

cost_drivers = [driver_prices[i] * var_team_drivers[i] for i in driver_list]
cost_constructors = [constructor_prices[i] * var_team_constructors[i] for i in constructor_list]

objective = lpSum(cost_drivers + cost_constructors)

constraint_total_value = objective <= max_cost
constraint_driver_team_size = lpSum([var_team_drivers[i] for i in driver_list]) == team_size_drivers
constraint_constructor_team_size = lpSum([var_team_constructors[i] for i in constructor_list]) == team_size_constructors

constraint_driver_unavailable = var_team_drivers["RUS"] == 0

var_driver_moves = [driver_team[i] * var_team_drivers[i] for i in driver_list]
var_constructor_moves = [constructor_team[i] * var_team_constructors[i] for i in constructor_list]
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
