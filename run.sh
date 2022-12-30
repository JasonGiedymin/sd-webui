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

export VERSION=${VERSION:-"2"}

clean_vols() {
  echo "Cleaning up volumes ..."
  rm -vRf ./volumes/
}

prep_vols() {
  echo "Prepping volumes ..."
  mkdir -vp $(pwd)/volumes/venv
  mkdir -vp $(pwd)/volumes/repositories
  mkdir -vp $(pwd)/volumes/models
  mkdir -vp $(pwd)/volumes/ldm
  mkdir -vp $(pwd)/volumes/cache
  mkdir -vp $(pwd)/volumes/embeddings

  ## currently mapping extensions results in a link issue with trying to move a directory from
  ## /sd/tmp to /sd/extensions
  # mkdir -vp $(pwd)/volumes/extensions

  container_id=$(docker create sd:${VERSION})
  echo "Started base container [$container_id] for file copy ..."
  
  echo "Copying venv files ..."
  docker cp $container_id:/sd/venv/ $(pwd)/volumes/

  # echo "Copying repository files ..."
  # docker cp $container_id:/sd/repositories/ $(pwd)/volumes/repositories

  echo "Removing [$container_id] ..."
  docker rm -v $container_id
  echo "Size: $(du -h -d 0 ./volumes/)"
  echo "Done."
}

clean_models() {
  if [ -e ./models ]; then
    rm -vRf models
  fi;
  mkdir -vp models
}

download_models() {
  ./models.py download --links
}

docker_command() {
  # -v $(pwd)/volumes/extensions:/sd/extensions \

  cat <<EOF
  docker run -it --rm --name=sd-webui \
    --network=host \
    --device=/dev/kfd \
    --device=/dev/dri \
    --group-add=video ${entrypoint_bypass} \
    --ipc=host \
    --cap-add=SYS_PTRACE \
    --security-opt seccomp=unconfined \
    -e HF_HOME=/sd/.cache \
    -e HUGGING_FACE_HUB_TOKEN="$HF_TOKEN_RO" \
    -v $(pwd)/docker/entrypoint.sh:/sd/entrypoint.sh \
    -v $(pwd)/volumes/venv:/sd/venv \
    -v $(pwd)/volumes/repositories:/sd/repositories \
    -v $(pwd)/volumes/models:/sd/models \
    -v $(pwd)/volumes/ldm:/sd/ldm \
    -v $(pwd)/volumes/cache:/sd/.cache \
    -v $(pwd)/volumes/embeddings:/sd/embeddings \
    -v $(pwd)/images:/sd/images \
    -v $(pwd)/model_cache:/sd/models/Stable-diffusion/model_cache \
    -v $(pwd)/models:/sd/models/Stable-diffusion \
    -v $(pwd)/docker/patches:/sd/patches \
    sd:${VERSION} ${cmd}
EOF
}

usage() {
  cat << EOF

  Usage:

    ./run {help|prep|build|ui|models|clean|reset|test|config}

    ------------------------------------------------------------------
    help   - this usage screen
    build  - build a new docker image
    prep   - prep files, useful if you need to refresh from a new build
    ui     - loads the ui
    models - downloads and links models
    clean  - cleans out volumes only
    reset  - resets volumes by running clean and prep
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
  docker build --tag sd:${VERSION} ./
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
