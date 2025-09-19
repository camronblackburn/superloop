import numpy as np
from accelergy.plug_in_interface.estimator import (
    Estimator,
    actionDynamicEnergy
)
from abc import ABC, abstractmethod

'''
A library of superconducting and cryoCMOS memory components 

notes & assumptions: 
- timeloop does not account for latency of components, it's assumed that everything 
    is optimally pipelined (designed for at a lower level of hierarchy)
    "get_latency" methods are not used by timeloop or accelergy

'''


class VTcellRAM(Estimator): 
    '''
    large arrays of superconducting VT cell memory

    citation: 
        V. Semenov et. al., "Very Large Scale Integration of Josephson-Junction-Based Superconductor Random Access Memories", Aug 2019.
        https://doi.org/10.1109/TASC.2019.2904971

    parameters: 
        cell_type (str): 
        width (int): 
        depth (int): 
    '''
    name = ["VTcellRAM", "VTcell_RAM"]
    percent_accuracy_0_to_100 = 80
    
    def __init__(self, 
                 global_cycle_seconds: float, 
                 width: int, 
                 depth: int
    ): 
        super().__init__()
        self.width = width
        self.depth = depth

        self.global_cycle_seconds = global_cycle_seconds

    @actionDynamicEnergy
    def read(self) -> float: 
        return 0
    
    @actionDynamicEnergy
    def write(self) -> float: 
        return 0
    
    @actionDynamicEnergy
    def update(self) -> float: 
        return 0
    
    def leak(self) -> float: 
        return 0
    
    def get_area(self) -> float: 
        return 0 


class DLMPassive(Estimator): 
    '''
    Delay Line Memory with passive transmission line 

    citation: 
        J. Volk et al. "Addressable superconductor integrated circuit memory from delay lines", 2023
        https://doi.org/10.1038/s41598-023-43205-8
    
    
    parameters: 
        line_depth (int): the number of bits stored in each delay line loop 
        line_count (int): the number of storage loops in the memory 
        time_bin (float): duration (in seconds) of a single bit time bin, default to global_cycle_seconds
            but doesn't need to be. 

    implementation assumptions: 
        - high memory capacity is achieved by arranging many delay lines in parallel 
        - if time_bin is different from global_cycle_seconds, additional logic is required to convert 
            between clock domains - this is *not* taken into account at the moment
        - 50% energy loss for biasing SFQ circuits 
    '''
    name = "dlm_ptl"
    percent_accuracy_0_to_100 = 80
    cell2density = {
        # [factor of speed of light, pitch]
        "Nb_mature": [0.298, 500],
        "Nb_aggressive": [0.296, 240],
        "MoN_ms_mature": [0.047, 500],
        "MoN_ms_aggressive": [0.034, 240],
        "MoN_sl_aggressive": [0.029, 240],
        "NbTiN_sl_academic": [0.011, 220],
        "NbN_academic": [0.007, 135],
    }

    def __init__(self, 
                 global_cycle_seconds: float, 
                 line_depth: int, 
                 line_count: int, 
                 time_bin: float = None,
                 cell_type: str = "NbN_academic"
    ): 
        super().__init__()

        assert cell_type in self.cell2density, f"cell type {cell_type} not in {self.cell2density.keys()}"
        self.type = cell_type

        self.global_cycle_seconds = global_cycle_seconds
        self.line_depth = line_depth
        self.line_count = line_count
        self.time_bin = time_bin
        if self.time_bin is None: 
            self.time_bin = self.global_cycle_seconds

        self.bias_overhead = 1.5    # 50% energy loss for biasing, pessimistic estimate


    @actionDynamicEnergy
    def read(self) -> float: 
        '''
        assumes no additional logic to read since output is available whether queried or not
        in reality, there must be some additional addressing logic 
        '''
        return 0
    
    @actionDynamicEnergy
    def write(self) -> float: 
        '''
        data passes additional DRO to write 

        B0 and B3 switch (Fig 5 in paper) -> 277uA + 188uA -> 9.57e-19 J
        '''
        return (9.57e-19) * self.bias_overhead * self.line_count
    
    @actionDynamicEnergy
    def update(self) -> float: 
        '''
        not relevant to DLM memory 
        '''
        return 0
    
    def leak(self) -> float: 
        ''' the energy dissipated each clock cycle, regardless of data path
    
            needs to switch first DRO2R (1.478 aJ) > merge (1.319 aJ) > 
            second DRO2R (1.478 aJ for reading pulse, 1.081 aJ for no pulse) 
            + JTLs not mentioned in the paper: 
                JTL for rank matching: 0.880 aJ
                JTL for receiving: 1.035 aJ
        
        the second DRO2R has data dependent value - take average
        '''
        pulse_prop = 6.19e-18  # dissipation each clock cycle regardless 
                                # of read or write, needed to update the pulse
        overclock = (self.global_cycle_seconds / self.time_bin) 
        return pulse_prop * self.bias_overhead * self.line_count * overclock
    
    def get_area(self) -> float: 
        '''
        following density calculation from paper 
        '''
        pulse_speed = self.cell2density[self.type][0]*3e8
        pitch = self.cell2density[self.type][1]*1e-9
        return (self.time_bin * pulse_speed * pitch) * self.line_depth * self.line_count
    

class nMem(Estimator): 
    '''
    Superconducting nanowire memory with hTron devices 

    citation: 
        O. Medeiros et al. "Scalable Superconducting Nanowire Memory Array with Row-Column Addressing", Aug 2025
        https://doi.org/10.48550/arXiv.2503.22897

    parameters: 
        width (int): width of array of cells 
        depth (int): depth of array of cells 

    implementation assumptions: 
        this paper describes detailed results for a simple 4x4 nMem 
        with no addressing. in scaling to main memory, we'll assume 
        just one memory block (not the best way to scale, but start 
        for now) - i.e. a large array of width x depth bit storage.
        assume we can read out a full row every clock cycle
    '''
    name = ["nMem"]
    percent_accuracy_0_to_100 = 80
    
    def __init__(self, 
                 global_cycle_seconds: float, 
                 width: int, 
                 depth: int
    ): 
        super().__init__()
        self.width = width
        self.depth = depth

        self.global_cycle_seconds = global_cycle_seconds
    
    # returns energy in J
    @actionDynamicEnergy
    def read(self) -> float: 
        # single bit pulse is 31fJ, from Table 1
        read_pulse = 31e-15 * self.width

        # read enable dissipation is determined by
        # the resistance of the read enable line (normal wire)
        # for 4 cell row, it's 270 Ohm (from suppl. materials)
        #    270 Ohm / 4 cell = 67.5 Ohm/cell 
        # avg read current bias is 185uA (from suppl. materials)
        read_enable = 185e-6 * 67.5 * self.width
        return read_pulse + read_enable
    
    @actionDynamicEnergy
    def write(self) -> float: 
        # single bit write pulse is 46fJ, from Table 1
        write_pulse = 46e-15 * self.width

        # write enable dissipation uses same enable line as read 
        # now avg current bias is 460uA
        write_enable = 460e-6 * 67.5 * self.width
        return write_pulse + write_enable
    
    @actionDynamicEnergy
    def update(self) -> float: 
        return 0
    
    def leak(self) -> float: 
        return 0
    
    # return area in m^2
    def get_area(self) -> float: 
        # nMem paper reports 2.6Mbit/cm^2, although unoptimized
        density = 2.6e6*100*100    # cm^2 to m^2
        total_bits = self.width * self.depth
        return total_bits/density

class AQFP_Dlatch(Estimator): 
    '''
    AQFP register file with D-latch storage cells

    citation: 
        N. Tsuji et. al., "Design and Implementation of a 16-word by 1-bit register file using AQFP logic", Jun 2017. 
        https://doi.org/10.1109/TASC.2017.2656128
        
    parameters: 
        cell_type (str): 
        width (int): 
        depth (int): 
    '''
    name = ["AQFP_Dlatch"]
    percent_accuracy_0_to_100 = 80
    
    def __init__(self, 
                 global_cycle_seconds: float, 
                 width: int, 
                 depth: int
    ): 
        super().__init__()
        self.width = width
        self.depth = depth

        self.global_cycle_seconds = global_cycle_seconds

    @actionDynamicEnergy
    def read(self) -> float: 
        return 0
    
    @actionDynamicEnergy
    def write(self) -> float: 
        return 0
    
    @actionDynamicEnergy
    def update(self) -> float: 
        return 0
    
    def leak(self) -> float: 
        return 0
    
    def get_area(self) -> float: 
        return 0 

class CryoDRAM(Estimator): 
    '''
    Cryogenic memory in 40nm CMOS 
    
    citation:
        R. Damsteegt et al. "A Benchmark of Cryo-CMOS Embedded SRAM/DRAMs in 40-nm CMOS", April 2024
        https://doi.org/10.1109/JSSC.2024.3385696

    all energy values are from 4.2K temp with LVT (low voltage threshold) transistors
    from Table II values in the paper, average of range given in the table is used here
    metrics from 32x32 array and includes drivers, addressing, etc. 

    parameters: 
        cell_type: str, the type of DRAM memory cell specified from cryoCMOS paper 
        width: int, the width of the DRAM array (probably datawidth), also will set bandwidth
        depth: int, the height of the DRAM array (number of rows), only used for area estimation

    '''
    name = ["cryo_DRAM", "cryoDRAM"]
    percent_accuracy_0_to_100 = 80
    cell2energies = {    # energy values in fJ
        # [read, write, refresh] 
        "2T_NW-PR": [346, 153.5, 22],
        "3T_NW-PR": [410, 156.5, 23.5],
        "3T_PW-PR": [262, 212, 22.2],
    }
    cell2area = {       # area values in um^2
        "2T_NW-PR": 0.084,
        "3T_NW-PR": 0.242,
        "3T_PW-PR": 0.254,
    }
    cell2latency = {       # latency values in ns
        "2T_NW-PR": 2.21,
        "3T_NW-PR": 1.22,
        "3T_PW-PR": 2.37,
    }

    def __init__(self, 
                 global_cycle_seconds: float, 
                 width: int, 
                 depth: int,
                 cell_type: str = "3T_PW-PR"
    ):
        super().__init__()

        assert cell_type in self.cell2energies, f"cell type {cell_type} not in {self.cell2energies.keys()}"
        self.type = cell_type
        self.width = width
        self.depth = depth

        self.global_cycle_seconds = global_cycle_seconds

    @actionDynamicEnergy
    def read(self) -> float: 
        return self.cell2energies[self.type][0] * 1e-15* self.width
    
    @actionDynamicEnergy
    def write(self) -> float: 
        return self.cell2energies[self.type][1] * 1e-15 * self.width
    
    @actionDynamicEnergy
    def update(self) -> float: 
        return self.cell2energies[self.type][2] * 1e-15 * self.width
    
    def leak(self) -> float: 
        # negligible leak at 4.2K 
        return 0
    
    def get_latency(self) -> float: 
        return self.cell2latency[self.type]
    
    def get_area(self) -> float: 
        return self.cell2area[self.type] * self.width * self.depth
    

class CryoSRAM(Estimator): 
    '''
    Cryogenic memory in 40nm CMOS 
    
    citation:
        R. Damsteegt et al. "A Benchmark of Cryo-CMOS Embedded SRAM/DRAMs in 40-nm CMOS", April 2024
        https://doi.org/10.1109/JSSC.2024.3385696

    all energy values are from 4.2K temp with LVT (low voltage threshold) transistors
    from Table II values in the paper, average of range given in the table is used here
    metrics from 32x32 array and includes drivers, addressing, etc. 

    same as DRAM except for different cell types; eventually figure out how to plug this
    into Cacti for more accurate metrics 

    parameters: 
        cell_type: str, the type of DRAM memory cell specified from cryoCMOS paper 
        width: int, the width of the DRAM array (probably datawidth), also will set bandwidth
        height: int, the height of the DRAM array (number of rows), only used for area estimation

    '''
    name = ["cryo_SRAM", "cryoSRAM"]
    percent_accuracy_0_to_100 = 80
    cell2energies = {    # energy values in pJ
        # [read, write] 
        "6T_static": [618, 473],
    }
    cell2area = {       # area values in um^2
        "6T_static": 0.435,
    }
    cell2latency = {       # latency values in ns
        "6T_static": 1.18,
    }

    def __init__(self, 
                 global_cycle_seconds: float, 
                 cell_type: str, 
                 width: int, 
                 depth: int
    ):
        super().__init__()

        assert cell_type in self.cell2energies, f"cell type {cell_type} not in {self.cell2energies.keys()}"
        self.type = cell_type
        self.width = width
        self.depth = depth

        self.global_cycle_seconds = global_cycle_seconds

    @actionDynamicEnergy
    def read(self) -> float: 
        return self.cell2energies[self.type][0] * 1e-15 * self.width
    
    @actionDynamicEnergy
    def write(self) -> float: 
        return self.cell2energies[self.type][1] * 1e-15 * self.width
    
    @actionDynamicEnergy
    def update(self) -> float: 
        return self.cell2energies[self.type][2] * 1e-15 * self.width
    
    def leak(self) -> float: 
        # negligible leak at 4.2K 
        return 0
    
    def get_latency(self) -> float: 
        return self.cell2latency[self.type]
    
    def get_area(self) -> float: 
        return self.cell2area[self.type] * self.width * self.depth
