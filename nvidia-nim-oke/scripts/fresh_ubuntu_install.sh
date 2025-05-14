#!/bin/bash
# author @jasperan
# this script installs all required dependencies on a fresh ubuntu image, which allows you to run NVIDIA container runtime workloads on docker.

# install sudo, curl (to download docker), gnupg2
apt-get update -y && apt-get install sudo curl gnupg2 -y

# declare environment variable
export NGC_API_KEY=<YOUR_NVIDIA_NGC_API_KEY>

# download and install docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# install nvidia container toolkit (required to run their images on NVIDIA GPUs)

curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list


sed -i -e '/experimental/ s/^#//g' /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update -y 
sudo apt-get install -y nvidia-container-toolkit
sudo apt install nvidia-cuda-toolkit -y 
sudo apt install nvidia-driver-525 -y # for ubuntu 22.04, change this to your recommended driver
# you can find your recommended driver for your specific docker image by running: ~ sudo ubuntu-drivers devices ~

# run the docker image inside the container.

# Choose a container name for bookkeeping
export CONTAINER_NAME=llama3-8b-instruct
export IMG_NAME="nvcr.io/nim/meta/llama3-8b-instruct:latest"
export LOCAL_NIM_CACHE="/home/ubuntu/nim/cache"
mkdir -p "$LOCAL_NIM_CACHE"
 
# login to NVIDIA NGC and run any image.

echo "$NGC_API_KEY" | docker login nvcr.io --username '$oauthtoken' --password-stdin

# launch dockerd if it wasn't previously launched on the background.
nohup dockerd &
# Start the LLM NIM
docker run -it --privileged --rm --name=$CONTAINER_NAME --runtime=nvidia --gpus 1 --env NGC_API_KEY="$NGC_API_KEY" -v "$LOCAL_NIM_CACHE:/opt/nim/cache" -u $(id -u) -p 8000:8000 $IMG_NAME