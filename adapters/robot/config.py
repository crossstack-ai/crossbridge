"""
Robot Framework adapter configuration.
"""

from dataclasses import dataclass


@dataclass
class RobotConfig:
    tests_path: str = "tests"
    output_dir: str = ".robot-output"
    pythonpath: str = "."
