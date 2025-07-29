#!/bin/bash
#SBATCH --job-name={{ job_name }}
#SBATCH --time={{ time }}
#SBATCH --nodes={{ nodes }}
#SBATCH --ntasks={{ ntasks }}
#SBATCH --mem-per-cpu={{ mem_per_cpu }}
#SBATCH --account={{ account }}
#SBATCH --partition={{ partition }}

echo "------------------------------------------------------"
echo "Job ID: $SLURM_JOB_ID"
echo "Allocated nodes: $SLURM_NODELIST"
echo "------------------------------------------------------"
echo ""

echo "~~~ Beginning VASP relaxation ~~~"
echo "cwd:"
echo "$(pwd)"
echo "ls -hl:"
ls -hl
echo ""

# Get the start time:
STARTTIME=$(date +%Y-%m-%dT%H:%M:%S)

module load RestrictedLicense
module load vasp/{{ vasp_version }}

# Max relaxation run index to allow
IMAX={{ imax }}

# Absolute path to status.json:
STATUS_JSON=$(realpath status.json)
TMP_JSON=$(realpath tmp.json)

echo "~~~ Updating status.json ~~~"

# If "status.json" does not exist, create it as an empty JSON object
if [ ! -f status.json ]; then
  echo '{}' > status.json
fi

# Update the status to "started" and add the job ID
jq --arg status "started" --arg jobid "$SLURM_JOB_ID" --arg starttime "$STARTTIME" \
  '.status = $status | .jobid = $jobid | .starttime = $starttime' status.json > tmp.json && \
  mv tmp.json status.json

cat status.json

# Exit immediately if a command exits with a non-zero status
set -e

# Define a cleanup function
cleanup() {
  echo "~~~ Cleanup initiated ~~~"
  echo "~~~ Updating status.json ~~~"

  # Get the stop time:
  STOPTIME=$(date +%Y-%m-%dT%H:%M:%S)

  if [ "$COMPLETED" != "true" ]; then
    echo "Job was stopped prematurely."
    STATUS="stopped"
  else
    echo "Job completed successfully."
    STATUS="complete"
  fi

  # Update the status to "complete"
  jq --arg status "$STATUS" --arg stoptime "$STOPTIME" \
    '.status = $status | .stoptime = $stoptime' $STATUS_JSON > $TMP_JSON && \
    mv $TMP_JSON $STATUS_JSON
  cat $STATUS_JSON

  echo "~~~ Cleanup complete ~~~"
}

# Trap termination signals and call the cleanup function
trap cleanup EXIT TERM INT

# Initialize the completion flag
COMPLETED=false

# Set I to the last "run.$I" directory present
I=0
while [ -d "run.$I" ]; do
  I=$(($I+1))
done
I=$(($I-1))

echo "~~~ Starting VASP relaxation loop ~~~"

# Run vasp in the "run.$I" directory and collect the number of
# ion relaxation steps
cd run.$I
echo "Begin run.$I..."
mpirun vasp >& stdout
NSTEPS=$(cat stdout | grep E0 | wc -l)
cd ..

# Loop to perform ionic relaxation until there was only one step
# in the run or the maximum number of relaxation runs reached
while [ $NSTEPS -gt 1 ] && [ $I -lt $IMAX ]
do
  echo "Continue relaxation runs..."
  I=$(($I+1))
  cp -r run.$(($I-1)) run.$I
  rm run.$(($I-1))/POTCAR
  cd run.$I
  rm OUTCAR
  cp CONTCAR POSCAR
  echo "Begin run.$I..."
  mpirun vasp >& stdout
  NSTEPS=$(cat stdout | grep E0 | wc -l)
  cd ..
done


echo "~~~ Starting final static calculation ~~~"

# Run a final static calculation in `run.final`
I=$(($I+1))
cp -r run.$(($I-1)) run.final
rm run.$(($I-1))/POTCAR
cd run.final
rm OUTCAR
cp CONTCAR POSCAR

sed -i "s/.*IBRION.*/IBRION = -1/g" INCAR
sed -i "s/.*NSW.*/NSW = 0/g" INCAR
sed -i "s/.*ISIF.*/ISIF = 2/g" INCAR
sed -i "s/.*ISMEAR.*/ISMEAR = -5/g" INCAR

echo "Begin run.final..."
mpirun vasp >& stdout
cd ..


# Set the completion flag to true before normal exit
COMPLETED=true

echo "~~~ VASP relaxation script completed ~~~"

