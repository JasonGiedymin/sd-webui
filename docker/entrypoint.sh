#!/usr/bin/env bash

set -e

pip install -U pip
pip install -r requirements.txt

source venv/bin/activate

for file in ./patches/*.patch
do
  echo "Testing patch, pay no mind to patch errors between the lines ..."
  echo "--------------------------------------------------------------------"
  if ! patch -Rsfp0 --dry-run < $file; then
  echo "--------------------------------------------------------------------"
    echo "--> applying patch [$file]"
    patch -N -p0 < $file
  else
    echo "--------------------------------------------------------------------"
    echo "patch [$file] applied, moving on ..."
  fi;
done;

echo "Purging pip cache in case of patches ..."
pip cache purge

# Fails on AMD as of right now ...
# python launch.py --precision full --no-half --force-enable-xformers

python launch.py --precision full --no-half
