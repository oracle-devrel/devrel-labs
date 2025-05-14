#!/bin/bash

# Deployment script for Agentic RAG

# Function to display usage
usage() {
  echo "Usage: $0 [--hf-token TOKEN] [--namespace NAMESPACE] [--cpu-only]"
  echo ""
  echo "Options:"
  echo "  --hf-token TOKEN     Hugging Face token (optional but recommended)"
  echo "  --namespace NAMESPACE    Kubernetes namespace to deploy to (default: default)"
  echo "  --cpu-only           Deploy without GPU support (not recommended for production)"
  exit 1
}

# Default values
NAMESPACE="default"
HF_TOKEN=""
CPU_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --hf-token)
      HF_TOKEN="$2"
      shift 2
      ;;
    --namespace)
      NAMESPACE="$2"
      shift 2
      ;;
    --cpu-only)
      CPU_ONLY=true
      shift
      ;;
    *)
      usage
      ;;
  esac
done

# Create namespace if it doesn't exist
kubectl get namespace $NAMESPACE > /dev/null 2>&1 || kubectl create namespace $NAMESPACE

echo "Deploying Agentic RAG to namespace $NAMESPACE..."

# Check for GPU availability if not in CPU-only mode
if [[ "$CPU_ONLY" == "false" ]]; then
  echo "Checking for GPU availability..."
  GPU_COUNT=$(kubectl get nodes "-o=custom-columns=GPU:.status.allocatable.nvidia\.com/gpu" --no-headers | grep -v "<none>" | wc -l)
  
  if [[ "$GPU_COUNT" -eq 0 ]]; then
    echo "WARNING: No GPUs detected in the cluster!"
    echo "The deployment is configured to use GPUs, but none were found."
    echo "Options:"
    echo "  1. Install the NVIDIA device plugin: kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml"
    echo "  2. Use --cpu-only flag to deploy without GPU support (not recommended for production)"
    echo "  3. Ensure your nodes have GPUs and proper drivers installed"
    
    read -p "Continue with deployment anyway? (y/n): " CONTINUE
    if [[ "$CONTINUE" != "y" && "$CONTINUE" != "Y" ]]; then
      echo "Deployment aborted."
      exit 1
    fi
    
    echo "Continuing with deployment despite no GPUs detected..."
  else
    echo "Found $GPU_COUNT nodes with GPUs available."
  fi
fi

# Create ConfigMap with Hugging Face token if provided
if [[ -n "$HF_TOKEN" ]]; then
  echo "Using provided Hugging Face token..."
  cat <<EOF | kubectl apply -n $NAMESPACE -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: agentic-rag-config
data:
  config.yaml: |
    HUGGING_FACE_HUB_TOKEN: "$HF_TOKEN"
EOF
else
  echo "No Hugging Face token provided. Creating empty config..."
  cat <<EOF | kubectl apply -n $NAMESPACE -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: agentic-rag-config
data:
  config.yaml: |
    # No Hugging Face token provided
    # You can still use Ollama models
EOF
fi

# Apply deployment and service
if [[ "$CPU_ONLY" == "true" ]]; then
  echo "Deploying in CPU-only mode (not recommended for production)..."
  # Create a temporary CPU-only version of the deployment file
  sed '/nvidia.com\/gpu/d' local-deployment/deployment.yaml > local-deployment/deployment-cpu.yaml
  kubectl apply -n $NAMESPACE -f local-deployment/deployment-cpu.yaml
  rm local-deployment/deployment-cpu.yaml
else
  kubectl apply -n $NAMESPACE -f local-deployment/deployment.yaml
fi

kubectl apply -n $NAMESPACE -f local-deployment/service.yaml

echo "Deployment started. Check status with: kubectl get pods -n $NAMESPACE"
echo "Access the application with: kubectl get service agentic-rag -n $NAMESPACE"
echo "Note: Initial startup may take some time as models are downloaded."

# Provide additional guidance for monitoring GPU usage
if [[ "$CPU_ONLY" == "false" ]]; then
  echo ""
  echo "To monitor GPU usage:"
  echo "  1. Check pod status: kubectl get pods -n $NAMESPACE"
  echo "  2. View pod logs: kubectl logs -f deployment/agentic-rag -n $NAMESPACE"
  echo "  3. Check GPU allocation: kubectl describe pod -l app=agentic-rag -n $NAMESPACE | grep -A5 'Allocated resources'"
fi 