#!/bin/bash


# modify this environment variable
export NGC_API_KEY=<YOUR_NVIDIA_NGC_API_KEY>

# Choose a container name for bookkeeping
export CONTAINER_NAME=llama3-8b-instruct

echo "$NGC_API_KEY" | docker login nvcr.io --username '$oauthtoken' --password-stdin
# Choose a LLM NIM Image from the NGC catalog
export IMG_NAME="nvcr.io/nim/meta/llama3-8b-instruct:latest"
#export IMG_NAME="nvcr.io/nvidia/aiworkflows/genai-llm-playground:latest"
 
# Choose a path on your system to cache the downloaded models
export LOCAL_NIM_CACHE="/home/$USER/nim/cache"
mkdir /home/$USER/nim
mkdir /home/$USER/nim/cache
mkdir -p "$LOCAL_NIM_CACHE"
 
# Start the LLM NIM
# here, you can specify --gpus all (if you have more than 1 node in your OKE cluster).
# specify port forwarding with -p.
docker run -it --rm --name=$CONTAINER_NAME \
  --privileged \
  --runtime=nvidia \
  --gpus 1 \
  --env NGC_API_KEY="$NGC_API_KEY" \
  -v "$LOCAL_NIM_CACHE:/opt/nim/cache" \
  -u $(id -u) \
  -p 8000:8000 \
  $IMG_NAME