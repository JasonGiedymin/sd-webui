#!/usr/bin/env bash

set -e

source venv/bin/activate

python3 -m pip install -U pip
python3 -m pip install -r requirements.txt

source venv/bin/activate

for file in ./patches/*.patch
do
  if [ -f $file ]; then
    echo "Testing patch, pay no mind to patch errors between the lines ..."
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

check_cuda="$(python -c 'import torch; print(torch.cuda.is_available())')"
if [ "$check_cuda" != "True" ]; then
    echo "cuda support was not True, was $check_cuda"
else
    echo "cuda support found ..."

    pip install numpy --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu117

    cat << EOF
=============================================================================
=========================== Checking xformers ===============================

This install will possibly take a long time the first time it is run.

EOF

pushd xformers
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
popd
    
fi;

# python3 launch.py --xformers --reinstall-xformers --precision full --no-half
# python3 launch.py --xformers --precision full --no-half
python3 launch.py --xformers
