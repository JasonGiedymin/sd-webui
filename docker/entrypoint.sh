#!/usr/bin/env bash

set -e

pip install -U pip
pip install -r requirements.txt

python launch.py --precision full --no-half
