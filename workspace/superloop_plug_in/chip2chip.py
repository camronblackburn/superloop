import numpy as np
from accelergy.plug_in_interface.estimator import (
    Estimator,
    actionDynamicEnergy
)
from abc import ABC, abstractmethod
from inter_temp import Cold2HotNetwork


class ColdChip2ChipNetwork(Cold2HotNetwork): 
    name = ["cold_chip2chip_network"]
    percent_accuracy_0_to_100 = 80

    def __init__(self, 
                 global_cycle_seconds: float,
                 datawidth: int,
                 cold_temp: float,
                 channel_count: int, 
                 amp_type: str = "aqfp_diffamp",
                 v_load: float = 1.1,
                 ):
        super().__init__(
            global_cycle_seconds=global_cycle_seconds,
            datawidth=datawidth,
            hot_temp=cold_temp,
            cold_temp=cold_temp,
            channel_count=channel_count,
            amp_type=amp_type,
            v_load=v_load,
        )
        self.route = "2->1"

    @actionDynamicEnergy
    def read(self) -> float: 
        return super().read()

    @actionDynamicEnergy
    def write(self) -> float: 
        return super().read()

    @actionDynamicEnergy
    def update(self) -> float: 
        return super().read()

    def leak(self) -> float: 
        return 0

    def get_area(self) -> float: 
        return 0
