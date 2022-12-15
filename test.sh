#!/usr/bin/env bash

set -e

source ./env

export VERSION=${VERSION:-"2"}

docker run -it --rm --name=sd-test \
  --network=host \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  --ipc=host \
  --cap-add=SYS_PTRACE \
  --security-opt seccomp=unconfined \
  -v $(pwd):/pwd \
  --entrypoint="" \
  sd:${VERSION} \
  bash
