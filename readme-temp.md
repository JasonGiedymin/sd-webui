alias drun='docker run -it --name=sd-webui --network=host --device=/dev/kfd --device=/dev/dri --group-add=video --ipc=host --cap-add=SYS_PTRACE --security-opt seccomp=unconfined -v $(pwd):/pwd'
    
-v 
dirs = [base, f'{base}/src/taming-transformers', f'{base}/src/clip',
        f'{base}/src/GFPGAN', f'{base}/src/blip', f'{base}/src/codeformer',
        f'{base}/src/realesrgan', f'{base}/src/k-diffusion', f'{base}/src/ldm']
for d in dirs:
    !rm -rf {d + '/.git'}
clear_output()

https://github.com/l1na-forever/stable-diffusion-rocm-docker/blob/main/Dockerfile
https://github.com/l1na-forever/stable-diffusion-rocm-docker

# Test
docker run -it --rm --name=sd-webui l1naforever/stable-diffusion-rocm:latest bash

docker run -it --rm --name=sd-webui \
  --network=host \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  --ipc=host \
  --cap-add=SYS_PTRACE \
  --security-opt seccomp=unconfined \
  -v $(pwd):/pwd \
  l1naforever/stable-diffusion-rocm:latest bash


## Step 2 - Setup env

Copy and supply tokens in in the `env` file.

```shell
cp env.sample env
```

## Step 3 - Download Models

Models are auto downloaded from build but you can run the download manually.

```shell
./download.sh
```
