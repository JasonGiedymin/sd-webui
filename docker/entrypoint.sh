#!/usr/bin/env bash

set -e

pip install -U pip
pip install -r requirements.txt

# Fails on AMD as of right now ...
# python launch.py --precision full --no-half --force-enable-xformers

python launch.py --precision full --no-half
