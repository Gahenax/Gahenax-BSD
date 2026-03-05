#!/bin/bash
#PBS -N Gahenax_BSD_Phase3
#PBS -o logs/bsd_mpi.out
#PBS -e logs/bsd_mpi.err
#PBS -l nodes=4:ppn=32              # 4 nodes, 32 processors per node
#PBS -l walltime=48:00:00           # Max wall-clock time
#PBS -q batch                       # Queue name
#PBS -l pmem=2gb                    # Memory per process

# Change to submitting directory
cd $PBS_O_WORKDIR

# Load MPI and Python modules
module purge
module load python/3.10 openmpi/4.1.4

# Activate virtual environment
source venv/bin/activate
export PYTHONPATH=$(pwd)

echo "Starting Gahenax-BSD on PBS Cluster."

# Execute using mpiexec
mpiexec python jules_orders/mpi_bsd_dispatch.py --family rank7_elkies --radius 100 --step 5
