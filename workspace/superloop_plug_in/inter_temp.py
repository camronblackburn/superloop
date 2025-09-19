import numpy as np

from accelergy.plug_in_interface.estimator import (
    Estimator,
    actionDynamicEnergy,
)


class Hot2ColdNetwork(Estimator):
    name = "hot2cold_network"
    percent_accuracy_0_to_100 = 70

    def __init__(self,
                 datawidth: int,
                 hot_temp: float,
                 cold_temp: float,
                 ):
        super().__init__()
        self.datawidth = datawidth
        self.hot_temp = hot_temp
        self.cold_temp = cold_temp

    @actionDynamicEnergy
    def read(self) -> float:
        # hot to cold is just like driving a long interconnect to get to the cold stage
        # should be comparable to off chip interconnect costs in CMOS
        # which we're not current accounting for, so keep this 0 for now
        return 0

    # Write and update aren't used for networks
    @actionDynamicEnergy
    def write(self) -> float:
        return 0

    @actionDynamicEnergy
    def update(self) -> float:
        return 0

    def get_area(self) -> float:
        return 0

    def leak(self, global_cycle_seconds: float) -> float:
        return 0


class Cold2HotNetwork(Estimator):
    name = "cold2hot_network"
    percent_accuracy_0_to_100 = 70

    def __init__(self,
                 datawidth: int,
                 hot_temp: float,
                 cold_temp: float,
                 ):
        super().__init__()
        self.datawidth = datawidth
        self.hot_temp = hot_temp
        self.cold_temp = cold_temp

    @actionDynamicEnergy
    def read(self) -> float:
        return self.datawidth * (self.hot_temp - self.cold_temp) * 10e-15  # 10fJ/bit/degree placeholder

    # Write and update aren't used for networks
    @actionDynamicEnergy
    def write(self) -> float:
        return 0

    @actionDynamicEnergy
    def update(self) -> float:
        return self.write()

    def get_area(self) -> float:
        return 0

    def leak(self, global_cycle_seconds: float) -> float:
        return 0
