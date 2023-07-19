# Setup

You can follow the easy or manual instructions.


## Complete Purge

Before starting, you may need to complete purge drivers.

```shell
sudo apt-get remove --purge nvidia\*
sudo apt-get autoremove -y
# you must reboot
reboot
```

## Easy Install

Follow [these instructions](https://developer.nvidia.com/cuda-downloads?target_os=Linux)

Current Instructions for Ubuntu 22.04.

> Remember to reboot after the install else the display will continue to use the default resolution.

```shell
wget https://developer.download.nvidia.com/compute/cuda/12.2.0/local_installers/cuda_12.2.0_535.54.03_linux.runsudo

sh cuda_12.2.0_535.54.03_linux.run
```

After install you'll see the following message:

```text
Please make sure that
 -   PATH includes /usr/local/cuda-12.2/bin
 -   LD_LIBRARY_PATH includes /usr/local/cuda-12.2/lib64, or, add /usr/local/cuda-12.2/lib64 to /etc/ld.so.conf and run ldconfig as root

To uninstall the CUDA Toolkit, run cuda-uninstaller in /usr/local/cuda-12.2/bin
To uninstall the NVIDIA Driver, run nvidia-uninstall
Logfile is /var/log/cuda-installer.log
```


### Modify Path

Until you make this change, you may not be able to run nvcc.

> Remember to start a new shell after modifying the path.

```shell
export PATH=$PATH:/usr/local/cuda-12.2/bin
```


### Basic cli tests
```shell
which nvidia-smi
nvidia-smi
which nvcc
nvcc --help
```


### Install Nvidia Docker

```shell
sudo apt-get install -y nvidia-docker2
# It's very important to restart the docker service!
sudo systemctl restart docker
```

> You may need to visit this docker [hub page](https://hub.docker.com/r/nvidia/cuda) to get the latest image.

```shell
# run test image, should see a gpu with specs
sudo docker run --rm --gpus all --name test nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

# Manual Setup

## Pre Reqs

1. Uninstall amd components
1. Install Nvidia drivers
1. Install Nvidia Docker tool kit: `https://github.com/NVIDIA/nvidia-docker`


## Setup

```shell
sudo amdgpu-uninstall
sudo apt-get purge amdgpu-install
sudo reboot

sudo apt-get install -y nvidia-driver-535 nvidia-dkms-535
# don't do this!
# sudo apt-get autoremove -y

# install cuda and tools for nvcc
sudo apt-get install -y cuda nvidia-cuda-toolkit

# OR using apt-mark hold
sudo apt-mark hold nvidia-driver-530
sudo apt-mark hold nvidia-dkms-530
sudo apt-mark hold nvidia-cuda-toolkit
sudo apt-mark hold nvidia-gds

# show holds
sudo apt-mark showhold

# to clear any locks or holds:
sudo apt-mark unhold nvidia-driver-530
sudo apt-mark unhold nvidia-dkms-530
sudo apt-mark unhold nvidia-cuda-toolkit
sudo apt-mark unhold nvidia-gds

# lock nvidia drivers from uninstalling using dpkg
# echo "nvidia-driver-530 hold" | sudo dpkg --set-selections
# echo "nvidia-dkms-530 hold" | sudo dpkg --set-selections
# echo "nvidia-cuda-toolkit hold" | sudo dpkg --set-selections
# echo "nvidia-gds hold" | sudo dpkg --set-selections

# to clear any locks or holds:
# sudo dpkg --clear-selections

## Basic cli tests
which nvidia-smi
sudo nvidia-smi
which nvcc
nvcc --help

# delete key
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

# complete reinstall, broken up by commands as each step is slow
# sudo dpkg --clear-selections
sudo apt-get install -y nvidia-driver-530 nvidia-dkms-530
sudo apt-get install -y cuda nvidia-cuda-toolkit
sudo apt-get install cuda
sudo apt-get install nvidia-gds

# OR using apt-mark hold
sudo apt-mark hold nvidia-driver-530
sudo apt-mark hold nvidia-dkms-530
sudo apt-mark hold nvidia-cuda-toolkit
sudo apt-mark hold nvidia-gds
# show holds
sudo apt-mark showhold
# to clear any locks or holds:
sudo apt-mark unhold nvidia-driver-530
sudo apt-mark unhold nvidia-dkms-530
sudo apt-mark unhold nvidia-cuda-toolkit
sudo apt-mark unhold nvidia-gds


```

## Development TLDR

Install nvidia drivers and proceed with the below.

`python3 -m venv .venv`

Setup packages and run

```shell
source .venv/bin/activate

pip install -r requirements.txt

# new packages? Run below
# pip freeze > requirements.txt

# supply env

# download models
./run.sh download

# build image(s)
./run.sh build

deactivate
exit
```


## Running this project

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
./run download
```

## Step 4 - Build

```shell
./run.sh build
```
