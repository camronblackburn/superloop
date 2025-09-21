import numpy as np
import os

from accelergy.plug_in_interface.estimator import (
    Estimator,
    actionDynamicEnergy,
)

THIS_SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))

# Delft Cri/oFlex signal line losses
# freq: dB/m
DELFT_S21 = {
    "300K": {
        "0": -6,
        "1": -8,
        "5": -15, 
        "10": -21.5,
        "15": -27
    }, 
    "4K": {
        "0": 0,
        "1": -1.5, 
        "5": -4, 
        "10": -6, 
        "15": -8.5
    }
}

#######
# Heatload values [stage1, stage2]
CRYOCABLE_LOAD = {
    "delft_crioflex_Ag": [2.7e-3, 0.8e-3],
    "BeCu_hypres_stripline1": [1.48e-3, 0.44e-3],
    "BeCu_hypres_stripline2": [2.5e-3, 0.74e-3], 
    "BeCu_hypres_stripline3": [3.78e-3, 1.118e-3], 
    "BeCu_hypres_coax": [8.35e-3, 2.473e-3]
}
# Hypres values come from Deepnarayan Gupta et. al., "Digital Output Data Links from Superconductor Integrated Circuits"
#                           # https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=8686133
# since 50K stage values were not given for the Hypres cables, the scaling from 4K->50K for the Delft cables was assumed 


class Cables(Estimator):
    '''
    This plug-in component models the heatload from cryogenic cables between temperature stages
    Since data-dependent losses in the hot2cold and cold2hot interconnects are handled in their respective 
    network components, this only models a constant leakage. 

    the heatload of a cable will can be set by passing in a supported `type` attribute: 
        "delft_crioflex"
        "BeCu" 
    OR setting `type` to 0 and providing values for `stage1_load` and `stage2_load`

    note, bandwidth CANNOT be set from a plug-in component, so must be set in YAML variables 

    args:
        hot_temp
        cold_temp
        channel_count
        type (opt)
        electrical_only (opt): If passed True, the cable heatload will be ignore and 0 leakage energy returned.
            defaults to False

    '''
    name = "cryocable"
    percent_accuracy_0_to_100 = 90

    def __init__(self,
                 global_cycle_seconds: float, 
                 hot_temp: float,
                 cold_temp: float,
                 channel_count: int,
                 type: str = "delft_crioflex", 
                 electrical_only: bool = False,
                 stage1_load: float = 0, 
                 stage2_load: float = 0
                 ):
        super().__init__()
        self.hot_temp = hot_temp
        self.cold_temp = cold_temp
        self.channel_count = channel_count
        self.electrical_only = electrical_only
        self.freq = 1/global_cycle_seconds

        self.route = ""
        if self.hot_temp > 100 and self.cold_temp > 10:
            self.route = "RT->1"
        if self.hot_temp < 100 and self.cold_temp < 10:
            self.route = "1->2"
        if self.hot_temp > 100 and self.cold_temp < 10: 
            self.route = "RT->2"
        if self.hot_temp == self.cold_temp:
            self.route = "stationary"

        self.logger.info(f"CryoCable initialized. Data route is {self.route}.")

        assert self.route != "", "Hot2ColdNetwork must be defined for routes in typical two stage cryocooler"

        self.type = type
        if self.type == 0:
            self.stage1_load = stage1_load
            self.stage2_load = stage2_load
        else:
            assert self.type in CRYOCABLE_LOAD.keys(), f"If using cryocable type, it must be in: {CRYOCABLE_LOAD.keys()}. or set type to 0 and provide stage1_load and stage2_load"
            self.stage1_load = CRYOCABLE_LOAD[self.type][0]
            self.stage2_load = CRYOCABLE_LOAD[self.type][1]
        
        self.logger.info(f"Stage1 (warm) cable heatload set to {self.stage1_load}; Stage2 (cold) cable set to {self.stage2_load}")

    def leak(self, global_cycle_seconds: float) -> float:
        if self.electrical_only:
            return 0

        if self.route == "RT->1":
            heatload = self.stage1_load
        if self.route == "1->2":
            heatload = self.stage2_load
        if self.route == "RT->2":
            heatload = self.stage1_load + self.stage2_load
        if self.route == "stationary":
            heatload = 0

        self.logger.info(f"single cable heatload is {heatload / self.freq}")

        return (heatload / self.freq)*self.channel_count

    # read handled in network components
    @actionDynamicEnergy
    def read(self) -> float:
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



class Hot2ColdNetwork(Estimator):
    '''
    This network component accounts for power dissipation when data is traveling from hot to cold in 
    a multi-stage cryocooler.
    It is assumed that data are only traveling between three possible temperature ranges: 
        - Room temperature (anything above 100K)
        - first stage (100K to 10K)
        - second stage (anything below 10K)

    Heat load and losses in tha cables are assumed to match the Delft Cri/oFlex signal lines
        50 Ohm flex Ag striplines
        https://delft-circuits.com/wp-content/uploads/2024/03/productsheets-Signal-line-22-febr-2024-.pdf

    The electrical losses in the cable depend on voltage load at the cold temp receiver, which can be
    optionally provided as an attribute, but will default to 2.5mV to drive a 50uA AQFP input.

    args:
        datawidth: width of data passed through the network
        hot_temp: temperature of the hot stage in Kelvin
        cold_temp: temperature of the cold stage in Kelvin
        electrical_only (False): if True, only account for electrical power dissipation
            and ignore thermal power load 
        length (opt): optional length of cabiling paramerter, will default to specs from SHI two 
            stage GM cryocooler if not provided
        v_load (opt): voltage load a cold head receiver, if not provided will assume 2.5mV
            to drive 50uA AQFP 
        global_cycle_seconds (always passed from accelergy): system period 
    '''
    name = "hot2cold_network"
    percent_accuracy_0_to_100 = 70

    def __init__(self,
                 global_cycle_seconds: float,
                 datawidth: int,
                 hot_temp: float,
                 cold_temp: float,
                 channel_count: int,
                 electrical_only: bool = False,
                 length: float = 0,
                 v_load: float = 2.5e-3,  # assume driving 50uA AQFP if not provided
                 ):
        super().__init__()
        self.datawidth = datawidth
        self.hot_temp = hot_temp
        self.cold_temp = cold_temp
        self.channel_count = channel_count
        self.electrical_only = electrical_only
        self.length = length
        self.v_load = v_load
        self.freq = 1/global_cycle_seconds

        self.route = ""
        if self.hot_temp > 100 and self.cold_temp > 10: 
            self.route = "RT->1"
        if self.hot_temp < 100 and self.cold_temp < 10: 
            self.route = "1->2"
        if self.hot_temp > 100 and self.cold_temp < 10: 
            self.route = "RT->2"
        if self.hot_temp == self.cold_temp:
            self.route = "stationary"

        assert self.route != "", "Hot2ColdNetwork must be defined for routes in typical two stage cryocooler"

    @actionDynamicEnergy
    def read(self) -> float:
        if self.route == "stationary":
            return 0

        # get S21/m from DELFT plots, scaling to match frequency provided
        if self.cold_temp > 50: 
            S21 = np.interp(self.freq, list(DELFT_S21["300K"].keys()), list(DELFT_S21["300K"].values()))
        else:
            S21 = np.interp(self.freq, list(DELFT_S21["4K"].keys()), list(DELFT_S21["4K"].values()))
        self.logger.info(f"S21/m from interpolation: {S21}")
        
        if self.length == 0: 
            if self.route == "RT->1": 
                # assume SHI RT to stage 1 cable length
                self.length = 320e-3
            if self.route == "1->2": 
                # assume SHI stage 1 to stage 2 cable length
                self.length = 240e-3 
            if self.route == "RT->2": 
                # assume SHI RT to stage 2 cable length
                self.length = 560e-3
        S21 = S21 * self.length

        self.logger.info(f"Setting S21 loss in {self.length} cable to: {S21}dB")
        S21 = 10**(S21/10)  # convert to linear
        
        p_diss = (self.v_load**2 / 50) * (1/(S21**2) - 1)
        e_diss = p_diss / self.freq
        self.logger.info(f"Energy dissipated on hot->cold single bit transfer: {e_diss}")
        return e_diss*self.datawidth

    def leak(self, global_cycle_seconds: float) -> float:
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


class Cold2HotNetwork(Estimator):
    '''
    This component accounts for power dissipation when data are traveling from COLD to HOT in 
    a multi-stage cryocooler.
    It is assumed that data are only traveling between three possible temperature ranges: 
        - Room temperature (anything above 100K)
        - first stage (100K to 10K)
        - second stage (anything below 10K)

    We will NOT set a leakage energy in this component because we assume it's already account for in 
    Hot2ColdNetwork and don't want to double count each wire. 

    Moving from cold to hot is more energetically expensive than moving from hot to cold because the cryo-signal
    must be amplified to overcome thermal noise at the hot end receiver. 

    The type of amplifier used and the load at the receiver will strongly impact the energy dissipation. 
    The type of amplifier can be passed in as an attribute, but we will assume that we're always trying to drive 
    CMOS DRAM around 1V. 
        Vdd = 1.1V from the cryoCMOS memory paper used in the memory plug-in (https://doi.org/10.1109/JSSC.2024.3385696)
        
    To drive this high of a voltage, superconducting drivers are usually combined with semiconductor amplifiers. All of 
    our amplifiers will assume that superconducting drivers can drive 50 Ohm loads with ~40mVpp swing at stage 1 
    if stage 1 is the hot_temp, then the signal is passed to a CMOS diff amp to write DRAM signals
    if RT is the hot_temp, then the signal is amplified again at stage 1 with SiGe LNA and sent along to CMOS diff amp->DRAM at RT
    

    args: 
        channel_count: number of channels in the physical hot2cold network (sets the area)

        
    '''
    name = "cold2hot_network"
    percent_accuracy_0_to_100 = 70

    def __init__(self,
                 global_cycle_seconds: float,
                 datawidth: int,
                 hot_temp: float,
                 cold_temp: float,
                 channel_count: int, 
                 amp_type: str = "aqfp_diffamp",
                 v_load: float = 1.1,
                 ):
        super().__init__()
        self.datawidth = datawidth
        self.hot_temp = hot_temp
        self.cold_temp = cold_temp
        self.channel_count = channel_count

        amp_type_options = ["aqfp_diffamp", "JLD_diffamp", "nTron"]
        assert amp_type in amp_type_options, f"Unsupported amplifier type, must be one of the following: {amp_type_options}"
        self.amp_type = amp_type
        self.freq = 1/global_cycle_seconds
        
        self.route = ""
        if self.hot_temp > 100 and self.cold_temp > 10: 
            self.route = "1->RT"
        if self.hot_temp < 100 and self.cold_temp < 10: 
            self.route = "2->1"
        if self.hot_temp > 100 and self.cold_temp < 10: 
            self.route = "2->RT"
        if self.hot_temp == self.cold_temp:
            self.route = "stationary"
        assert self.route != "", "Cold2HotNetwork must be defined for routes in typical two stage cryocooler"

        # assume that all CMOS DRAM interfacing with superconducting circuit is optimized according to G. Konnopka et. al.
        # and has similar diff amp at the input to amplify to 1V
        diff_amp_power = 7.25e-3 / 17 # 7.25mW for write op of 64kB mem from Table III in G. Konnopka et. al.,
                                   #     assume 17 diff amps used in 64kB design (matches JLD count)
        self.diff_amp_energy = diff_amp_power / self.freq

        # assume amplification from stage 1 to RT is always SiGe LNA: https://www.qorvo.com/products/p/SGL0622Z#parameters
        lna_power = 3.3*10.5e-3 # W, from Qorvo datasheet
        self.lna_energy = lna_power / self.freq
        

    @actionDynamicEnergy
    def read(self) -> float:
        if self.route == "stationary":
            return 0
        if self.route == "1->RT":
            return self.lna_energy * self.datawidth
        
        if self.amp_type == "aqfp_diffamp":
            return self.aqfp_diffamp_energy()
        if self.amp_type == "JLD_diffamp":
            return self.JLD_diffamp_energy()
        if self.amp_type == "nTron":
            return self.nTron_energy()
        else:
            return 0

    def get_area(self) -> float:
        if self.route == "stationary":
            return 0
        if self.amp_type == "aqfp_diffamp":
            return self.aqfp_diffamp_area()
        if self.amp_type == "JLD_diffamp":
            return self.JLD_diffamp_area()
        if self.amp_type == "nTron":
            return self.nTron_area()
        else:
            return 0

    # Josephson Latching Driver to CMOS diff amp 
    # JLD (Suzuki stack) amplifies to 40mV-level, then CMOS diff amp gets up to 1.1V
    # circuit and design concept from G. Konnopka et. al. "Fully Functional Operation of Low-Power 64-kb
    #     Josephson-CMOS Hybrid Memories", June 2017; https://doi.org/10.1109/TASC.2016.2646911
    # but JLD power taken from more recent optimization: Y. Mustafa et. al., "Optimization of Suzuki Stack 
    #     Circuit to Reduce Power Dissipation" Nov 2022; https://doi.org/10.1109/TASC.2022.3192202
    # and diff amp power from G. Konnopka et. al. which was also driving optimized 1V cryoDRAM 
    #     (but at the same temperature stage)
    # 
    # we will assume that diff amp is always placed in front of the CMOS dram write logic 
    # and that a single super
    def JLD_diffamp_energy(self) -> float:
        JLD_power = 60e-6 # W, Ii/Ib = 0.7, Fig 4 in Mustafa et. al., 
        JLD_energy = JLD_power / self.freq
        
        if self.route == "2->RT":
            return (JLD_energy + self.diff_amp_energy + self.lna_energy) * self.datawidth
        elif self.route == "2->1":
            return (JLD_energy + self.diff_amp_energy) * self.datawidth
        else: 
            return 0
    
    def JLD_diffamp_area(self) -> float:
        # JLD will take up the majority of the footprint, so ignore CMOS diff amp
        # can extract from die image in Fig 4. Hironaka et. al. https://doi.org/10.1109/TASC.2020.2994208
        JLD_area = 0.420e-3 * 0.140e-3 # 420um by 140 um 
        return JLD_area*self.channel_count


    ## AQFP Suzuki-style amp with CMOS 
    # Suzuki stack-style amplifier but for AQFP logic amplifies signal to 40mV-level 
    #     with about 3e-7 W simulated dissipation 
    # assume we can pair with similar CMOS diff amp from G. Konnopka et. al. 
    def aqfp_diffamp_energy(self) -> float:
        aqfp_power = 3e-7 # W, from simulation
        aqfp_energy = aqfp_power / self.freq

        if self.route == "2->RT":
            return (aqfp_energy + self.diff_amp_energy + self.lna_energy) * self.datawidth
        elif self.route == "2->1":
            return (aqfp_energy + self.diff_amp_energy) * self.datawidth
        else: 
            return 0
    
    def aqfp_diffamp_area(self) -> float:
        aqfp_area = 20e-6 * 20e-6 # 20um by 20 um 
        return aqfp_area*self.channel_count


    ## nTron cryoamp 
    def nTron_energy(self) -> float:
        # assume exact set up as Q. Zhao, et. al. "A nanocryotron comparator can connect single-flux-quantum circuits to conventional electronics"
        #  doi: 10.1088/1361-6668/aa5f33
        # even though it's not quite right, 
        # FIX ME
        ntron_energy = 8e-18
        if self.route == "2->RT":
            return (ntron_energy + self.diff_amp_energy + self.lna_energy) * self.datawidth
        elif self.route == "2->1":
            return (ntron_energy + self.diff_amp_energy) * self.datawidth
        else: 
            return 0
    
    def nTron_area(self) -> float:
        ntron_area = 0.1 * 1e-6*1e-6  # 0.1um active area 
        return ntron_area*self.channel_count

    def leak(self, global_cycle_seconds: float) -> float:
        # account for in Hot2ColdNetwork
        # don't double count! 
        return 0

    # Write and update aren't used for networks
    @actionDynamicEnergy
    def write(self) -> float:
        return 0

    @actionDynamicEnergy
    def update(self) -> float:
        return self.write()