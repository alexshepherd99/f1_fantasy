import sys
sys.path.insert(0, "/workspaces/f1_fantasy")

from pulp import LpMaximize, LpProblem, LpStatus, lpSum, LpVariable


var_d1_selected = LpVariable(name="D1 Sel", cat="Binary")
var_d2_selected = LpVariable(name="D2 Sel", cat="Binary")
var_d3_selected = LpVariable(name="D3 Sel", cat="Binary")
var_d4_selected = LpVariable(name="D4 Sel", cat="Binary")
var_d5_selected = LpVariable(name="D5 Sel", cat="Binary")

const_d1_price = 25.0
const_d2_price = 30.0
const_d3_price = 55.5
const_d4_price = 10.0
const_d5_price = 76.0

const_max_value = 100.0

objective = (
    (var_d1_selected * const_d1_price) +
    (var_d2_selected * const_d2_price) +
    (var_d3_selected * const_d3_price) +
    (var_d4_selected * const_d4_price) +
    (var_d5_selected * const_d5_price)
)

constraint_total_value = objective <= 100.0

model = LpProblem("model", LpMaximize)

model += objective
model += constraint_total_value

model.solve()

for var in model.variables():
    print(f"{var.name}: {var.value()}")

https://stackoverflow.com/questions/60144756/how-to-optimize-variables-combination-in-a-dictionary-using-pulp-python
