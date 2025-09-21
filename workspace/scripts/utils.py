import os
import sys
import glob
try:
    import pytimeloop.timeloopfe.v4 as tl
    import pytimeloop.timeloopfe as timeloopfe
except ImportError:
    import timeloopfe.v4 as tl
    import timeloopfe
import threading
import shutil
import logging
from joblib import Parallel, delayed
from tqdm import tqdm

THIS_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(THIS_SCRIPT_DIR)
from tl_post_processing import *


def get_run_dir(sub_arch: str):
    out_dir = os.path.join(
        THIS_SCRIPT_DIR,
        "..",
        "examples",
        "outputs",
        f"{sub_arch}_{threading.get_ident()}_{os.getpid()}",
    )
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
        
    os.makedirs(out_dir, exist_ok=True)
    return out_dir

    
def get_spec(sub_architecture: str, **kwargs):
    return tl.Specification.from_yaml_files(
        "../models/top.yaml.jinja2",
        jinja_parse_data=dict(sub_architecture=sub_architecture, **kwargs)
    )


def generate_result(
    sub_architecture: str, 
    batch_size: int, 
    add_cooling: bool = True,
    return_none_on_fail: bool = False,
    **kwargs
):
    try:
        spec = get_spec(sub_architecture, **kwargs)
        spec.variables["BATCH_SIZE"] = batch_size
        out_dir = get_run_dir(sub_architecture)
        result = tl.call_mapper(
            spec, 
            output_dir=out_dir,
            log_to=f'{out_dir}/log.txt'
        )
        result.clear_zero_energies()
        result.clear_zero_areas()
        if add_cooling:
            add_cooling_overhead(result, spec)
        
        return result
    except Exception as e:
        if not return_none_on_fail:
            raise e
        print(f'Failed to generate result for sub_architecture: {sub_architecture}')
        return None


def get_per_component_temperature(component_keys, spec):
    nodes = spec["architecture"]["nodes"]
    comp_attr = {
        nodes[i]["name"]: nodes[i]["attributes"]
        for i in range(len(nodes)) if nodes[i]["name"] in component_keys
    }
    # assume room temperature (300K)if not specified
    return {
        k: v["temperature"] if "temperature" in v else 300
        for k, v in comp_attr.items()
    }


def add_cooling_overhead(result, spec):
    '''
    Cooling overhead calculated for SHI Cryogenics RDE-418D4 4K Cryocooler 
    (https://shicryogenics.com/product/rde-418d4-4k-cryocooler-series/)
    with F-50 compressor (https://shicryogenics.com/product/f-50-indoor-water-cooled-compressor-series/)

    heat capacity maps: https://shicryogenics.com/wp-content/uploads/2020/09/RDE-418D4_Capacity_Map-2.pdf

    compressor draws 7.5kW at 60Hz 
    T1 is first stage temperature, T2 is second stage temp
    specific heat capacity is (power at RT) / (power at stage)

    T2 = 4K, maximum heat capacity is 2W -> specific heat capacity is 3750 W/W
        with this we get 80W heat capacity at stage 2 for "free" with T2 = 70K

    if we aren't cooking to 4K, just take specific heat capacity from first stage
    T1 = 70K, maximum heat capacity is 80W -> specific heat capacity is 93.75
    '''
    # first extract temperatures for each component from spec
    comp_temp = get_per_component_temperature(
        result.per_component_energy.keys(), spec
    )
    
    # determine if there will be 4K cooling or not
    # if there is 4K cooling, then we get 80W of heat for "free" at stage 1
    # if there is not, then we need separate 70K cooling system 
    cooling_to_4K = (
        True if any(v < 10 for v in comp_temp.values()) else False
    )
    for k,v in comp_temp.items():
        if v is None:
            continue
        
        # if room temp 
        if v > 200 and v < 300:
            # no need to add overhead
            continue
        
        # circuit at first stage 
        if v > 10 and v < 80: 
            if cooling_to_4K:
                power = (result.per_component_energy[k] /
                         (result.cycles * result.cycle_seconds))
                if power < 80:
                    continue    
                else: 
                    result.per_component_energy[k] = (
                        result.per_component_energy[k] * 93.75
                    )
                    logging.info(
                        f"Power at first stage exceeds 80W for {k}: {power}W"
                    )
                    logging.info(
                        f"Added 93.75x overhead to {k} for first stage"
                    )
            else:
                result.per_component_energy[k] = (
                    result.per_component_energy[k] * 93.75
                )
                logging.info(f"Added 93.75x overhead to {k} for first stage")

        # circuit at second stage
        if v < 10:
            result.per_component_energy[k] = (
                result.per_component_energy[k] * 1000 #3750
            )
            logging.info(f"Added 3750x overhead to {k} for second stage")
    
    # update total energy
    result.energy = sum(result.per_component_energy.values())
    return

def parallel(jobs):
    return Parallel(n_jobs=-1)(tqdm(list(jobs)))