#!/usr/bin/env bash

set -e

source ./env

# checks
if [ -z "$(which huggingface-cli)" ]; then
  echo "Looks like you may need to source the .venv."
  echo "  source ./venv/bin/activate"
  echo "Otherwise doing it manually here now ..."
  source ./.venv/bin/activate
fi;

export IMAGE=${IMAGE:-"sd-nvidia"}
export VERSION=${VERSION:-"3"}

clean_vols() {
  echo "Cleaning up volumes ..."
  rm -vRf ./volumes/
}

prep_vols() {
  echo "Prepping volumes ..."
  mkdir -vp $(pwd)/volumes/xformers
  mkdir -vp $(pwd)/volumes/venv
  mkdir -vp $(pwd)/volumes/repositories
  mkdir -vp $(pwd)/volumes/models
  mkdir -vp $(pwd)/volumes/ldm
  mkdir -vp $(pwd)/volumes/cache
  mkdir -vp $(pwd)/volumes/embeddings

  ## currently mapping extensions results in a link issue with trying to move a directory from
  ## /sd/tmp to /sd/extensions
  # mkdir -vp $(pwd)/volumes/extensions

  container_id=$(docker create --env UID=$(id -u) --env GID=$(id -g) --user ${UID}:${GID} ${IMAGE}${VERSION})
  echo "Started base container [$container_id] for file copy ..."
  
  echo "Copying venv files ..."
  docker cp $container_id:/sd/venv/ $(pwd)/volumes/
  echo "Copying xformers files ..."
  docker cp $container_id:/sd/xformers/ $(pwd)/volumes/
  echo "Copying models files ..."
  docker cp $container_id:/sd/models/ $(pwd)/volumes/

  # echo "Copying repository files ..."
  # docker cp $container_id:/sd/repositories/ $(pwd)/volumes/repositories

  echo "Removing [$container_id] ..."
  docker rm -v $container_id
  echo "Size: $(du -h -d 0 ./volumes/)"
  echo "Done."

  # ensure user owns all these files
  # helps if user had to use sudo for cleaning
  chown $USER:$USER -R $(pwd)/volumes/
}

clean_models() {
  if [ -e ./models ]; then
    rm -vRf models
  fi;
  mkdir -vp models
}

download_models() {
  sudo chown $USER:$USER -R volumes/models
  ./models.py download --links
}

docker_command() {
  # Run as root for now ...
  # --env UID=$(id -u) --env GID=$(id -g) \
  # --user ${UID}:${GID} \

  cat <<EOF
  docker run -it --rm --name=sd-webui-nvidia \
    --env UID=$(id -u) --env GID=$(id -g) \
    --user ${UID}:${GID} \
    --gpus all \
    --network=host \
    -e HF_HOME=/sd/.cache \
    -e HUGGING_FACE_HUB_TOKEN="$HF_TOKEN_RO" \
    -v $(pwd)/docker/entrypoint.sh:/sd/entrypoint.sh \
    -v $(pwd)/volumes/xformers:/sd/xformers \
    -v $(pwd)/volumes/venv:/sd/venv \
    -v $(pwd)/volumes/repositories:/sd/repositories \
    -v $(pwd)/volumes/models:/sd/models \
    -v $(pwd)/volumes/ldm:/sd/ldm \
    -v $(pwd)/volumes/cache:/sd/.cache \
    -v $(pwd)/volumes/embeddings:/sd/embeddings \
    -v $(pwd)/images:/sd/images \
    -v $(pwd)/model_cache:/sd/model_cache \
    -v $(pwd)/models:/sd/models/Stable-diffusion \
    -v $(pwd)/docker/patches:/sd/patches \
    ${entrypoint_bypass} \
    ${IMAGE}${VERSION} ${cmd}
EOF
}

usage() {
  cat << EOF

  Usage:

    ./run {help|build|ui|models|clean|prep|reset|test|config}

    ------------------------------------------------------------------
    help   - this usage screen
    build  - build a new docker image
    ui     - loads the ui
    models - downloads and links models
    clean  - cleans out volumes only (not model cache) - do this for venv issues
    prep   - prep files, useful if you need to refresh from a new build
    reset  - resets volumes by running clean and prep commands (may need run with sudo)
    shell  - runs a shell that bypasses the entrypoint for manual work
    config - test the config

EOF
}

run_ui() {
  eval "$(docker_command)"
}

run_shell() {
  export entrypoint_bypass="--entrypoint=''"
  export cmd="bash"
  eval "$(docker_command)"
}

run_config_check() {
  ./models.py check
}

run_build() {
  docker build --tag ${IMAGE}${VERSION} -f Dockerfile ./
}

run() {
  case $@ in
    build)
      run_build
      ;;
    ui)
      run_ui
      ;;
    shell)
      run_shell
      ;;
    config)
      run_config_check
      ;;
    prep)
      prep_vols
      ;;
    clean)
      clean_vols
      ;;
    reset)
      clean_vols
      prep_vols
      ;;
    models)
      download_models
      ;;
    *)
      usage
      exit 1;
      ;;
  esac
}

run $@
