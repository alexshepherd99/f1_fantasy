import sys
sys.path.insert(0, "/workspaces/f1_fantasy")

from pulp import LpMaximize, LpProblem, LpStatus, lpSum, LpVariable

from races.asset import Driver


varMaxVal = 100.0

