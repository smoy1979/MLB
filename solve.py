from datetime import datetime

from pulp import *
from util.data import read_config, read_data


class Solve:
    """ """
    def __init__(self):
        """ """
        self.prob = None
        self.x = None
        self.y = None
        self.teams_df = None
        self._start_dt = None
        self._end_dt = None
        self._duration = None

    def load(self):
        """ """
        self.teams_df = read_config("teams.csv")
        print(self.teams_df)

        self._start_dt = datetime(2026, 3, 25, 0, 0, 0)
        self._end_dt = datetime(2026, 9, 27, 0, 0, 0)
        self._duration = (self._end_dt - self._start_dt).days

    def setup(self):
        """ """
        # Create the problem
        self.prob = LpProblem("My_MILP_Problem", LpMinimize)

        # Define variables
        self.x = LpVariable("x", 0, 4, LpInteger)
        self.y = LpVariable("y", -1, 1, LpInteger)

        # Objective function
        self.prob += self.x + self.y, "Total Cost"

        # Constraints
        self.prob += self.x + 2*self.y >= 3, "Constraint 1"

    def solve(self):
        """ """
        # Solve the problem
        self.prob.solve()

        # Print the results
        print("Status:", LpStatus[self.prob.status])
        print("x =", self.x.varValue)
        print("y =", self.y.varValue)
