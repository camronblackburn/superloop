import numpy as np
from accelergy.plug_in_interface.estimator import (
    Estimator,
    actionDynamicEnergy
)
from abc import ABC, abstractmethod


class ColdChip2ChipNetwork(Estimator): 
    name = ["cold_chip2chip_network"]
    percent_accuracy_0_to_100 = 80

    @actionDynamicEnergy
    def read(self) -> float: 
        return 1

    @actionDynamicEnergy
    def write(self) -> float: 
        return 1

    @actionDynamicEnergy
    def update(self) -> float: 
        return 1

    def leak(self) -> float: 
        return 0

    def get_area(self) -> float: 
        return 0
