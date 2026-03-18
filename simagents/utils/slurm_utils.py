"""SLURM job submission utilities."""
from __future__ import annotations
from simagents.config.settings import SLURMSettings


def generate_slurm_script(job_name: str, genic_param_file: str, gadget_param_file: str, mp_gadget_root: str, slurm_settings: SLURMSettings, output_dir: str = ".") -> str:
    return f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --partition={slurm_settings.partition}
#SBATCH --nodes={slurm_settings.nodes}
#SBATCH --ntasks-per-node={slurm_settings.ntasks}
#SBATCH --cpus-per-task={slurm_settings.cpus_per_task}
#SBATCH --time={slurm_settings.time}
#SBATCH --mem-per-cpu={slurm_settings.mem_per_cpu}
#SBATCH --output={output_dir}/{job_name}_%j.out

# Run GenIC to generate initial conditions
mpirun -np $SLURM_NTASKS {mp_gadget_root}/genic/MP-GenIC {genic_param_file}

# Run MP-Gadget simulation
mpirun -np $SLURM_NTASKS {mp_gadget_root}/gadget/MP-Gadget {gadget_param_file}
"""
