import subprocess
from typing import Optional


def submit_slurm_job(
    working_dir: str,
    nodes: int = 1,
    ntasks: int = 2,
    cpus_per_task: int = 14,
    job_name: str = "dmo-64",
    partition: str = "RM",
    time: str = "16:00:00",
    email: str = "xiaowen4@andrew.cmu.edu",
    mem_per_cpu: str = "8G",
    mp_gadget_root: str = "/path/to/mp-gadget-root",
) -> Optional[str]:
    """
    Submit a SLURM job for MP-Gadget simulation.
    
    Args:
        working_dir: Working directory containing .genic and .gadget files
        nodes: Number of nodes
        ntasks: Number of MPI tasks
        cpus_per_task: CPUs per task
        job_name: SLURM job name
        partition: SLURM partition
        time: Time limit
        email: Email for notifications
        mem_per_cpu: Memory per CPU
        mp_gadget_root: Path to MP-Gadget installation
        
    Returns:
        Job ID if successful, None otherwise
    """
    if not working_dir.endswith("/"):
        working_dir += "/"
    
    template_script = f"""#!/bin/bash
#SBATCH --partition={partition}
#SBATCH --output={working_dir}run.out
#SBATCH --job-name={job_name}
#SBATCH --time={time}
#SBATCH -N {nodes}
#SBATCH --ntasks={ntasks}
#SBATCH --cpus-per-task={cpus_per_task}
#SBATCH --mail-type=END
#SBATCH --mail-user={email}
#SBATCH --mem-per-cpu={mem_per_cpu}

module load intel/2022.1.2
module load intelmpi/2022.1.2-intel2022.1.2 

export OMP_NUM_THREADS={cpus_per_task}
export I_MPI_JOB_RESPECT_PROCESS_PLACEMENT=0

ROOT={mp_gadget_root}
SCRIPT_ROOT_DIR={working_dir}

echo "Generating IC for set $k"
date
mpirun -np {ntasks} $ROOT/genic/MP-GenIC $SCRIPT_ROOT_DIR/output.genic || exit 1
echo "Running Gadget for set $k"
date
mpirun -np {ntasks} $ROOT/gadget/MP-Gadget $SCRIPT_ROOT_DIR/output.gadget || exit 1
echo "Finished set $k"
date"""
    
    # Save the script
    script_path = working_dir + "script.slurm"
    with open(script_path, "w") as f:
        f.write(template_script)
    
    # Submit the job
    try:
        result = subprocess.run(
            ["sbatch", script_path],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            # Extract job ID from output
            job_id = result.stdout.strip().split()[-1]
            return job_id
        else:
            print(f"SLURM submission failed: {result.stderr}")
            return None
    except Exception as e:
        print(f"Error submitting SLURM job: {e}")
        return None