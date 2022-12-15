#!/usr/bin/env bash

set -e

source ./env

export VERSION=${VERSION:-2}

docker build --tag sd:${VERSION} ./
