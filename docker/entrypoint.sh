#!/usr/bin/env bash

set -e

source venv/bin/activate

python3 -m pip install -U pip
python3 -m pip install -r requirements.txt

source venv/bin/activate

for file in ./patches/*.patch
do
  if [ -f $file ]; then
    echo "Testing patch ..."
    echo "--------------------------------------------------------------------"
    if patch -Rsfp0 --dry-run < $file; then
      echo "--------------------------------------------------------------------"
      echo "--> applying patch [$file]"
      patch -N -p0 < $file
    else
      echo "--------------------------------------------------------------------"
      echo "patch [$file] applied, moving on ..."
    fi;
  fi;
done;

echo "Purging pip cache in case of patches ..."
python3 -m pip cache purge

# Fails on AMD as of right now ...
# python launch.py --precision full --no-half --force-enable-xformers

python3 launch.py --xformers --reinstall-xformers --precision full --no-half
