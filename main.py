import pandas as pd

from util.framework import setup_framework, setup_logging
from solve import Solve


def run():
    """ """
    solve = Solve()
    solve.load()
    solve.setup()
    solve.solve()


if __name__ == '__main__':  # pragma: no cover
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)

    setup_framework()
    setup_logging()
    run()
