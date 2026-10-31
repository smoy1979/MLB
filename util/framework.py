"""
setup basic framework requirements
1. make sure folders exist
2. a helper function for logging config, to be used when multi-processing
"""
import os
import logging


FOLDERS = [
    "data",             # base folder
]


def setup_framework():  # pragma: no cover
    """ setup framework """
    for folder in FOLDERS:
        if not os.path.exists(folder):
            os.mkdir(folder)


def setup_logging():  # pragma: no cover
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",  # Customize timestamp format
        level=logging.INFO
    )
