# Quick Start with Minikube

This guide provides instructions for deploying the Agentic RAG system on Minikube for local testing.

## Prerequisites

1. [Minikube](https://minikube.sigs.k8s.io/docs/start/) installed
2. [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/) installed
3. Docker or another container runtime installed
4. NVIDIA GPU with appropriate drivers installed
5. [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed

## Step 1: Start Minikube with GPU Support

Start Minikube with sufficient resources and GPU support:

```bash
# For Linux
minikube start --cpus 4 --memory 16384 --disk-size 50g --driver=kvm2 --gpu

# For Windows
minikube start --cpus 4 --memory 16384 --disk-size 50g --driver=hyperv --gpu

# For macOS (Note: GPU passthrough is limited on macOS)
minikube start --cpus 4 --memory 16384 --disk-size 50g --driver=hyperkit
```

Verify that Minikube is running:

```bash
minikube status
```

## Step 2: Install NVIDIA Device Plugin

Install the NVIDIA device plugin to enable GPU support in Kubernetes:

```bash
# Apply the NVIDIA device plugin
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml
```

Verify that the GPU is available in the cluster:

```bash
kubectl get nodes "-o=custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\.com/gpu"
```

## Step 3: Clone the Repository

Clone the repository containing the Kubernetes manifests:

```bash
git clone https://github.com/devrel/devrel-labs.git
cd devrel-labs/agentic_rag/k8s
```

## Step 4: Deploy the Application

The deployment includes both Hugging Face models and Ollama for inference. The Hugging Face token is optional but recommended for using Mistral models.

### Option 1: Deploy without a Hugging Face token (Ollama models only)

```bash
# Create a namespace
kubectl create namespace agentic-rag

# Create an empty ConfigMap
cat <<EOF | kubectl apply -n agentic-rag -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: agentic-rag-config
data:
  config.yaml: |
    # No Hugging Face token provided
    # You can still use Ollama models
EOF

# Apply the manifests
kubectl apply -n agentic-rag -f local-deployment/deployment.yaml
kubectl apply -n agentic-rag -f local-deployment/service.yaml
```

### Option 2: Deploy with a Hugging Face token (both Mistral and Ollama models)

```bash
# Create a namespace
kubectl create namespace agentic-rag

# Create ConfigMap with your Hugging Face token
cat <<EOF | kubectl apply -n agentic-rag -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: agentic-rag-config
data:
  config.yaml: |
    HUGGING_FACE_HUB_TOKEN: "your-huggingface-token"
EOF

# Apply the manifests
kubectl apply -n agentic-rag -f local-deployment/deployment.yaml
kubectl apply -n agentic-rag -f local-deployment/service.yaml
```

### Option 3: Using the deployment script

```bash
# Make the script executable
chmod +x deploy.sh

# Deploy with a Hugging Face token
./deploy.sh --hf-token "your-huggingface-token" --namespace agentic-rag

# Or deploy without a Hugging Face token
./deploy.sh --namespace agentic-rag
```

## Step 5: Monitor the Deployment

Check the status of your pods:

```bash
kubectl get pods -n agentic-rag
```

View the logs:

```bash
kubectl logs -f deployment/agentic-rag -n agentic-rag
```

## Step 6: Access the Application

For Minikube, you need to use port-forwarding to access the application:

```bash
kubectl port-forward -n agentic-rag service/agentic-rag 8080:80
```

Then access the application in your browser at `http://localhost:8080`.

Alternatively, you can use Minikube's service command:

```bash
minikube service agentic-rag -n agentic-rag
```

## Troubleshooting

### Insufficient Resources

If pods are stuck in Pending state due to insufficient resources, you can increase Minikube's resources:

```bash
minikube stop
minikube start --cpus 6 --memory 16384 --disk-size 50g --driver=kvm2 --gpu
```

### GPU-Related Issues

If you encounter GPU-related issues:

1. **Check GPU availability in Minikube**:
   ```bash
   minikube ssh -- nvidia-smi
   ```

2. **Verify NVIDIA device plugin is running**:
   ```bash
   kubectl get pods -n kube-system | grep nvidia-device-plugin
   ```

3. **Check if GPU is available to Kubernetes**:
   ```bash
   kubectl describe nodes | grep nvidia.com/gpu
   ```

### Slow Model Download

The first time you deploy, the models will be downloaded, which can take some time. You can check the progress in the logs:

```bash
kubectl logs -f deployment/agentic-rag -n agentic-rag
```

### Service Not Accessible

If you can't access the service, make sure port-forwarding is running or try using the Minikube service command.

## Cleanup

To remove all resources:

```bash
kubectl delete namespace agentic-rag
```

To stop Minikube:

```bash
minikube stop
```

To delete the Minikube cluster:

```bash
minikube delete
``` 