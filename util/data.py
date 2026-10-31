import pandas as pd


def read_config(filename):
    """ """
    full_path = f"config/{filename}"
    return pd.read_csv(full_path, sep=",")

def read_data(filename):
    """ """
    full_path = f"data/{filename}"
    return pd.read_csv(full_path, sep=",")


if __name__ == '__main__':  # pragma: no cover
    """ """