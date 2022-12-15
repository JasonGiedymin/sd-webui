#!/usr/bin/env bash

set -e

source ./env

export VERSION=${VERSION:-"2"}

map_models() {
  container_dir="/sd/models/Stable-diffusion/"
  models=$(huggingface-cli scan-cache --dir model_cache -v | grep model | awk -F ' ' '{print $10}')
  for model in $models
  do
    model_name=$(echo "$model" | awk -F '/' '{print $7}' | awk -F 'models--' '{print $2}')
    echo "-v $model/model.ckpt:$container_dir$model_name.ckpt"
  done
}

# run() {
#   docker_command="docker run -it --rm --name=sd-webui \
#     --network=host \
#     --device=/dev/kfd \
#     --device=/dev/dri \
#     --group-add=video \
#     --ipc=host \
#     --cap-add=SYS_PTRACE \
#     --security-opt seccomp=unconfined \
#     $(map_models) \
#     sd:${VERSION}"
  
#   eval "$docker_command"
# }

docker_command() {
  cat <<EOF
  docker run -it --rm --name=sd-webui \
    --network=host \
    --device=/dev/kfd \
    --device=/dev/dri \
    --group-add=video \
    --ipc=host \
    --cap-add=SYS_PTRACE \
    --security-opt seccomp=unconfined \
    $(map_models) \
    sd:${VERSION}
EOF
}

run() {
  eval "$(docker_command)"
}

run
