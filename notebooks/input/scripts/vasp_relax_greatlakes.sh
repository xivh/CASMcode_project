#!/bin/bash
#SBATCH --job-name={{ job_name }}
#SBATCH --time={{ time }}
#SBATCH --nodes={{ nodes }}
#SBATCH --ntasks={{ ntasks }}
#SBATCH --mem-per-cpu={{ mem_per_cpu }}
#SBATCH --account={{ account }}
#SBATCH --partition={{ partition }}

module load RestrictedLicense
module load vasp/{{ vasp_version }}

# Max number of relaxation runs to allow
IMAX={{ imax }}

echo "{\"status\": \"started\"}" > status.json

# Set I to the last "run.$I" directory present
I=0
while [ -d "run.$I" ]; do
  I=$(($I+1))
done
I=$(($I-1))

# Run vasp in the "run.$I" directory and collect the number of
# ion relaxation steps
cd run.$I
mpirun vasp >& stdout
NSTEPS=$(cat stdout | grep E0 | wc -l)
cd ..

# Loop to perform ionic relaxation until there was only one step
# in the run or the maximum number of relaxation runs reached
while [ $NSTEPS -gt 1 ] && [ $I -lt $IMAX ]
do
 I=$(($I+1))
 cp -r run.$(($I-1)) run.$I
 rm run.$(($I-1))/POTCAR
 cd run.$I
 cp CONTCAR POSCAR
 mpirun vasp >& stdout
 NSTEPS=$(cat stdout | grep E0 | wc -l)
 cd ..
done

# Run a final static calculation in `run.final`
I=$(($I+1))
cp -r run.$(($I-1)) run.final
rm run.$(($I-1))/POTCAR
cd run.final
cp CONTCAR POSCAR

sed -i "s/.*IBRION.*/IBRION = -1/g" INCAR
sed -i "s/.*NSW.*/NSW = 0/g" INCAR
sed -i "s/.*ISIF.*/ISIF = 2/g" INCAR
sed -i "s/.*ISMEAR.*/ISMEAR = -5/g" INCAR

mpirun vasp >& stdout
cd ..

echo "{\"status\": \"complete\"}" > status.json
