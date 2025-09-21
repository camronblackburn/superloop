## Superloop container 

**notes** on Timeloop/Accelergy output formats: 
timeloop-mapper.stats.txt
    - gives energies in pJ 
    per-instance-cycle leakage matches the value reported in Accelergy logs 
        sometimes - not exactly for multiplier 


cryocable: 
    per-instance-cycle leakage: 6.4pJ 
    total leakage: 5.5e10 pJ 

cold2hot: 
    timeloop stats
        leakage: 0 (make sense we don't have that set)
        vector access energy: 0.427 pJ 
        energy(total): 3.58e6
    timeloopfe
        per_component_energy: 3.58e-6
        per_compute_energy:


main memory: 
    timeloop stats
        vector access energy: 2.68e2 pJ 
        energy (per-scalar-access): 2.10 pJ
        energy (per instance): 8.79e6 pJ
        energy(total): 8.79e6 pJ
    ERT summary (pJ?)
        write: 217.008
        read: 268.288
        update: 22.732
    timeloopfe
        per_component_energy: 1.46e-5
        per_compute_energy: 1.71e-15 = 1.46e-5/computes 

commenting out temp network and running same workload: 
    main memory 
        timeloopfe
            per_component_energy: 0.003375
            per_compute_energy: 3.93e-13
        ERT summary: 
            write: 217.008
            read: 268.288
            update: 22.73
        timeloop stats
            vector access energy: 2.68e2

commenting out only the cable components with leakage
    main memory
        timeloopfe
            per_component_energy: 0.003375
            per_compute_energy: 3.93e-13
just needed to make sure to add no coalesce flag to cable components! it was storing some of the data outside of DRAM it looks like 