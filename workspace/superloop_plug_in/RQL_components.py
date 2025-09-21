import os
import numpy as np
from accelergy.plug_in_interface.estimator import (
    Estimator,
    actionDynamicEnergy
)

'''
Library of RQL components for processing and on-chip storage 
all values are taken from the Stony Brook University RQL VHDL cell library tuned for the
MITLL 10 kA/cm^2 248nm process 

citation:
    M. Dorojevets, et. al., "Towards 32-bit Energy-Efficient Superconductor  RQL Processors: The Cell-Level 
        Design and Analysis  of Key Processing and On-Chip Storage Units", (2014)
        https://doi.org/10.1109/TASC.2014.2368354

in this paper, energy and power dissipation is given as a combined static and dynamic term
but we need them separated for leakage vs dynamic power

dynamic power is estimated as, P = (2/3) sum(Ic(i)*PHI0*f)


'''

class IntMult(Estimator):
    '''
    Integer multiplier Table 1
    '''
    name = "rql_intmult"
    percent_accuracy_0_to_100 = 80

    def __init__(self, depth: int):
        self.depth = depth
        
        self.logger.info(f"RQL IntMult Estimator initialized: IntMult, {self.depth}-bit")
    
    @actionDynamicEnergy
    def mult(self) -> float:
        return 0