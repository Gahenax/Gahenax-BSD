#!/bin/bash
# run_htcondor_chunk.sh - Executed by HTCondor on Jules-Forge (Katsina) Nodes
# Arguments: $1 = Condor Process ID (Chunk Number)

if [ -z "$1" ]; then
    echo "Error: Missing chunk ID argument from HTCondor \$(Process)"
    exit 1
fi

CHUNK_ID=$1
echo "=========================================================="
echo " Starting HTCondor Job Chunk $CHUNK_ID on $(hostname)"
echo "=========================================================="

# Ensure output directories exist
mkdir -p evidence/phase3/logs

# Execute the dispatch script specifying the chunk
# Adjust --family and other parameters as needed by the campaign
python jules_orders/jules_bsd_dispatch_p3_multi.py --family rank7_elkies --chunk $CHUNK_ID

echo "=========================================================="
echo " Finished Chunk $CHUNK_ID. Compressing telemetry..."
echo "=========================================================="

# Compress telemetry for extraction (LANCIS policy: don't store raw data)
tar -czf evidence/phase3/telemetry_chunk_${CHUNK_ID}.tar.gz evidence/phase3/manifest_*.json evidence/phase3/verdicts_*.jsonl evidence/phase3/telemetry_*.jsonl

# Clean up uncompressed files
rm evidence/phase3/*.json evidence/phase3/*.jsonl

echo "Deployment complete."
