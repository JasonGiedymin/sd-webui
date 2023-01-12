# Setup

## Pre Reqs

1. Uninstall amd components
1. Install Nvidia drivers
1. Install Nvidia Docker tool kit: `https://github.com/NVIDIA/nvidia-docker`

```shell
sudo amdgpu-uninstall
sudo apt-get purge amdgpu-install
sudo reboot

sudo apt-get install -y nvidia-driver-525 nvidia-dkms-525
sudo apt-key del 7fa2af80
sudo reboot

wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb
sudo dpkg -i cuda-keyring_1.0-1_all.deb

echo "deb [signed-by=/usr/share/keyrings/cuda-archive-keyring.gpg] https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/ /" | sudo tee /etc/apt/sources.list.d/cuda-ubuntu2204-x86_64.list

wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin
sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600

sudo apt-get update
sudo apt-get install cuda
sudo apt-get install nvidia-gds
sudo reboot

distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    && curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# run test image, should see a gpu with specs
sudo docker run --rm --gpus all --name test nvidia/cuda:11.6.2-base-ubuntu20.04 nvidia-smi
```

## TLDR

`python3 -m venv .venv`

Setup packages and run

```shell
source .venv/bin/activate

pip install -r requirements.txt

# new packages? Run below
# pip freeze > requirements.txt

# supply env

./download.sh
./build.sh

deactivate
exit
```

## Step 1 - venv

Create and source a virtual env

Create it like so:

```shell
python3 -m venv .venv
```

Activate it and install libs like so:
```shell
source .venv/bin/activate

pip install -r requirements.txt
```

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

## Step 4 - Build

```shell
./build.sh
```
