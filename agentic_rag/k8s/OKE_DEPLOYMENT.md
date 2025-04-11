# Deploying Agentic RAG on Oracle Kubernetes Engine (OKE)

This guide provides detailed instructions for deploying the Agentic RAG system on Oracle Kubernetes Engine (OKE).

## Prerequisites

1. Access to an Oracle Cloud Infrastructure (OCI) account
2. OKE cluster created and configured
3. `kubectl` installed and configured to connect to your OKE cluster
4. OCI CLI installed and configured (optional but recommended)
5. GPU-enabled node pool in your OKE cluster

## Step 1: Create a GPU-enabled Node Pool

If you don't already have a GPU-enabled node pool in your OKE cluster, you'll need to create one:

1. Navigate to the OKE cluster in the OCI Console
2. Click on "Add Node Pool"
3. Configure the node pool:
   - Name: `gpu-pool`
   - Shape: Select a GPU-enabled shape (e.g., `VM.GPU2.1`, `VM.GPU3.1`, or `BM.GPU4.8`)
   - Image: Select an Oracle Linux image
   - Node count: Start with 1-2 nodes
4. Click "Create"

Wait for the node pool to be created and the nodes to become active.

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

## Step 5: Configure Load Balancer (Optional)

By default, the service is exposed as a LoadBalancer, which will automatically create an OCI Load Balancer. If you want to customize the load balancer:

```bash
# Edit the service
kubectl edit service agentic-rag -n agentic-rag
```

Add annotations for OCI Load Balancer configuration:

```yaml
metadata:
  annotations:
    service.beta.kubernetes.io/oci-load-balancer-shape: "flexible"
    service.beta.kubernetes.io/oci-load-balancer-shape-flex-min: "10"
    service.beta.kubernetes.io/oci-load-balancer-shape-flex-max: "100"
```

## Step 6: Monitor the Deployment

Check the status of your pods:

```bash
kubectl get pods -n agentic-rag
```

View the logs:

```bash
kubectl logs -f deployment/agentic-rag -n agentic-rag
```

Check GPU allocation:

```bash
kubectl describe pod -l app=agentic-rag -n agentic-rag | grep -A5 'Allocated resources'
```

## Step 7: Access the Application

Get the external IP of the load balancer:

```bash
kubectl get service agentic-rag -n agentic-rag
```

Access the application in your browser at `http://<EXTERNAL-IP>`.

## Troubleshooting

### Pod Stuck in Pending State

If the pod is stuck in Pending state, check the events:

```bash
kubectl describe pod -l app=agentic-rag -n agentic-rag
```

Common issues include:

1. **Insufficient resources**: Ensure your node pool has enough resources
2. **GPU not available**: Ensure your node pool has GPU-enabled nodes
3. **Image pull issues**: Check if the image can be pulled from the registry

### GPU-Related Issues

If you encounter GPU-related issues:

1. **Check GPU availability in OKE**:
   ```bash
   kubectl get nodes "-o=custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\.com/gpu"
   ```

2. **Verify NVIDIA device plugin is running**:
   ```bash
   kubectl get pods -n kube-system | grep nvidia-device-plugin
   ```

3. **Check if GPU is available to the pod**:
   ```bash
   kubectl describe pod -l app=agentic-rag -n agentic-rag | grep -A5 'Allocated resources'
   ```

4. **Check NVIDIA driver installation on the node**:
   ```bash
   # Get the node name
   NODE_NAME=$(kubectl get pod -l app=agentic-rag -n agentic-rag -o jsonpath='{.items[0].spec.nodeName}')
   
   # Create a debug pod on the node
   kubectl debug node/$NODE_NAME -it --image=ubuntu
   
   # Inside the debug pod
   chroot /host
   nvidia-smi
   ```

### Load Balancer Issues

If the load balancer is not provisioning or not accessible:

1. Check the service status:
   ```bash
   kubectl get service agentic-rag -n agentic-rag
   ```

2. Check OCI Console for load balancer status and configuration

3. Ensure your VCN security lists allow traffic to the load balancer

## Scaling

To scale the deployment:

```bash
kubectl scale deployment agentic-rag -n agentic-rag --replicas=2
```

Note: Each replica will require its own GPU.

## Cleanup

To remove all resources:

```bash
kubectl delete namespace agentic-rag
```

To delete the OCI Load Balancer (if it's not automatically deleted):

1. Navigate to the Load Balancers page in the OCI Console
2. Find the load balancer created for your service
3. Click "Delete" and confirm 