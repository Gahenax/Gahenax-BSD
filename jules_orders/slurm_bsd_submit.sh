#!/bin/bash
#SBATCH --job-name=Gahenax_BSD_Phase3
#SBATCH --output=logs/bsd_mpi_%j.out
#SBATCH --error=logs/bsd_mpi_%j.err
#SBATCH --nodes=4                   # Number of physical nodes
#SBATCH --ntasks-per-node=32        # Number of MPI ranks per node (usually cores)
#SBATCH --time=48:00:00             # Max wall-clock time
#SBATCH --partition=compute         # Cluster partition (queue)
#SBATCH --mem-per-cpu=2G            # RAM per core (needs ~2G for large mpmath)

# Unload any conflicting modules and load MPI/Python
module purge
module load python/3.10 openmpi/4.1.4

# Activate virtual environment
source venv/bin/activate

# Set PYTHONPATH to repository root
export PYTHONPATH=$(pwd)

echo "Starting Gahenax-BSD on $SLURM_JOB_NUM_NODES nodes with $SLURM_NTASKS total ranks."

# Execute using mpirun
# mpirun will automatically spawn the correct number of processes across nodes
mpirun python jules_orders/mpi_bsd_dispatch.py --family rank7_elkies --radius 100 --step 5
