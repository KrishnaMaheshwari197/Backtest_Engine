"""
Utility functions for backtesting.
Includes configuration loading, data loading, and time conversion utilities.
"""

import pandas as pd
import yaml 
from easydict import EasyDict
from datetime import time
from pathlib import Path

CACHE = {}

# Convert time object to total seconds
def time_to_seconds(t):
    """Convert time object to seconds since midnight."""
    return t.hour * 3600 + t.minute * 60 + t.second

# Convert seconds to time object
def seconds_to_time(seconds):
    """Convert seconds since midnight to time object."""
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return time(int(hours), int(minutes), int(seconds))


def get_cfg(file_path: str = "config.yaml") -> EasyDict:
    """Get the config yaml file as an EasyDict object.

    Parameters:
        file_path (str): The path to the config yaml file.
    Returns:
        EasyDict: The yaml file as an EasyDict object.
    """
    if file_path not in CACHE:
        CACHE[file_path] = _load_cfg(file_path)
    if CACHE[file_path] is None:
        raise FileNotFoundError(f"Config file not found at {file_path}")
    return CACHE[file_path]


def _load_cfg(file_path: str = "config.yaml") -> EasyDict:
    """Load the config yaml file as an EasyDict object.

    Parameters:
        file_path (str): The path to the config yaml file.
    Returns:
        EasyDict: The yaml file as an EasyDict object.
    """
    with open(file_path, "r") as stream:
        try:
            return EasyDict(yaml.safe_load(stream))
        except yaml.YAMLError as exc:
            print(exc)
            return None

