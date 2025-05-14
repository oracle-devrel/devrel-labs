# Kubernetes Deployment for Agentic RAG

This directory contains Kubernetes manifests and guides for deploying the Agentic RAG system on Kubernetes.

## Deployment Options

We currently provide a single deployment option with plans for a distributed deployment in the future:

### Local Deployment

This is a single-pod deployment where all components run in the same pod. It's simpler to deploy and manage, making it ideal for testing and development.

**Features:**
- Includes both Hugging Face models and Ollama for inference
- Uses GPU acceleration for faster inference
- Simpler deployment and management
- Easier debugging (all logs in one place)
- Lower complexity (no inter-service communication)
- Quicker setup

**Model Options:**
- **Hugging Face Models**: Uses `Mistral-7B` models from Hugging Face (requires a token)
- **Ollama Models**: Uses `ollama` for inference (llama3, phi3, qwen2)

### Future: Distributed System Deployment

A distributed system deployment that separates the LLM inference system into its own service is planned for future releases. This will allow for better resource allocation and scaling in production environments.

**Advantages:**
- Independent scaling of components
- Better resource optimization
- Higher availability
- Flexible model deployment
- Load balancing capabilities

## Deployment Guides

We provide several guides for different environments:

1. [**General Kubernetes Guide**](README_k8s.md): Basic instructions for any Kubernetes cluster
2. [**Oracle Kubernetes Engine (OKE) Guide**](OKE_DEPLOYMENT.md): Detailed instructions for deploying on OCI
3. [**Minikube Guide**](MINIKUBE.md): Quick start guide for local testing with Minikube

## Directory Structure

```bash
k8s/
├── README_MAIN.md           # This file
├── README.md                # General Kubernetes guide
├── OKE_DEPLOYMENT.md        # Oracle Kubernetes Engine guide
├── MINIKUBE.md              # Minikube guide
├── deploy.sh                # Deployment script
└── local-deployment/        # Manifests for local deployment
    ├── configmap.yaml
    ├── deployment.yaml
    └── service.yaml
```

## Quick Start

For a quick start, use the deployment script. Just go into the script and replace your `HF_TOKEN` in line 17:

```bash
# Make the script executable
chmod +x deploy.sh

# Deploy with a Hugging Face token
./deploy.sh --hf-token "your-huggingface-token" --namespace agentic-rag

# Or deploy without a Hugging Face token (Ollama models only)
./deploy.sh --namespace agentic-rag

# Deploy without GPU support (not recommended for production)
./deploy.sh --cpu-only --namespace agentic-rag
```

## Resource Requirements

The deployment requires the following minimum resources:

- **CPU**: 4+ cores
- **Memory**: 16GB+ RAM
- **Storage**: 50GB+
- **GPU**: 1 NVIDIA GPU (required for optimal performance)

## Next Steps

After deployment, you can:

1. **Add Documents**: Upload PDFs, process web content, or add repositories to the knowledge base
2. **Configure Models**: Download and configure different models
3. **Customize**: Adjust the system to your specific needs
4. **Scale**: For production use, consider implementing the distributed deployment with persistent storage (coming soon)

## Troubleshooting

See the specific deployment guides for troubleshooting tips. Common issues include:

- Insufficient resources
- Network connectivity problems
- Model download failures
- Configuration errors
- GPU driver issues

### GPU-Related Issues

If you encounter GPU-related issues:

1. **Check GPU availability**: Ensure your Kubernetes cluster has GPU nodes available
2. **Verify NVIDIA drivers**: Make sure NVIDIA drivers are installed on the nodes
3. **Check NVIDIA device plugin**: Ensure the NVIDIA device plugin is installed in your cluster
4. **Inspect pod logs**: Check for GPU-related errors in the pod logs

```bash
kubectl logs -f deployment/agentic-rag -n <namespace>
```

## GPU Configuration Summary

The deployment has been configured to use GPU acceleration by default for optimal performance:

### Key GPU Configuration Changes

1. **Resource Requests and Limits**:
   - Each pod requests and is limited to 1 NVIDIA GPU
   - Memory and CPU resources have been increased to better support GPU workloads

2. **NVIDIA Container Support**:
   - The deployment installs NVIDIA drivers and CUDA in the container
   - Environment variables are set to enable GPU visibility and capabilities

3. **Ollama GPU Configuration**:
   - Ollama is configured to use GPU acceleration automatically
   - Models like llama3, phi3, and qwen2 will benefit from GPU acceleration

4. **Deployment Script Enhancements**:
   - Added GPU availability detection
   - Added `--cpu-only` flag for environments without GPUs
   - Provides guidance for GPU monitoring and troubleshooting

5. **Documentation Updates**:
   - Added GPU-specific instructions for different Kubernetes environments
   - Included troubleshooting steps for GPU-related issues
   - Updated resource requirements to reflect GPU needs

### CPU Fallback

While the deployment is optimized for GPU usage, a CPU-only mode is available using the `--cpu-only` flag with the deployment script. However, this is not recommended for production use as inference performance will be significantly slower.

## Contributing

Contributions to improve the deployment manifests and guides are welcome. Please submit a pull request or open an issue. 