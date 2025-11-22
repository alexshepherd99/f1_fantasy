import sys
sys.path.insert(0, "/workspaces/f1_fantasy")

from pulp import LpMaximize, LpProblem, LpStatus, lpSum, LpVariable, PULP_CBC_CMD

prices = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0]
team = [1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

n = len(prices)
N = range(n)

max_cost = 139.0

max_team_size = 2

max_moves = 1

model = LpProblem("F1_Team", LpMaximize)

var_team_new = LpVariable.dicts('team', N, cat="Binary")

objective = lpSum([prices[i] * var_team_new[i] for i in N])
constraint_total_value = objective <= max_cost
constraint_team_size = lpSum([var_team_new[i] for i in N]) == max_team_size
constraint_team_moves = lpSum([team[i] * var_team_new[i] for i in N]) >= (max_team_size - max_moves)

model += objective
model += constraint_total_value
model += constraint_team_size
model += constraint_team_moves

PULP_CBC_CMD(msg=0).solve(model)

for var in model.variables():
    print(f"{var.name}: {var.value()}")
