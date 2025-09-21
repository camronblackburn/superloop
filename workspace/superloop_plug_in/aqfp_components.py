import os
import numpy as np
from accelergy.plug_in_interface.estimator import (
    Estimator,
    actionDynamicEnergy
)
from abc import ABC, abstractmethod

'''
Library of AQFP components developed in MITLL SFQ5ee process

notes & assumptions
- in AQFP logic, every device is clocked once per cycle regardless of where and what 
the data are, so energy dissipation is a constant regardless of of datapath - i.e. all 
energy dissipation is leakage
- Timeloop assumes that all components are pipelined such that each can read, write, or compute 
once per clock cycle - i.e. it will not check for phase alignment across AQFP components for now

'''


FORECAST_OPTIONS = [
    "conservative",
    "moderate",
    "aggressive"
]

CELL_NODE_LOOKUP = {
    # only used in area projections for now, but should include 
    # dielectric losses for energy projections in the future
    
    "v1.0": {   # cell used in circuit designs now, https://doi.org/10.1109/TASC.2025.3540048
        "width": 20e-6,
        "height": 20e-6,
        "area": 400e-12,        # m^2
        "loss_tangent": 1.5e-3  # from Sergey AC paper: https://doi.org/10.1109/TASC.2022.3230373
    },

    # ideal projected limit from transformer req
    # for SFQ5ee process -> 1e4 qfp/mm^2
    "vInf.0": {
        "area": 1e-10,
        "loss_tangent": 1.5e-3  # Sergey's paper (https://arxiv.org/abs/2210.02632)
    },

    # ideal projected limit from transformer req
    # for advanced fab process -> 22e4 qfp/mm^2
    "vInf.1": {
        "area": 4.5e-12,     # m^2
        "loss_tangent": 1e-5    # dielectric loss tanget with interlayer dielectrics
                                # from Sergey AC paper: https://doi.org/10.1109/TASC.2022.3230373
    }
}

class AQFPEstimator(Estimator):
    '''
    base class for all AQFP components since they follow similar generic formula

    children components must define functions: 
        get_device_count() which returns the number of AQFPs in the circuit component

    args:
        cell_node: AQFP cell library development node, determines area
        frequency (opt): frequency devices are run, default = 5 GHz
        forecast (opt): a string that describes how optimistic to make the design,
            recognized values are ["conservative", "moderate", "aggressive"]. This will 
            be used to determine things like routing overhead in area projections, or
            whether to include extra buffers on the input and output of circuits, etc. 
            default = "conservative"

    '''
    name = "aqfp constructor"
    percent_accuracy_0_to_100 = 0

    def __init__(
            self, 
            cell_node: str, 
            global_cycle_seconds: float, 
            clock_derate: int = 1,
            forecast: str = "conservative", 
            phase_count: int = 4
        ): 
        super().__init__()

        self.logger.info(f"cell_node: {cell_node}")
        assert str(cell_node) in CELL_NODE_LOOKUP.keys(), f"Unsupported cell node, must be a recognized key: {CELL_NODE_LOOKUP.keys()}"
        self.cell_node = CELL_NODE_LOOKUP[cell_node]

        assert forecast in FORECAST_OPTIONS, f"Unsupported forecast mode, must be one of the following: {FORECAST_OPTIONS}"
        self.forecast = forecast

        self.clock_derate = clock_derate
        self.frequency = 1/global_cycle_seconds/self.clock_derate
        self.phase_count = phase_count

        self.qfp_count = self.get_device_count()

    @abstractmethod
    def get_device_count(self): 
        pass

    @actionDynamicEnergy
    def read(self) -> float: 
        # all AQFP energy dissipation is leakage
        return 0

    def leak(self) -> float: 
        self.logger.info(f"{self.name} leakage")
        energy_per_cycle = self.lookup_energy(self.frequency)
        self.logger.info(f"at {self.frequency:.2e} Hz each AQFP dissipates {energy_per_cycle*1e21:.3} zJ")
        return self.qfp_count*energy_per_cycle / self.clock_derate

    def lookup_energy(self, frequency: float) -> float: 
        # E_sw = 2Phi0*I_c*(t_j/t_x) -> JJ time constant / switching speed
        # N. Takeuchi, et. al. "AQFP: A Tutorial Review",
        # https://doi.org/10.1587/transele.2021SEP0003
        PHI0 = 2.07e-15  
        
        # assume SFQ5ee process with unshunted 50uA JJ: 
        #  -> Bc = 544
        #  -> Cs = 3.5e14 F/m^2
        #  -> Jc = 100 uA/um^2
        tj = np.sqrt(2*np.pi*PHI0*3.5e-14/(544*100e-6))
        tx = 1/(4*frequency)
        E_sw = 2*PHI0*50e-6*(tj/tx)
        return E_sw

    def get_area(self) -> float:
        if self.forecast == "conservative":
            # 30% routing overhead
            routing = 1.3
        elif self.forecast == "moderate":
            # 20% routing overhead
            routing = 1.2
        else:
            # 10% routing overhead
            routing = 1.1
        self.logger.info(f"{self.forecast} routing overhead: {round(100*(routing-1))}%")
        area = self.qfp_count * self.cell_node["area"] * routing
        return area

class SRLoop(AQFPEstimator):
    '''
    Estimator for AQFP Set-Reset Loop register

    citation
        L.C. Blackburn, et. al. "A Compact Serial Memory Cell for Adiabatic Quantum Flux Parametron Register Files", Aug 2025
        https://doi.org/10.1109/TASC.2025.3540048
        *values account for additional improvements in layout density since published result

    args: 
        cell_bit_depth: bit depth for a single cell in the register array
        array_w: array width 
        array_h: array height
    '''
    name = "aqfp_reg_sr"
    percent_accuracy_0_to_100 = 80

    def __init__(self, 
                 cell_bit_depth: int, 
                 array_w: int, 
                 array_h: int, 
                 cell_node: str, 
                 global_cycle_seconds: float,
                 clock_derate: float = 1,
                 forecast: str = "conservative",
                 phase_count: int = 4):
        
        self.cell_bit_depth = cell_bit_depth
        self.array_w = array_w 
        self.array_h = array_h
    
        # note you need to define component specific arguments before initializing super() 
        # if the args are used in the abstract methods 
        super().__init__(cell_node, global_cycle_seconds, clock_derate, forecast, phase_count)
        
        self.logger.info("SRLoopProjected Estimator initialized.")

        self.logger.info(f"{self.array_w} x {self.array_h} x {self.cell_bit_depth}-bit SRLoop has {self.qfp_count} AQFPs.")
        
    def get_device_count(self): 
        qfp_per_cell = self.cell_bit_depth*4 + 5 
        count = self.array_w * self.array_h * qfp_per_cell
        return count
    
    @actionDynamicEnergy
    def read(self) -> float:
        self.logger.info("SRLoopProjected is estimating energy of read op")
        return 0
    
    @actionDynamicEnergy
    def write(self) -> float:
        self.logger.info("SRLoopProjected is estimating energy of write op")
        return 0
    
    @actionDynamicEnergy
    def update(self) -> float:
        return self.read() + self.write()
    

class IntAddRCSA(AQFPEstimator):
    '''
    ripple carry split adder (RCSA) with AQFP logic 
        like a ripple carry adder, but the carry is separated from the
        sum so that the throughput is improved 

    args: 
        depth: bit depth of the adder 
    '''
    name = "aqfp_intadder_rcsa"
    percent_accuracy_0_to_100 = 80

    def __init__(
            self, 
            depth: int, 
            cell_node: str, 
            global_cycle_seconds: float, 
            clock_derate: int = 1,
            forecast: str = "conservative", 
            phase_count: int = 4
            ):
        self.depth = depth
        assert depth%4 == 0, f"Adder bit depth must be a multiple of 4"

        super().__init__(cell_node, global_cycle_seconds, clock_derate, forecast, phase_count)
        self.logger.info("AQFP intadd Estimator initialized: IntAddRCSA")

        self.logger.info(f"{self.depth}-bit RCSA adder has {self.qfp_count} AQFP devices.")

    def get_device_count(self):
        if self.forecast != "conservative": 
            self.logger.warning("Only conservative forecast supported in adder at this time! Switching to conservative projections . . . ")
            self.forecast = "conservative"
        
        if self.forecast == "conservative":
            fourbit = 183       # device count for conservative 4-bit int RCSA
            m = self.depth / 4
            count = m*fourbit + 128*(m*(m-1)/2) + 64*(m*(m-1)/2)
        return count
    
    @actionDynamicEnergy
    def add(self) -> float: 
        # all AQFP energy dissipation is leakage
        self.logger.info("AQFP IntAdd add op")
        return 0 


class IntMult(AQFPEstimator): 
    '''
    Integer multiplier with AQFP logic 
    
    args: 
        depth: bit depth of multiplier
    '''
    name = "aqfp_intmult"
    percent_accuracy_0_to_100 = 50

    def __init__(
            self, 
            depth: int, 
            cell_node: str, 
            global_cycle_seconds: float, 
            clock_derate: int = 1,
            forecast: str = "conservative", 
            phase_count: int = 4
    ):
        self.depth = depth
        assert depth % 4 == 0, "Multiplier bit depth must be a multiple of 4"

        super().__init__(cell_node, global_cycle_seconds, clock_derate, forecast, phase_count)
        self.logger.info("AQFP intmult Estimator initialized: IntMult")

        self.logger.info(f"{self.depth}-bit intmult has {self.qfp_count} AQFP devices.")

    def get_device_count(self):
        fourbit_mult_count = 1052   # not yet published LL design
        # multipliers scale by factor of 4 every time bit depth is doubled
        n = np.log2(self.depth/4)
        return 4**n * fourbit_mult_count
    
    @actionDynamicEnergy
    def mult(self) -> float: 
        # all AQFP energy dissipation is leakage
        self.logger.info("AQFP IntMult mult op")
        return 0 
