#!/bin/bash

# Function to broadcast and log messages
broadcast() {
  echo "$1"
}

log() {
  echo "$1" >> /var/log/script.log
}

# Main script execution starts here
echo "Running cloudinit.sh script"

# Add public key to OPC user
echo "Adding public key to OPC authorized_keys"
sudo -u opc sh -c "echo ${PUB_KEY} >> /home/opc/.ssh/authorized_keys"

# Install essential packages including git
echo "Installing necessary packages..."
dnf install -y dnf-utils zip unzip gcc git
dnf config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo
dnf remove -y runc

# Install Docker
echo "Installing Docker..."
dnf install -y docker-ce --nobest
systemctl enable docker.service

# Get API key from Terraform variable
api_key="${nvidia_api_key}"

# Install NVIDIA container toolkit for Docker
broadcast "Installing NVIDIA container toolkit for Docker..."
log "Installing NVIDIA container toolkit for Docker..."
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/nvidia-container-toolkit.repo | sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo >/dev/null
sudo yum install -y nvidia-container-toolkit >/dev/null
sudo systemctl restart docker
broadcast "NVIDIA container toolkit installed successfully."
log "NVIDIA container toolkit installed successfully."

# Generate CDI configuration for Docker
broadcast "Configuring CDI for Docker..."
log "Configuring CDI for Docker..."
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml >/dev/null
broadcast "CDI configured successfully for Docker."
log "CDI configured successfully for Docker."

# Setup NVIDIA driver persistence across reboots
broadcast "Enabling NVIDIA persistence daemon..."
log "Enabling NVIDIA persistence daemon..."
nvidia-persistenced
sudo systemctl enable nvidia-persistenced
broadcast "NVIDIA persistence daemon enabled."
log "NVIDIA persistence daemon enabled."

# Configure Docker to use NVIDIA runtime
broadcast "Configuring Docker to use NVIDIA runtime..."
log "Configuring Docker to use NVIDIA runtime..."
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "runtimes": {
        "nvidia": {
            "path": "nvidia-container-runtime",
            "runtimeArgs": []
        }
    }
}
EOF
sudo systemctl restart docker
broadcast "Docker configured to use NVIDIA runtime."
log "Docker configured to use NVIDIA runtime."

# Start Docker and add OPC user to Docker group
echo "Starting Docker service..."
systemctl start docker.service
usermod -aG docker opc

# Install Python packages
echo "Installing Python packages..."
python3 -m pip install --upgrade pip wheel oci
python3 -m pip install --upgrade setuptools
python3 -m pip install oci-cli langchain six

# Grow filesystem
echo "Expanding filesystem..."
/usr/libexec/oci-growfs -y

# Optional firewall configuration
# broadcast "Configuring firewall..."
# log "Configuring firewall..."
# sudo firewall-cmd --zone=public --add-port=8888/tcp --permanent
# sudo firewall-cmd --reload
# broadcast "Firewall configuration complete."
# log "Firewall configuration complete."

# Holoscan installation
broadcast "Logging in to nvcr.io..."
log "Logging in to nvcr.io..."
echo $api_key | docker login nvcr.io --username '$oauthtoken' --password-stdin >/dev/null
broadcast "Logged in to nvcr.io successfully."
log "Logged in to nvcr.io successfully."

broadcast "Pulling Holoscan image from nvcr.io..."
log "Pulling Holoscan image from nvcr.io..."
docker pull nvcr.io/nvidia/clara-holoscan/holoscan:v2.4.0-dgpu >/dev/null
broadcast "Holoscan image pulled successfully."
log "Holoscan image pulled successfully."

broadcast "Starting Holoscan Jupyter container..."
log "Starting Holoscan Jupyter container..."

docker run -d \
  --gpus all \
  --net host \
  --ipc=host \
  --cap-add=CAP_SYS_PTRACE \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -v /home/user/holoscan_examples:/examples \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --name holoscan_jupyter \
  nvcr.io/nvidia/clara-holoscan/holoscan:v2.4.0-dgpu /bin/bash -c \
  "apt-get update && apt-get install -y python3-pip git && \
  pip3 install jupyter && \
  mkdir -p /workspace/holoscan_jupyter_notebooks && \
  jupyter notebook --ip=0.0.0.0 --port=8888 --allow-root --no-browser --NotebookApp.token='' --NotebookApp.password='' --notebook-dir=/workspace"

broadcast "Holoscan Jupyter container started successfully."
log "Holoscan Jupyter container started successfully."

# Stop and configure firewall
echo "Configuring firewall..."
systemctl stop firewalld
firewall-offline-cmd --zone=public --add-port=8888/tcp
systemctl start firewalld

broadcast "Cloudinit.sh script completed."
log "Cloudinit.sh script completed."
